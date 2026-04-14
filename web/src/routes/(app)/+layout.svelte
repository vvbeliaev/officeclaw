<script lang="ts">
	import { page } from '$app/state';
	import { goto, invalidateAll } from '$app/navigation';
	import { onMount } from 'svelte';
	import { Icon } from '$lib/icons';
	import AgentSidebarCard from '$lib/components/agent-sidebar-card.svelte';
	import WorkspaceNav from '$lib/components/workspace-nav.svelte';
	import OfficeclawLogo from '$lib/components/officeclaw-logo.svelte';
	import WorkspaceSwitcher from '$lib/components/workspace-switcher.svelte';

	let { data, children } = $props();

	// `agents` and `workspaceCounts` come from the child [workspaceId] layout.
	// Parent layouts can't access child layout data via `data`, but page.data
	// is the fully-merged object — so we read those fields from there.
	type AgentEntry = {
		id: string;
		name: string;
		status: string;
		isAdmin: boolean;
		avatarUrl?: string | null;
		workspaceId: string;
	};
	type WorkspaceCounts = {
		skills: number;
		envs: number;
		channels: number;
		mcp: number;
		knowledge: number;
		prompts: number;
	};

	const agents = $derived(page.data.agents as AgentEntry[] | undefined);
	const workspaceCounts = $derived(page.data.workspaceCounts as WorkspaceCounts | undefined);

	type Theme = 'light' | 'dark' | 'sage';
	let theme = $state<Theme>('dark');

	onMount(() => {
		const saved = localStorage.getItem('oc-theme') as Theme | null;
		if (saved === 'light' || saved === 'dark' || saved === 'sage') theme = saved;
	});

	function setTheme(t: Theme) {
		theme = t;
		localStorage.setItem('oc-theme', t);
		const h = document.documentElement;
		h.classList.remove('dark', 'sage');
		if (t === 'dark') h.classList.add('dark');
		if (t === 'sage') h.classList.add('dark', 'sage');
	}

	type AgentStatus = 'running' | 'idle' | 'error';

	const workspaceId = $derived(page.params.workspaceId as string | undefined);

	const activeAgentId = $derived(
		page.url.pathname.includes('/agents/') ? page.params.id : undefined
	);

	const initials = $derived(
		data.user?.name
			?.split(' ')
			.map((n: string) => n[0])
			.join('')
			.slice(0, 2)
			.toUpperCase() ?? '?'
	);

	// ── Spawn agent ───────────────────────────────────────────
	let spawning = $state(false);
	let spawnName = $state('');
	let spawnInput: HTMLInputElement | null = $state(null);
	let spawnError: string | null = $state(null);
	let spawnLoading = $state(false);

	function openSpawn() {
		spawning = true;
		spawnName = '';
		spawnError = null;
		// Focus after DOM update
		setTimeout(() => spawnInput?.focus(), 0);
	}

	function cancelSpawn() {
		spawning = false;
		spawnName = '';
		spawnError = null;
	}

	async function createAgent() {
		const name = spawnName.trim();
		if (!name || spawnLoading) return;

		spawnLoading = true;
		spawnError = null;

		try {
			const res = await fetch('/api/agents', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ name, workspace_id: workspaceId })
			});

			if (!res.ok) {
				const text = await res.text();
				spawnError = text || `HTTP ${res.status}`;
				return;
			}

			const agent = await res.json();
			spawning = false;
			spawnName = '';
			await invalidateAll();
			goto(`/w/${workspaceId}/agents/${agent.id}`);
		} catch (err) {
			spawnError = err instanceof Error ? err.message : 'Failed to create agent';
		} finally {
			spawnLoading = false;
		}
	}

	function onSpawnKey(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			createAgent();
		} else if (e.key === 'Escape') {
			cancelSpawn();
		}
	}
</script>

<div class="shell">
	<aside class="sidebar">
		<!-- Logo -->
		<header class="logo-row">
			<OfficeclawLogo />
		</header>

		<div class="scroll">
			<!-- Fleet section -->
			<section class="section">
				<div class="section-head">
					<span class="section-label font-mono">fleet</span>
					<button
						class="section-spawn"
						class:active={spawning}
						type="button"
						aria-label="Spawn agent"
						onclick={openSpawn}
					>
						<Icon icon="oc:spawn" width={12} height={12} />
					</button>
				</div>

				{#if !agents || agents.length === 0 && !spawning}
					<p class="empty">
						Bootstrap pending<span class="blink">…</span>
					</p>
				{:else}
					<div class="agent-list">
						{#each agents as agent (agent.id)}
							<AgentSidebarCard
								id={agent.id}
								workspaceId={workspaceId ?? ''}
								name={agent.name}
								status={agent.status as AgentStatus}
								isAdmin={agent.isAdmin}
								avatarUrl={agent.avatarUrl}
								active={activeAgentId === agent.id}
							/>
						{/each}

						{#if spawning}
							<div class="spawn-form">
								<input
									bind:this={spawnInput}
									bind:value={spawnName}
									onkeydown={onSpawnKey}
									placeholder="agent name…"
									class="spawn-input font-mono"
									maxlength={64}
									disabled={spawnLoading}
								/>
								{#if spawnError}
									<p class="spawn-error font-mono">{spawnError}</p>
								{/if}
								<div class="spawn-actions">
									<button
										class="spawn-confirm font-mono"
										type="button"
										onclick={createAgent}
										disabled={!spawnName.trim() || spawnLoading}
									>
										{#if spawnLoading}
											<span class="spinner-sm"></span>creating…
										{:else}
											create ↵
										{/if}
									</button>
									<button
										class="spawn-cancel font-mono"
										type="button"
										onclick={cancelSpawn}
									>
										esc
									</button>
								</div>
							</div>
						{/if}
					</div>
				{/if}
			</section>

			<!-- Divider -->
			<div class="divider"></div>

			<!-- Workspace section -->
			<section class="section">
				<div class="section-head">
					<span class="section-label font-mono">workspace</span>
				</div>
				{#if workspaceId && workspaceCounts}
					<WorkspaceNav workspaceId={workspaceId} counts={workspaceCounts} />
				{/if}
			</section>
		</div>

		<!-- Workspace switcher -->
		<WorkspaceSwitcher
			workspaces={data.workspaces ?? []}
			activeWorkspaceId={workspaceId ?? ''}
		/>

		<!-- Theme switcher -->
		<div class="theme-row">
			<button
				class="theme-btn"
				class:active={theme === 'light'}
				onclick={() => setTheme('light')}
				title="Light"
			>
				<Icon icon="tabler:sun" width={13} height={13} />
			</button>
			<button
				class="theme-btn"
				class:active={theme === 'dark'}
				onclick={() => setTheme('dark')}
				title="Dark — Amber"
			>
				<Icon icon="tabler:moon" width={13} height={13} />
			</button>
			<button
				class="theme-btn sage"
				class:active={theme === 'sage'}
				onclick={() => setTheme('sage')}
				title="Dark — Sage"
			>
				<Icon icon="tabler:leaf" width={13} height={13} />
			</button>
		</div>

		<!-- User footer -->
		<a href="/profile" class="user-footer">
			<div class="user-avatar">{initials}</div>
			<div class="user-meta">
				<p class="user-name">{data.user?.name ?? 'User'}</p>
				<p class="user-email">{data.user?.email ?? ''}</p>
			</div>
			<Icon icon="tabler:chevron-right" width={13} height={13} class="user-chevron" />
		</a>
	</aside>

	<main class="main">
		{@render children()}
	</main>
</div>

<style>
	.shell {
		display: flex;
		min-height: 100vh;
	}

	.sidebar {
		width: 260px;
		flex-shrink: 0;
		display: flex;
		flex-direction: column;
		background: var(--sidebar);
		border-right: 1px solid var(--sidebar-border);
	}

	.logo-row {
		height: 56px;
		display: flex;
		align-items: center;
		gap: 0.65rem;
		padding: 0 1rem;
		border-bottom: 1px solid var(--sidebar-border);
		flex-shrink: 0;
	}

	.scroll {
		flex: 1;
		overflow-y: auto;
		padding: 1rem 0 0.5rem;
	}

	.section {
		padding-bottom: 0.5rem;
	}

	.section-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.25rem 1rem 0.5rem 1.1rem;
	}

	.section-label {
		font-size: 0.58rem;
		text-transform: uppercase;
		letter-spacing: 0.18em;
		color: color-mix(in oklch, var(--sidebar-foreground) 38%, transparent);
	}

	.section-spawn {
		width: 18px;
		height: 18px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 3px;
		color: color-mix(in oklch, var(--sidebar-foreground) 40%, transparent);
		transition:
			color 150ms ease,
			background 150ms ease;
	}

	.section-spawn:hover {
		color: var(--primary);
		background: color-mix(in oklch, var(--primary) 12%, transparent);
	}

	.section-spawn.active {
		color: var(--primary);
		background: color-mix(in oklch, var(--primary) 14%, transparent);
	}

	/* ── Spawn inline form ────────────────────────────────── */
	.spawn-form {
		margin: 0.1rem 0.25rem 0.25rem;
		padding: 0.55rem 0.7rem 0.5rem;
		background: color-mix(in oklch, var(--sidebar-accent) 50%, transparent);
		border: 1px solid color-mix(in oklch, var(--primary) 22%, var(--sidebar-border));
		border-radius: 0.35rem;
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
		animation: spawn-appear 120ms ease;
	}

	@keyframes spawn-appear {
		from {
			opacity: 0;
			transform: translateY(-4px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.spawn-input {
		width: 100%;
		background: transparent;
		border: none;
		outline: none;
		font-size: 0.78rem;
		color: var(--sidebar-foreground);
		letter-spacing: 0.01em;
	}

	.spawn-input::placeholder {
		color: color-mix(in oklch, var(--sidebar-foreground) 35%, transparent);
	}

	.spawn-input:disabled {
		opacity: 0.5;
	}

	.spawn-error {
		font-size: 0.62rem;
		color: var(--destructive);
		letter-spacing: 0.02em;
	}

	.spawn-actions {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		border-top: 1px solid color-mix(in oklch, var(--sidebar-border) 60%, transparent);
		padding-top: 0.35rem;
	}

	.spawn-confirm {
		display: flex;
		align-items: center;
		gap: 0.3rem;
		font-size: 0.6rem;
		letter-spacing: 0.06em;
		color: var(--primary);
		transition: opacity 150ms ease;
	}

	.spawn-confirm:disabled {
		opacity: 0.35;
		cursor: not-allowed;
	}

	.spawn-cancel {
		font-size: 0.6rem;
		letter-spacing: 0.06em;
		color: color-mix(in oklch, var(--sidebar-foreground) 35%, transparent);
		transition: color 150ms ease;
	}

	.spawn-cancel:hover {
		color: var(--sidebar-foreground);
	}

	.spinner-sm {
		display: inline-block;
		width: 8px;
		height: 8px;
		border-radius: 9999px;
		border: 1px solid currentColor;
		border-right-color: transparent;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.empty {
		font-size: 0.72rem;
		color: color-mix(in oklch, var(--sidebar-foreground) 40%, transparent);
		padding: 0.5rem 1.1rem;
		font-family: var(--font-mono);
	}

	.blink {
		animation: blink 1.4s ease-in-out infinite;
	}

	@keyframes blink {
		0%,
		100% {
			opacity: 0.25;
		}
		50% {
			opacity: 1;
		}
	}

	.agent-list {
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
	}

	.divider {
		height: 1px;
		margin: 0.5rem 1.1rem 0.75rem;
		background: var(--sidebar-border);
	}

	/* ── Theme switcher ──────────────────────────────────────── */
	.theme-row {
		display: flex;
		gap: 0.2rem;
		padding: 0.5rem 0.75rem;
		border-top: 1px solid var(--sidebar-border);
	}

	.theme-btn {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 0.38rem;
		border-radius: 0.3rem;
		color: color-mix(in oklch, var(--sidebar-foreground) 40%, transparent);
		transition:
			color 150ms ease,
			background 150ms ease;
	}

	.theme-btn:hover {
		color: var(--sidebar-foreground);
		background: var(--sidebar-accent);
	}

	.theme-btn.active {
		color: var(--sidebar-primary);
		background: color-mix(in oklch, var(--sidebar-primary) 14%, transparent);
	}

	.theme-btn.sage.active {
		color: oklch(0.72 0.14 148);
		background: color-mix(in oklch, oklch(0.72 0.14 148) 14%, transparent);
	}

	/* ── User footer ─────────────────────────────────────────── */
	.user-footer {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		padding: 0.6rem 0.75rem;
		border-top: 1px solid var(--sidebar-border);
		flex-shrink: 0;
		text-decoration: none;
		color: var(--sidebar-foreground);
		transition: background 150ms ease;
	}

	.user-footer:hover {
		background: var(--sidebar-accent);
	}

	.user-avatar {
		width: 28px;
		height: 28px;
		border-radius: 9999px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.65rem;
		font-weight: 600;
		background: color-mix(in oklch, var(--primary) 20%, transparent);
		color: var(--primary);
		flex-shrink: 0;
	}

	.user-meta {
		flex: 1;
		min-width: 0;
	}

	.user-name {
		font-size: 0.75rem;
		font-weight: 500;
		line-height: 1.1;
		color: var(--sidebar-foreground);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.user-email {
		font-size: 0.68rem;
		line-height: 1.1;
		margin-top: 0.15rem;
		color: color-mix(in oklch, var(--sidebar-foreground) 45%, transparent);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	:global(.user-chevron) {
		color: color-mix(in oklch, var(--sidebar-foreground) 28%, transparent);
		flex-shrink: 0;
		transition:
			color 150ms ease,
			transform 150ms ease;
	}

	.user-footer:hover :global(.user-chevron) {
		color: color-mix(in oklch, var(--sidebar-foreground) 55%, transparent);
		transform: translateX(2px);
	}

	/* ── Main ────────────────────────────────────────────────── */
	.main {
		flex: 1;
		display: flex;
		flex-direction: column;
		min-width: 0;
		overflow: hidden;
	}
</style>
