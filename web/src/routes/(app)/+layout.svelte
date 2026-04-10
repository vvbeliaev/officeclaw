<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { authClient } from '$lib/auth-client';
	import { Icon } from '$lib/icons';
	import AgentSidebarCard from '$lib/components/agent-sidebar-card.svelte';
	import WorkspaceNav from '$lib/components/workspace-nav.svelte';

	let { data, children } = $props();

	type AgentStatus = 'running' | 'idle' | 'error';

	async function signOut() {
		await authClient.signOut();
		goto(resolve('/auth'));
	}

	const activeAgentId = $derived(
		page.url.pathname.startsWith('/agents/') ? page.params.id : undefined
	);

	const initials = $derived(
		data.user?.name
			?.split(' ')
			.map((n: string) => n[0])
			.join('')
			.slice(0, 2)
			.toUpperCase() ?? '?'
	);
</script>

<div class="shell">
	<aside class="sidebar">
		<!-- Logo -->
		<header class="logo-row">
			<div class="logo-mark">
				<Icon icon="oc:claw" width={13} height={13} />
			</div>
			<span class="logo-text">
				Office<span class="logo-bold">Claw</span>
			</span>
		</header>

		<div class="scroll">
			<!-- Fleet section -->
			<section class="section">
				<div class="section-head">
					<span class="section-label font-mono">fleet</span>
					<button class="section-spawn" type="button" aria-label="Spawn agent">
						<Icon icon="oc:spawn" width={12} height={12} />
					</button>
				</div>

				{#if data.agents.length === 0}
					<p class="empty">
						Bootstrap pending<span class="blink">…</span>
					</p>
				{:else}
					<div class="agent-list">
						{#each data.agents as agent (agent.id)}
							<AgentSidebarCard
								id={agent.id}
								name={agent.name}
								status={agent.status as AgentStatus}
								isAdmin={agent.isAdmin}
								active={activeAgentId === agent.id}
							/>
						{/each}
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
				<WorkspaceNav counts={data.workspaceCounts} />
			</section>
		</div>

		<!-- User footer -->
		<footer class="user-footer">
			<div class="user-row">
				<div class="user-avatar">{initials}</div>
				<div class="user-meta">
					<p class="user-name">{data.user?.name ?? 'User'}</p>
					<p class="user-email">{data.user?.email ?? ''}</p>
				</div>
			</div>
			<button class="signout" onclick={signOut}>
				<Icon icon="tabler:logout" width={12} height={12} />
				Sign out
			</button>
		</footer>
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

	.logo-mark {
		width: 28px;
		height: 28px;
		background: var(--primary);
		color: var(--primary-foreground);
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		clip-path: polygon(0 0, 100% 0, 100% 75%, 75% 100%, 0 100%);
	}

	.logo-text {
		font-size: 0.875rem;
		letter-spacing: -0.01em;
		color: var(--sidebar-foreground);
		font-weight: 400;
	}

	.logo-bold {
		font-weight: 600;
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

	/* ── User footer ─────────────────────────────────────────── */
	.user-footer {
		border-top: 1px solid var(--sidebar-border);
		padding: 0.75rem;
		flex-shrink: 0;
	}

	.user-row {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		padding: 0.3rem 0.5rem;
		margin-bottom: 0.25rem;
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

	.signout {
		width: 100%;
		display: flex;
		align-items: center;
		gap: 0.45rem;
		padding: 0.35rem 0.7rem;
		font-size: 0.68rem;
		border-radius: 0.25rem;
		color: color-mix(in oklch, var(--sidebar-foreground) 45%, transparent);
		transition:
			color 150ms ease,
			background 150ms ease;
	}

	.signout:hover {
		color: var(--sidebar-foreground);
		background: var(--sidebar-accent);
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
