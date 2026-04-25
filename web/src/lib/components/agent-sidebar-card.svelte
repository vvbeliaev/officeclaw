<script lang="ts">
	import { goto } from '$app/navigation';
	import AgentAvatar from './agent-avatar.svelte';
	import { Icon } from '$lib/icons';
	import { agentLifecycle } from '$lib/stores/agent-lifecycle.svelte';

	type AgentStatus = 'running' | 'idle' | 'error';

	type Props = {
		id: string;
		workspaceId: string;
		name: string;
		status: AgentStatus;
		isAdmin: boolean;
		avatarUrl?: string | null;
		active: boolean;
	};

	let { id, workspaceId, name, status, isAdmin, avatarUrl = null, active }: Props = $props();

	const transitional = $derived(agentLifecycle.get(id));

	type DisplayPhase = 'idle' | 'starting' | 'running' | 'stopping' | 'error';

	const phase: DisplayPhase = $derived(
		transitional ? (transitional.phase as DisplayPhase) : (status as DisplayPhase)
	);

	const statusClass = $derived(
		{
			running: 'status-running',
			idle: 'status-idle',
			starting: 'status-pending',
			stopping: 'status-pending',
			error: 'status-error'
		}[phase]
	);

	const statusLabel = $derived(phase);

	function handlePower(e: MouseEvent) {
		e.preventDefault();
		e.stopPropagation();
		if (phase === 'idle') agentLifecycle.start(id);
		else if (phase === 'running') agentLifecycle.stop(id);
		else if (phase === 'error') {
			// Retry: dismiss the error and try start
			agentLifecycle.dismissError(id);
			agentLifecycle.start(id);
		}
	}

	const powerLabel = $derived(
		phase === 'running'
			? `Stop ${name}`
			: phase === 'idle'
				? `Start ${name}`
				: phase === 'error'
					? `Retry ${name}`
					: phase === 'starting'
						? 'Starting…'
						: 'Stopping…'
	);

	const isTransitioning = $derived(phase === 'starting' || phase === 'stopping');
</script>

<a
	href={`/w/${workspaceId}/agents/${id}`}
	class="agent-card"
	class:active
	aria-current={active ? 'page' : undefined}
>
	<span class="rail" aria-hidden="true"></span>

	<AgentAvatar {name} {isAdmin} {avatarUrl} size={34} />

	<div class="meta">
		<div class="name-row">
			<span class="name font-display">{name}</span>
			{#if isAdmin}
				<span class="admin-tag">admin</span>
			{/if}
		</div>
		<div class="status-row">
			<span class="status-dot {statusClass}"></span>
			<span class="status-label font-mono">{statusLabel}</span>
		</div>
	</div>

	<div class="actions">
		<button
			class="gear-btn"
			aria-label="Agent settings"
			onclick={(e) => {
				e.preventDefault();
				e.stopPropagation();
				goto(`/w/${workspaceId}/agents/${id}/settings`);
			}}
		>
			<Icon icon="tabler:settings" width={12} height={12} />
		</button>

		<button
			class="power-btn power-{phase}"
			class:transitioning={isTransitioning}
			disabled={isTransitioning}
			aria-label={powerLabel}
			title={powerLabel}
			onclick={handlePower}
		>
			{#if isTransitioning}
				<span class="power-spinner"></span>
			{:else if phase === 'running'}
				<Icon icon="oc:stopped" width={11} height={11} />
			{:else if phase === 'error'}
				<Icon icon="tabler:refresh" width={11} height={11} />
			{:else}
				<Icon icon="oc:running" width={11} height={11} />
			{/if}
		</button>
	</div>
</a>

<style>
	.agent-card {
		position: relative;
		display: flex;
		align-items: center;
		gap: 0.7rem;
		padding: 0.5rem 0.55rem 0.5rem 0.9rem;
		margin: 0 0.25rem;
		border-radius: 0.375rem;
		color: var(--sidebar-foreground);
		text-decoration: none;
		transition: background 150ms ease, color 150ms ease;
	}

	.agent-card:hover {
		background: color-mix(in oklch, var(--sidebar-accent) 60%, transparent);
	}

	.agent-card.active {
		background: color-mix(in oklch, var(--primary) 7%, var(--sidebar-accent));
	}

	.rail {
		position: absolute;
		left: 0;
		top: 0.55rem;
		bottom: 0.55rem;
		width: 2px;
		background: transparent;
		border-radius: 2px;
		transition: background 200ms ease;
	}

	.agent-card.active .rail {
		background: var(--primary);
		box-shadow: 0 0 8px oklch(from var(--primary) l c h / 0.4);
	}

	.meta {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
	}

	.name-row {
		display: flex;
		align-items: baseline;
		gap: 0.4rem;
		min-width: 0;
	}

	.name {
		font-style: italic;
		font-size: 1rem;
		line-height: 1.1;
		color: var(--sidebar-foreground);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.admin-tag {
		font-size: 0.58rem;
		font-family: var(--font-mono);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--primary);
		padding: 0.05rem 0.3rem;
		border-radius: 2px;
		background: color-mix(in oklch, var(--primary) 14%, transparent);
		flex-shrink: 0;
	}

	.status-row {
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}

	.status-label {
		font-size: 0.625rem;
		color: color-mix(in oklch, var(--sidebar-foreground) 50%, transparent);
		letter-spacing: 0.02em;
	}

	/* ── Actions cluster ─────────────────────────────────────── */
	.actions {
		display: flex;
		align-items: center;
		gap: 0.2rem;
		flex-shrink: 0;
	}

	/* ── Gear button (hover-only) ────────────────────────────── */
	.gear-btn {
		width: 22px;
		height: 22px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 4px;
		color: color-mix(in oklch, var(--sidebar-foreground) 38%, transparent);
		opacity: 0;
		transition:
			opacity 120ms ease,
			color 120ms ease,
			background 120ms ease;
	}

	.agent-card:hover .gear-btn {
		opacity: 1;
	}

	.gear-btn:hover {
		color: var(--primary);
		background: color-mix(in oklch, var(--primary) 12%, transparent);
	}

	/* ── Power button ────────────────────────────────────────── */
	.power-btn {
		width: 24px;
		height: 24px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 999px;
		border: 1px solid transparent;
		transition:
			background 150ms ease,
			border-color 150ms ease,
			color 150ms ease,
			box-shadow 150ms ease,
			opacity 150ms ease,
			transform 150ms ease;
	}

	.power-btn:disabled {
		cursor: default;
	}

	/* idle: subtle, plays on hover */
	.power-idle {
		color: color-mix(in oklch, var(--sidebar-foreground) 45%, transparent);
		background: transparent;
		border-color: color-mix(in oklch, var(--sidebar-border) 80%, transparent);
	}

	.agent-card:hover .power-idle,
	.power-idle:focus-visible {
		color: var(--primary);
		border-color: color-mix(in oklch, var(--primary) 35%, transparent);
		background: color-mix(in oklch, var(--primary) 8%, transparent);
	}

	.power-idle:hover {
		transform: scale(1.06);
		box-shadow: 0 0 10px color-mix(in oklch, var(--primary) 22%, transparent);
	}

	/* running: always-visible green-ish dot, hover reveals stop intent */
	.power-running {
		color: var(--status-running, oklch(0.78 0.16 148));
		background: color-mix(in oklch, var(--status-running, oklch(0.78 0.16 148)) 12%, transparent);
		border-color: color-mix(in oklch, var(--status-running, oklch(0.78 0.16 148)) 30%, transparent);
		box-shadow: 0 0 8px color-mix(in oklch, var(--status-running, oklch(0.78 0.16 148)) 22%, transparent);
	}

	.power-running:hover {
		color: var(--destructive);
		background: color-mix(in oklch, var(--destructive) 12%, transparent);
		border-color: color-mix(in oklch, var(--destructive) 35%, transparent);
		box-shadow: 0 0 10px color-mix(in oklch, var(--destructive) 22%, transparent);
	}

	/* transitioning */
	.power-btn.transitioning {
		color: var(--primary);
		background: color-mix(in oklch, var(--primary) 10%, transparent);
		border-color: color-mix(in oklch, var(--primary) 28%, transparent);
	}

	/* error */
	.power-error {
		color: var(--destructive);
		background: color-mix(in oklch, var(--destructive) 10%, transparent);
		border-color: color-mix(in oklch, var(--destructive) 32%, transparent);
	}

	.power-error:hover {
		background: color-mix(in oklch, var(--destructive) 18%, transparent);
	}

	.power-spinner {
		width: 9px;
		height: 9px;
		border-radius: 9999px;
		border: 1.25px solid currentColor;
		border-right-color: transparent;
		animation: spin 0.75s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
