<script lang="ts">
	import { tick } from 'svelte';
	import { invalidateAll } from '$app/navigation';
	import { Chat, type UIMessage } from '@ai-sdk/svelte';
	import { DefaultChatTransport } from 'ai';
	import AgentAvatar from '$lib/components/agent-avatar.svelte';
	import { Icon } from '$lib/icons';

	let { data } = $props();

	type LifecyclePhase = 'idle' | 'starting' | 'running' | 'stopping' | 'error';

	// Lifecycle phase is a client-side overlay on top of the server status.
	// Server `agent.status` is one of 'idle' | 'running' | 'error';
	// on top of that we add transient 'starting' / 'stopping' while a
	// request is in flight. `error` is sticky — it's cleared only when
	// the user dismisses or retries.
	let phaseOverride: LifecyclePhase | null = $state(null);
	let lifecycleError: string | null = $state(null);

	const phase: LifecyclePhase = $derived(
		phaseOverride ?? (data.agent.status as LifecyclePhase)
	);

	// Recreate the Chat instance whenever the user navigates to a different
	// agent. SvelteKit reuses the same +page.svelte component across param
	// changes, so we rebuild the chat (and its transport) per agent id.
	// `$derived` memoizes on data.agent.id, so one instance per agent.
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

	// Auto-grow composer
	function autoSize() {
		if (!composer) return;
		composer.style.height = 'auto';
		composer.style.height = Math.min(composer.scrollHeight, 180) + 'px';
	}
	$effect(() => {
		void [input];
		autoSize();
	});

	// Autoscroll on new messages / streaming
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

	// Extract plain text from a message's parts (v5 UIMessage schema).
	function messageText(m: UIMessage): string {
		return m.parts
			.filter((p): p is { type: 'text'; text: string } => p.type === 'text')
			.map((p) => p.text)
			.join('');
	}

	// ── Lifecycle actions ────────────────────────────────────
	// We write to `phaseOverride`, not `phase` (derived). On success
	// we drop the override so the derived phase falls through to the
	// freshly-loaded server status; on failure we keep it at 'error'.
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

	// Status dot variant mapping (CSS class suffix)
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
			<AgentAvatar name={data.agent.name} isAdmin={data.agent.isAdmin} size={32} />
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
					<Icon icon="oc:running" width={13} height={13} />
					<span>Start</span>
				</button>
			{:else if phase === 'starting'}
				<button class="lifecycle-btn transitioning" disabled>
					<span class="spinner"></span>
					<span>starting…</span>
				</button>
			{:else if phase === 'running'}
				<button class="lifecycle-btn stop" onclick={stopAgent}>
					<Icon icon="oc:stopped" width={12} height={12} />
					<span>Stop</span>
				</button>
			{:else if phase === 'stopping'}
				<button class="lifecycle-btn transitioning" disabled>
					<span class="spinner"></span>
					<span>stopping…</span>
				</button>
			{:else if phase === 'error'}
				<button class="lifecycle-btn retry" onclick={startAgent}>
					<Icon icon="oc:error" width={13} height={13} />
					<span>Retry start</span>
				</button>
			{/if}
			<div class="header-divider"></div>
			<button class="header-btn" aria-label="Agent scope" disabled={!isRunning}>
				<Icon icon="oc:tool" width={14} height={14} />
				<span>Scope</span>
			</button>
			<button class="header-btn" aria-label="Agent logs">
				<Icon icon="oc:log" width={14} height={14} />
				<span>Logs</span>
			</button>
		</div>
	</header>

	<!-- ── Lifecycle error banner ─────────────────────────────── -->
	{#if lifecycleError}
		<div class="lifecycle-error">
			<Icon icon="oc:error" width={14} height={14} />
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
					<AgentAvatar name={data.agent.name} isAdmin={data.agent.isAdmin} size={72} />

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
							<div class="agent-mark font-display">—</div>
							<div class="agent-body">
								<div class="agent-name-tag font-display">{data.agent.name}</div>
								<div class="prose">
									{text}{#if isStreaming && isLast}<span class="cursor">▮</span>{/if}
								</div>
							</div>
						</article>
					{/if}
				{/each}

				{#if chat.status === 'submitted' && chat.messages.at(-1)?.role === 'user'}
					<article class="msg agent-msg">
						<div class="agent-mark font-display">—</div>
						<div class="agent-body">
							<div class="agent-name-tag font-display">{data.agent.name}</div>
							<div class="thinking prose font-mono">thinking<span class="cursor">▮</span></div>
						</div>
					</article>
				{/if}

				{#if chat.error}
					<article class="msg error-msg font-mono">
						<Icon icon="oc:error" width={14} height={14} />
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
							sandbox stopping — composer paused
						{:else}
							⌘ + ⏎ to send
						{/if}
					</span>
					<button
						type="submit"
						class="send"
						disabled={isStreaming || !input.trim() || !isRunning}
					>
						{#if isStreaming}
							streaming<span class="cursor">▮</span>
						{:else}
							send
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
		height: 56px;
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 1.5rem;
		border-bottom: 1px solid var(--border);
		background: var(--background);
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 0.85rem;
	}

	.header-meta {
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
	}

	.agent-name {
		font-size: 1.125rem;
		font-style: italic;
		line-height: 1;
		letter-spacing: -0.005em;
	}

	.agent-sub {
		font-size: 0.68rem;
		display: flex;
		align-items: center;
		gap: 0.4rem;
		color: var(--muted-foreground);
	}

	.agent-sub .sep {
		opacity: 0.5;
	}

	.agent-sub .image {
		opacity: 0.75;
	}

	.header-actions {
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}

	.header-divider {
		width: 1px;
		height: 18px;
		background: var(--border);
		margin: 0 0.35rem;
	}

	.header-btn {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.4rem 0.7rem;
		font-size: 0.72rem;
		border-radius: 0.25rem;
		color: var(--muted-foreground);
		transition:
			background 150ms ease,
			color 150ms ease;
	}

	.header-btn:hover:not(:disabled) {
		background: var(--muted);
		color: var(--foreground);
	}

	.header-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	/* ── Lifecycle button (start/stop/retry) ──────────────── */
	.lifecycle-btn {
		display: flex;
		align-items: center;
		gap: 0.45rem;
		padding: 0.45rem 0.85rem;
		font-size: 0.72rem;
		font-family: var(--font-mono);
		letter-spacing: 0.02em;
		border-radius: 0.25rem;
		border: 1px solid transparent;
		transition:
			background 150ms ease,
			border-color 150ms ease,
			color 150ms ease,
			box-shadow 150ms ease;
	}

	.lifecycle-btn.start {
		background: var(--primary);
		color: var(--primary-foreground);
		box-shadow: 0 0 12px color-mix(in oklch, var(--primary) 30%, transparent);
	}

	.lifecycle-btn.start:hover {
		filter: brightness(1.08);
	}

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
		border-color: color-mix(in oklch, var(--primary) 30%, transparent);
		cursor: default;
	}

	.lifecycle-btn.retry {
		background: color-mix(in oklch, var(--destructive) 10%, transparent);
		color: var(--destructive);
		border-color: color-mix(in oklch, var(--destructive) 35%, transparent);
	}

	.lifecycle-btn.retry:hover {
		background: color-mix(in oklch, var(--destructive) 16%, transparent);
	}

	/* ── Spinner ──────────────────────────────────────────── */
	.spinner {
		width: 12px;
		height: 12px;
		border-radius: 9999px;
		border: 1.5px solid currentColor;
		border-right-color: transparent;
		animation: spin 0.8s linear infinite;
	}

	.spinner-mono {
		width: 10px;
		height: 10px;
		border-width: 1px;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* ── Lifecycle error banner ───────────────────────────── */
	.lifecycle-error {
		display: flex;
		align-items: flex-start;
		gap: 0.65rem;
		padding: 0.75rem 1.5rem;
		background: color-mix(in oklch, var(--destructive) 10%, transparent);
		border-bottom: 1px solid color-mix(in oklch, var(--destructive) 30%, transparent);
		color: var(--destructive);
	}

	.lifecycle-error-body {
		flex: 1;
		min-width: 0;
	}

	.lifecycle-error-title {
		font-size: 0.68rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		margin-bottom: 0.2rem;
	}

	.lifecycle-error-detail {
		font-family: var(--font-mono);
		font-size: 0.72rem;
		line-height: 1.45;
		margin: 0;
		white-space: pre-wrap;
		word-wrap: break-word;
		color: color-mix(in oklch, var(--destructive) 85%, var(--foreground));
	}

	.lifecycle-error-dismiss {
		flex-shrink: 0;
		font-size: 0.65rem;
		color: var(--destructive);
		text-decoration: underline;
		text-underline-offset: 3px;
		letter-spacing: 0.03em;
	}

	/* ── Canvas ───────────────────────────────────────────────── */
	.canvas {
		flex: 1;
		overflow-y: auto;
		padding: 3rem 1.5rem 2rem;
		scroll-behavior: smooth;
	}

	.thread {
		max-width: 42rem;
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 2rem;
	}

	/* ── Offline state (idle / starting / error) ─────────── */
	.offline-state {
		max-width: 36rem;
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
		font-size: 2.5rem;
		line-height: 1.05;
		letter-spacing: -0.01em;
		margin: 2rem 0 1rem;
	}

	.offline-title em {
		color: var(--primary);
	}

	.dot-dot-dot {
		display: inline-block;
		color: var(--primary);
		animation: dot-fade 1.4s ease-in-out infinite;
	}

	@keyframes dot-fade {
		0%,
		100% {
			opacity: 0.3;
		}
		50% {
			opacity: 1;
		}
	}

	.offline-sub {
		font-size: 0.92rem;
		line-height: 1.65;
		color: var(--muted-foreground);
		max-width: 28rem;
		margin-bottom: 2.25rem;
	}

	.offline-cta {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.7rem 1.25rem;
		background: var(--primary);
		color: var(--primary-foreground);
		font-family: var(--font-mono);
		font-size: 0.78rem;
		letter-spacing: 0.03em;
		border-radius: 0.3rem;
		box-shadow: 0 0 20px color-mix(in oklch, var(--primary) 30%, transparent);
		transition:
			filter 150ms ease,
			transform 150ms ease;
	}

	.offline-cta:hover {
		filter: brightness(1.08);
		transform: translateY(-1px);
	}

	.offline-cta:active {
		transform: translateY(0);
	}

	/* ── Boot log (starting state) ────────────────────────── */
	.boot-log {
		background: color-mix(in oklch, var(--muted) 50%, transparent);
		border: 1px solid var(--border);
		border-radius: 0.3rem;
		padding: 1rem 1.25rem;
		font-size: 0.72rem;
		line-height: 1.9;
		color: var(--muted-foreground);
		text-align: left;
		min-width: 18rem;
	}

	.boot-line {
		display: flex;
		align-items: center;
		gap: 0.55rem;
	}

	.boot-line.active {
		color: var(--primary);
	}

	.boot-line.pending {
		opacity: 0.4;
	}

	.tick {
		font-family: var(--font-mono);
		width: 10px;
		text-align: center;
		color: color-mix(in oklch, var(--status-running) 80%, transparent);
	}

	.boot-line.pending .tick {
		color: var(--muted-foreground);
	}

	/* ── Intro ────────────────────────────────────────────── */
	.intro {
		padding: 2rem 0 1rem;
		border-bottom: 1px solid var(--border);
		margin-bottom: 1rem;
	}

	.intro-title {
		font-size: 2.75rem;
		line-height: 1;
		letter-spacing: -0.01em;
		margin-bottom: 1rem;
	}

	.intro-title em {
		color: var(--primary);
	}

	.intro-sub {
		font-size: 0.95rem;
		line-height: 1.6;
		color: var(--muted-foreground);
		max-width: 36rem;
	}

	/* ── Messages (editorial — no bubbles) ───────────────────── */
	.msg {
		position: relative;
	}

	.agent-msg {
		display: grid;
		grid-template-columns: 1.5rem 1fr;
		gap: 1rem;
		align-items: start;
	}

	.agent-mark {
		font-size: 1.5rem;
		line-height: 1;
		color: var(--primary);
		opacity: 0.9;
		padding-top: 0.1rem;
		user-select: none;
	}

	.agent-name-tag {
		font-size: 0.72rem;
		font-style: italic;
		color: color-mix(in oklch, var(--primary) 60%, var(--foreground));
		letter-spacing: 0.01em;
		margin-bottom: 0.45rem;
	}

	.prose {
		font-size: 0.98rem;
		line-height: 1.65;
		color: var(--foreground);
		white-space: pre-wrap;
		word-wrap: break-word;
	}

	.thinking {
		font-size: 0.78rem;
		color: var(--muted-foreground);
		letter-spacing: 0.02em;
	}

	/* User messages: right outdent, warm quote treatment */
	.user-msg {
		display: flex;
		justify-content: flex-end;
		padding-left: 4rem;
	}

	.user-bubble {
		position: relative;
		font-size: 0.95rem;
		line-height: 1.55;
		color: var(--foreground);
		padding: 0.75rem 1rem 0.75rem 1.25rem;
		background: color-mix(in oklch, var(--muted) 70%, transparent);
		border-radius: 0.35rem 0.35rem 0 0.35rem;
		max-width: 32rem;
		white-space: pre-wrap;
		word-wrap: break-word;
		border-right: 2px solid color-mix(in oklch, var(--primary) 35%, transparent);
	}

	/* Streaming cursor */
	.cursor {
		display: inline-block;
		color: var(--primary);
		animation: cursor-blink 1s ease-in-out infinite;
		margin-left: 2px;
		font-family: var(--font-mono);
	}

	@keyframes cursor-blink {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.2;
		}
	}

	/* Chat-level error */
	.error-msg {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.6rem 0.85rem;
		background: color-mix(in oklch, var(--destructive) 8%, transparent);
		border: 1px solid color-mix(in oklch, var(--destructive) 30%, transparent);
		color: var(--destructive);
		font-size: 0.72rem;
		border-radius: 0.25rem;
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
		padding: 1rem 1.5rem 1.5rem;
		background: linear-gradient(
			to top,
			var(--background) 30%,
			color-mix(in oklch, var(--background) 0%, transparent)
		);
	}

	.composer {
		max-width: 42rem;
		margin: 0 auto;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.4rem;
		padding: 0.85rem 1rem 0.6rem;
		transition:
			border-color 150ms ease,
			box-shadow 150ms ease;
	}

	.composer:focus-within {
		border-color: color-mix(in oklch, var(--primary) 55%, var(--border));
		box-shadow: 0 0 0 3px color-mix(in oklch, var(--primary) 14%, transparent);
	}

	.composer textarea {
		width: 100%;
		border: 0;
		outline: 0;
		resize: none;
		background: transparent;
		color: var(--foreground);
		font-family: var(--font-sans);
		font-size: 0.95rem;
		line-height: 1.5;
		min-height: 1.5rem;
		max-height: 180px;
	}

	.composer textarea::placeholder {
		color: color-mix(in oklch, var(--foreground) 30%, transparent);
		font-family: var(--font-mono);
		font-size: 0.85rem;
		font-style: normal;
	}

	.composer textarea:disabled {
		color: color-mix(in oklch, var(--foreground) 40%, transparent);
	}

	.composer-foot {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-top: 0.5rem;
		padding-top: 0.5rem;
		border-top: 1px solid color-mix(in oklch, var(--border) 70%, transparent);
	}

	.hint {
		font-size: 0.62rem;
		color: color-mix(in oklch, var(--foreground) 35%, transparent);
		letter-spacing: 0.03em;
	}

	.send {
		font-size: 0.72rem;
		font-family: var(--font-mono);
		padding: 0.4rem 0.85rem;
		border-radius: 0.25rem;
		background: var(--primary);
		color: var(--primary-foreground);
		transition:
			filter 150ms ease,
			background 150ms ease;
		letter-spacing: 0.03em;
	}

	.send:hover:not(:disabled) {
		filter: brightness(1.05);
	}

	.send:disabled {
		background: color-mix(in oklch, var(--foreground) 10%, transparent);
		color: color-mix(in oklch, var(--foreground) 40%, transparent);
		cursor: not-allowed;
	}
</style>
