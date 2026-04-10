<script lang="ts">
	import { tick } from 'svelte';
	import { invalidateAll } from '$app/navigation';
	import { Chat, type UIMessage } from '@ai-sdk/svelte';
	import { DefaultChatTransport } from 'ai';
	import AgentAvatar from '$lib/components/agent-avatar.svelte';
	import Markdown from '$lib/components/markdown.svelte';
	import { Icon } from '$lib/icons';

	let { data } = $props();

	type LifecyclePhase = 'idle' | 'starting' | 'running' | 'stopping' | 'error';

	let phaseOverride: LifecyclePhase | null = $state(null);
	let lifecycleError: string | null = $state(null);

	const phase: LifecyclePhase = $derived(
		phaseOverride ?? (data.agent.status as LifecyclePhase)
	);

	const chat = $derived(
		new Chat<UIMessage>({
			id: data.agent.id,
			transport: new DefaultChatTransport({
				api: `/api/agents/${data.agent.id}/chat`
			}),
			onError: (err) => {
				console.error('[chat] error:', err);
			}
		})
	);

	let input = $state('');
	let composer: HTMLTextAreaElement | null = $state(null);
	let scroller: HTMLElement | null = $state(null);

	function autoSize() {
		if (!composer) return;
		composer.style.height = 'auto';
		composer.style.height = Math.min(composer.scrollHeight, 200) + 'px';
	}
	$effect(() => {
		void [input];
		autoSize();
	});

	$effect(() => {
		void [chat.messages, chat.status];
		tick().then(() => {
			if (scroller) scroller.scrollTop = scroller.scrollHeight;
		});
	});

	async function send() {
		const text = input.trim();
		if (!text || chat.status === 'streaming' || chat.status === 'submitted') return;
		input = '';
		await chat.sendMessage({ text });
	}

	function onKey(e: KeyboardEvent) {
		if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
			e.preventDefault();
			send();
		}
	}

	function messageText(m: UIMessage): string {
		return m.parts
			.filter((p): p is { type: 'text'; text: string } => p.type === 'text')
			.map((p) => p.text)
			.join('');
	}

	async function startAgent() {
		phaseOverride = 'starting';
		lifecycleError = null;
		try {
			const res = await fetch(`/api/agents/${data.agent.id}/start`, { method: 'POST' });
			if (!res.ok) {
				const text = await res.text();
				throw new Error(text || `HTTP ${res.status}`);
			}
			await invalidateAll();
			phaseOverride = null;
		} catch (err) {
			phaseOverride = 'error';
			lifecycleError = err instanceof Error ? err.message : 'Failed to start sandbox';
		}
	}

	async function stopAgent() {
		phaseOverride = 'stopping';
		lifecycleError = null;
		try {
			const res = await fetch(`/api/agents/${data.agent.id}/stop`, { method: 'POST' });
			if (!res.ok) {
				const text = await res.text();
				throw new Error(text || `HTTP ${res.status}`);
			}
			await invalidateAll();
			phaseOverride = null;
		} catch (err) {
			phaseOverride = 'error';
			lifecycleError = err instanceof Error ? err.message : 'Failed to stop sandbox';
		}
	}

	function dismissLifecycleError() {
		lifecycleError = null;
		phaseOverride = null;
	}

	const isStreaming = $derived(chat.status === 'streaming' || chat.status === 'submitted');
	const lastMessageId = $derived(chat.messages.at(-1)?.id);
	const isRunning = $derived(phase === 'running');
	const isTransitioning = $derived(phase === 'starting' || phase === 'stopping');

	const statusDotVariant = $derived(
		phase === 'running'
			? 'running'
			: phase === 'starting' || phase === 'stopping'
				? 'pending'
				: phase === 'error'
					? 'error'
					: 'idle'
	);
</script>

<div class="chat-shell">
	<!-- ── Header ─────────────────────────────────────────────── -->
	<header class="chat-header">
		<div class="header-left">
			<AgentAvatar name={data.agent.name} isAdmin={data.agent.isAdmin} size={30} />
			<div class="header-meta">
				<h1 class="agent-name font-display">{data.agent.name}</h1>
				<p class="agent-sub">
					<span class="status-dot status-{statusDotVariant}"></span>
					<span class="font-mono">{phase}</span>
					<span class="sep">·</span>
					<span class="image font-mono">{data.agent.image.split('/').at(-1)}</span>
				</p>
			</div>
		</div>
		<div class="header-actions">
			{#if phase === 'idle'}
				<button class="lifecycle-btn start" onclick={startAgent}>
					<Icon icon="oc:running" width={12} height={12} />
					<span>Start</span>
				</button>
			{:else if phase === 'starting'}
				<button class="lifecycle-btn transitioning" disabled>
					<span class="spinner"></span>
					<span>starting…</span>
				</button>
			{:else if phase === 'running'}
				<button class="lifecycle-btn stop" onclick={stopAgent}>
					<Icon icon="oc:stopped" width={11} height={11} />
					<span>Stop</span>
				</button>
			{:else if phase === 'stopping'}
				<button class="lifecycle-btn transitioning" disabled>
					<span class="spinner"></span>
					<span>stopping…</span>
				</button>
			{:else if phase === 'error'}
				<button class="lifecycle-btn retry" onclick={startAgent}>
					<Icon icon="oc:error" width={12} height={12} />
					<span>Retry</span>
				</button>
			{/if}
			<div class="header-divider"></div>
			<button class="header-btn" aria-label="Agent scope" disabled={!isRunning}>
				<Icon icon="oc:tool" width={13} height={13} />
				<span>Scope</span>
			</button>
			<button class="header-btn" aria-label="Agent logs">
				<Icon icon="oc:log" width={13} height={13} />
				<span>Logs</span>
			</button>
		</div>
	</header>

	<!-- ── Lifecycle error banner ─────────────────────────────── -->
	{#if lifecycleError}
		<div class="lifecycle-error">
			<Icon icon="oc:error" width={13} height={13} />
			<div class="lifecycle-error-body">
				<div class="lifecycle-error-title font-mono">sandbox lifecycle failed</div>
				<pre class="lifecycle-error-detail">{lifecycleError}</pre>
			</div>
			<button class="lifecycle-error-dismiss font-mono" onclick={dismissLifecycleError}>
				dismiss
			</button>
		</div>
	{/if}

	<!-- ── Canvas ─────────────────────────────────────────────── -->
	<section class="canvas" bind:this={scroller}>
		{#if phase === 'idle' || phase === 'starting' || phase === 'error'}
			<!-- ── Offline / transitional state ─────────────── -->
			<div class="offline-state">
				<div class="offline-inner">
					<AgentAvatar name={data.agent.name} isAdmin={data.agent.isAdmin} size={68} />

					<h2 class="offline-title font-display">
						{#if phase === 'idle'}
							<em>{data.agent.name}</em> is resting.
						{:else if phase === 'starting'}
							Waking <em>{data.agent.name}</em><span class="dot-dot-dot">…</span>
						{:else}
							<em>{data.agent.name}</em> couldn't start.
						{/if}
					</h2>

					<p class="offline-sub">
						{#if phase === 'idle'}
							The sandbox VM is cold. Start it to begin chatting — your workspace
							files, skills, and MCPs will be synced to a fresh container.
						{:else if phase === 'starting'}
							Launching sandbox, syncing workspace, waiting for the nanobot gateway
							to come online. This usually takes under 15 seconds.
						{:else}
							The sandbox failed to start. Check the error above and try again,
							or inspect logs for details.
						{/if}
					</p>

					{#if phase === 'idle'}
						<button class="offline-cta" onclick={startAgent}>
							<Icon icon="oc:running" width={14} height={14} />
							<span>Start {data.agent.name}</span>
						</button>
					{:else if phase === 'starting'}
						<div class="boot-log font-mono">
							<div class="boot-line">
								<span class="tick">✓</span> building vm payload
							</div>
							<div class="boot-line">
								<span class="tick">✓</span> mounting workspace
							</div>
							<div class="boot-line active">
								<span class="spinner spinner-mono"></span> launching sandbox
							</div>
							<div class="boot-line pending">
								<span class="tick">·</span> awaiting gateway
							</div>
						</div>
					{:else if phase === 'error'}
						<button class="offline-cta" onclick={startAgent}>
							<Icon icon="oc:error" width={14} height={14} />
							<span>Retry start</span>
						</button>
					{/if}
				</div>
			</div>
		{:else}
			<!-- ── Running / stopping: chat thread ─────────── -->
			<div class="thread">
				{#if chat.messages.length === 0}
					<div class="intro">
						<p class="intro-eyebrow font-mono">ready</p>
						<h2 class="intro-title font-display">
							Hey <em>{data.user?.name?.split(' ')[0] ?? 'there'}</em>.
						</h2>
						<p class="intro-sub">
							{#if data.agent.isAdmin}
								I'm your Admin. Tell me what you want to build — I'll scaffold agents, wire up
								skills, environments, and channels for you.
							{:else}
								I'm ready when you are.
							{/if}
						</p>
					</div>
				{/if}

				{#each chat.messages as message (message.id)}
					{@const text = messageText(message)}
					{@const isLast = message.id === lastMessageId}
					{#if message.role === 'user'}
						<article class="msg user-msg">
							<div class="user-bubble">{text}</div>
						</article>
					{:else}
						<article class="msg agent-msg">
							<div class="agent-avatar-col">
								<AgentAvatar name={data.agent.name} isAdmin={data.agent.isAdmin} size={22} />
							</div>
							<div class="agent-body">
								<div class="agent-name-tag font-display">{data.agent.name}</div>
								<Markdown {text} streaming={isStreaming && isLast} />
							</div>
						</article>
					{/if}
				{/each}

				{#if chat.status === 'submitted' && chat.messages.at(-1)?.role === 'user'}
					<article class="msg agent-msg">
						<div class="agent-avatar-col">
							<AgentAvatar name={data.agent.name} isAdmin={data.agent.isAdmin} size={22} />
						</div>
						<div class="agent-body">
							<div class="agent-name-tag font-display">{data.agent.name}</div>
							<div class="thinking-dots" aria-label="thinking">
								<span></span>
								<span></span>
								<span></span>
							</div>
						</div>
					</article>
				{/if}

				{#if chat.error}
					<article class="msg error-msg font-mono">
						<Icon icon="oc:error" width={13} height={13} />
						{chat.error.message}
						<button class="retry" onclick={() => chat.clearError()}>dismiss</button>
					</article>
				{/if}
			</div>
		{/if}
	</section>

	<!-- ── Composer (only when running or stopping) ──────────── -->
	{#if phase === 'running' || phase === 'stopping'}
		<footer class="composer-wrap">
			<form
				class="composer"
				onsubmit={(e) => {
					e.preventDefault();
					send();
				}}
			>
				<textarea
					class="composer-input"
					bind:this={composer}
					bind:value={input}
					onkeydown={onKey}
					placeholder={data.agent.isAdmin
						? 'ask your admin…'
						: `write to ${data.agent.name.toLowerCase()}…`}
					rows="1"
					disabled={!isRunning}
					aria-label="Message composer"
				></textarea>
				<div class="composer-foot">
					<span class="hint font-mono">
						{#if isTransitioning}
							sandbox stopping
						{:else}
							<kbd>⌘</kbd><kbd>↵</kbd> to send
						{/if}
					</span>
					<button
						type="submit"
						class="send-btn"
						disabled={isStreaming || !input.trim() || !isRunning}
						aria-label="Send message"
					>
						{#if isStreaming}
							<span class="spinner send-spinner"></span>
						{:else}
							<Icon icon="tabler:arrow-up" width={14} height={14} />
						{/if}
					</button>
				</div>
			</form>
		</footer>
	{/if}
</div>

<style>
	.chat-shell {
		display: flex;
		flex-direction: column;
		height: 100vh;
		max-height: 100vh;
		background: var(--background);
	}

	/* ── Header ────────────────────────────────────────────── */
	.chat-header {
		height: 54px;
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 1.25rem;
		border-bottom: 1px solid var(--border);
		background: var(--background);
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.header-meta {
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
	}

	.agent-name {
		font-size: 1rem;
		font-variation-settings: 'opsz' 24, 'wght' 650;
		line-height: 1;
		letter-spacing: -0.01em;
	}

	.agent-sub {
		font-size: 0.65rem;
		display: flex;
		align-items: center;
		gap: 0.35rem;
		color: var(--muted-foreground);
	}

	.agent-sub .sep { opacity: 0.4; }
	.agent-sub .image { opacity: 0.65; }

	.header-actions {
		display: flex;
		align-items: center;
		gap: 0.2rem;
	}

	.header-divider {
		width: 1px;
		height: 16px;
		background: var(--border);
		margin: 0 0.3rem;
	}

	.header-btn {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.35rem 0.6rem;
		font-size: 0.7rem;
		border-radius: 0.3rem;
		color: var(--muted-foreground);
		transition: background 150ms ease, color 150ms ease;
	}

	.header-btn:hover:not(:disabled) {
		background: var(--muted);
		color: var(--foreground);
	}

	.header-btn:disabled {
		opacity: 0.35;
		cursor: not-allowed;
	}

	/* ── Lifecycle buttons ────────────────────────────────── */
	.lifecycle-btn {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.38rem 0.8rem;
		font-size: 0.7rem;
		font-family: var(--font-mono);
		letter-spacing: 0.02em;
		border-radius: 0.3rem;
		border: 1px solid transparent;
		transition: background 150ms ease, border-color 150ms ease, color 150ms ease, box-shadow 150ms ease;
	}

	.lifecycle-btn.start {
		background: var(--primary);
		color: var(--primary-foreground);
		box-shadow: 0 0 12px color-mix(in oklch, var(--primary) 28%, transparent);
	}
	.lifecycle-btn.start:hover { filter: brightness(1.07); }

	.lifecycle-btn.stop {
		background: transparent;
		color: var(--muted-foreground);
		border-color: var(--border);
	}
	.lifecycle-btn.stop:hover {
		color: var(--foreground);
		border-color: color-mix(in oklch, var(--destructive) 40%, var(--border));
		background: color-mix(in oklch, var(--destructive) 6%, transparent);
	}

	.lifecycle-btn.transitioning {
		background: color-mix(in oklch, var(--primary) 10%, transparent);
		color: var(--primary);
		border-color: color-mix(in oklch, var(--primary) 28%, transparent);
		cursor: default;
	}

	.lifecycle-btn.retry {
		background: color-mix(in oklch, var(--destructive) 10%, transparent);
		color: var(--destructive);
		border-color: color-mix(in oklch, var(--destructive) 32%, transparent);
	}
	.lifecycle-btn.retry:hover {
		background: color-mix(in oklch, var(--destructive) 16%, transparent);
	}

	/* ── Spinner ──────────────────────────────────────────── */
	.spinner {
		width: 11px;
		height: 11px;
		border-radius: 9999px;
		border: 1.5px solid currentColor;
		border-right-color: transparent;
		animation: spin 0.75s linear infinite;
	}
	.spinner-mono { width: 9px; height: 9px; border-width: 1px; }
	.send-spinner { width: 13px; height: 13px; }

	@keyframes spin { to { transform: rotate(360deg); } }

	/* ── Lifecycle error banner ───────────────────────────── */
	.lifecycle-error {
		display: flex;
		align-items: flex-start;
		gap: 0.65rem;
		padding: 0.65rem 1.25rem;
		background: color-mix(in oklch, var(--destructive) 9%, transparent);
		border-bottom: 1px solid color-mix(in oklch, var(--destructive) 28%, transparent);
		color: var(--destructive);
	}

	.lifecycle-error-body { flex: 1; min-width: 0; }

	.lifecycle-error-title {
		font-size: 0.65rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		margin-bottom: 0.2rem;
	}

	.lifecycle-error-detail {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		line-height: 1.45;
		margin: 0;
		white-space: pre-wrap;
		word-wrap: break-word;
		color: color-mix(in oklch, var(--destructive) 80%, var(--foreground));
	}

	.lifecycle-error-dismiss {
		flex-shrink: 0;
		font-size: 0.63rem;
		color: var(--destructive);
		text-decoration: underline;
		text-underline-offset: 3px;
		letter-spacing: 0.03em;
	}

	/* ── Canvas ───────────────────────────────────────────────── */
	.canvas {
		flex: 1;
		overflow-y: auto;
		padding: 2.5rem 1.5rem 1.5rem;
		scroll-behavior: smooth;
	}

	/* Subtle top-fade when scrolled */
	.canvas {
		mask-image: linear-gradient(to bottom, transparent 0, black 2.5rem);
	}

	.thread {
		max-width: 42rem;
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 1.75rem;
	}

	/* ── Offline state ───────────────────────────────────── */
	.offline-state {
		max-width: 34rem;
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 5rem 1rem 3rem;
	}

	.offline-inner {
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
	}

	.offline-title {
		font-size: 2.25rem;
		font-variation-settings: 'opsz' 48, 'wght' 700;
		line-height: 1.08;
		letter-spacing: -0.015em;
		margin: 1.75rem 0 0.9rem;
	}

	.offline-title em {
		color: var(--primary);
		font-style: italic;
	}

	.dot-dot-dot {
		display: inline-block;
		color: var(--primary);
		animation: dot-fade 1.4s ease-in-out infinite;
	}

	@keyframes dot-fade {
		0%, 100% { opacity: 0.3; }
		50% { opacity: 1; }
	}

	.offline-sub {
		font-size: 0.9rem;
		line-height: 1.65;
		color: var(--muted-foreground);
		max-width: 26rem;
		margin-bottom: 2rem;
	}

	.offline-cta {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.65rem 1.2rem;
		background: var(--primary);
		color: var(--primary-foreground);
		font-family: var(--font-mono);
		font-size: 0.76rem;
		letter-spacing: 0.03em;
		border-radius: 9999px;
		box-shadow: 0 0 20px color-mix(in oklch, var(--primary) 28%, transparent);
		transition: filter 150ms ease, transform 150ms ease;
	}

	.offline-cta:hover { filter: brightness(1.07); transform: translateY(-1px); }
	.offline-cta:active { transform: translateY(0); }

	/* ── Boot log ─────────────────────────────────────────── */
	.boot-log {
		background: color-mix(in oklch, var(--card) 80%, transparent);
		border: 1px solid var(--border);
		border-radius: 0.5rem;
		padding: 0.9rem 1.1rem;
		font-size: 0.7rem;
		line-height: 2;
		color: var(--muted-foreground);
		text-align: left;
		min-width: 18rem;
	}

	.boot-line { display: flex; align-items: center; gap: 0.5rem; }
	.boot-line.active { color: var(--primary); }
	.boot-line.pending { opacity: 0.35; }

	.tick {
		font-family: var(--font-mono);
		width: 10px;
		text-align: center;
		color: var(--status-running);
	}

	.boot-line.pending .tick { color: var(--muted-foreground); }

	/* ── Intro ────────────────────────────────────────────── */
	.intro {
		padding: 1.5rem 0 2rem;
	}

	.intro-eyebrow {
		font-size: 0.62rem;
		letter-spacing: 0.18em;
		text-transform: uppercase;
		color: var(--primary);
		margin-bottom: 0.85rem;
		opacity: 0.8;
	}

	.intro-title {
		font-size: 2.5rem;
		font-variation-settings: 'opsz' 48, 'wght' 720;
		line-height: 1.05;
		letter-spacing: -0.015em;
		margin-bottom: 0.9rem;
	}

	.intro-title em {
		color: var(--primary);
		font-style: italic;
	}

	.intro-sub {
		font-size: 0.95rem;
		line-height: 1.65;
		color: var(--muted-foreground);
		max-width: 34rem;
	}

	/* ── Messages ─────────────────────────────────────────── */
	.msg {
		position: relative;
		animation: msg-in 220ms cubic-bezier(0.16, 1, 0.3, 1) both;
	}

	@keyframes msg-in {
		from { opacity: 0; transform: translateY(8px); }
		to   { opacity: 1; transform: translateY(0); }
	}

	/* Agent message — avatar + body */
	.agent-msg {
		display: grid;
		grid-template-columns: 1.75rem 1fr;
		gap: 0.75rem;
		align-items: start;
	}

	.agent-avatar-col {
		padding-top: 0.15rem;
	}

	.agent-body {
		min-width: 0;
	}

	.agent-name-tag {
		font-size: 0.7rem;
		font-variation-settings: 'opsz' 12, 'wght' 550;
		color: color-mix(in oklch, var(--primary) 65%, var(--foreground));
		letter-spacing: 0.01em;
		margin-bottom: 0.35rem;
	}

	/* Thinking dots */
	.thinking-dots {
		display: flex;
		gap: 5px;
		align-items: center;
		padding: 0.4rem 0;
	}

	.thinking-dots span {
		display: block;
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background: var(--muted-foreground);
		animation: thinking-bounce 1.4s ease-in-out infinite;
		opacity: 0.5;
	}

	.thinking-dots span:nth-child(2) { animation-delay: 0.18s; }
	.thinking-dots span:nth-child(3) { animation-delay: 0.36s; }

	@keyframes thinking-bounce {
		0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
		30%           { transform: translateY(-5px); opacity: 1; }
	}

	/* User message — right-aligned pill */
	.user-msg {
		display: flex;
		justify-content: flex-end;
		padding-left: 5rem;
	}

	.user-bubble {
		position: relative;
		font-size: 0.95rem;
		line-height: 1.6;
		color: var(--foreground);
		padding: 0.7rem 1rem;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 1rem 1rem 0.2rem 1rem;
		max-width: 30rem;
		white-space: pre-wrap;
		word-wrap: break-word;
	}

	/* Error */
	.error-msg {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.55rem 0.8rem;
		background: color-mix(in oklch, var(--destructive) 8%, transparent);
		border: 1px solid color-mix(in oklch, var(--destructive) 28%, transparent);
		color: var(--destructive);
		font-size: 0.7rem;
		border-radius: 0.4rem;
	}

	.retry {
		margin-left: auto;
		color: var(--destructive);
		text-decoration: underline;
		text-underline-offset: 2px;
	}

	/* ── Composer ───────────────────────────────────────────── */
	.composer-wrap {
		flex-shrink: 0;
		padding: 0.75rem 1.5rem 1.25rem;
	}

	.composer {
		max-width: 42rem;
		margin: 0 auto;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.875rem;
		padding: 0.9rem 1rem 0.7rem 1.1rem;
		transition: border-color 200ms ease, box-shadow 200ms ease;
	}

	.composer:focus-within {
		border-color: color-mix(in oklch, var(--primary) 50%, var(--border));
		box-shadow: 0 0 0 3px color-mix(in oklch, var(--primary) 10%, transparent);
	}

	/* Critical: kill the global outline-ring/50 on the textarea itself */
	.composer-input {
		width: 100%;
		border: 0;
		outline: none !important;
		box-shadow: none !important;
		resize: none;
		background: transparent;
		color: var(--foreground);
		font-family: var(--font-sans);
		font-size: 0.95rem;
		line-height: 1.55;
		min-height: 1.55rem;
		max-height: 200px;
	}

	.composer-input::placeholder {
		color: color-mix(in oklch, var(--foreground) 28%, transparent);
		font-style: normal;
	}

	.composer-input:disabled {
		color: color-mix(in oklch, var(--foreground) 35%, transparent);
	}

	.composer-foot {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-top: 0.55rem;
	}

	.hint {
		font-size: 0.6rem;
		color: color-mix(in oklch, var(--foreground) 28%, transparent);
		letter-spacing: 0.03em;
		display: flex;
		align-items: center;
		gap: 0.2rem;
	}

	kbd {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 0.05rem 0.3rem;
		border-radius: 0.2rem;
		background: color-mix(in oklch, var(--foreground) 8%, transparent);
		border: 1px solid color-mix(in oklch, var(--foreground) 12%, transparent);
		font-family: var(--font-mono);
		font-size: 0.6rem;
		line-height: 1.4;
	}

	.send-btn {
		width: 28px;
		height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 50%;
		background: var(--primary);
		color: var(--primary-foreground);
		flex-shrink: 0;
		transition: filter 150ms ease, transform 150ms ease, background 150ms ease;
	}

	.send-btn:hover:not(:disabled) {
		filter: brightness(1.07);
		transform: scale(1.05);
	}

	.send-btn:active:not(:disabled) {
		transform: scale(0.97);
	}

	.send-btn:disabled {
		background: color-mix(in oklch, var(--foreground) 10%, transparent);
		color: color-mix(in oklch, var(--foreground) 35%, transparent);
		cursor: not-allowed;
	}
</style>
