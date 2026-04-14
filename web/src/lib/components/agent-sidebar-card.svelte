<script lang="ts">
	import { goto } from '$app/navigation';
	import AgentAvatar from './agent-avatar.svelte';
	import { Icon } from '$lib/icons';

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

	const statusClass = $derived(
		{
			running: 'status-running',
			idle: 'status-idle',
			error: 'status-error'
		}[status]
	);

	const statusLabel = $derived(
		{
			running: 'running',
			idle: 'idle',
			error: 'error'
		}[status]
	);
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
</a>

<style>
	.agent-card {
		position: relative;
		display: flex;
		align-items: center;
		gap: 0.7rem;
		padding: 0.5rem 0.75rem 0.5rem 0.9rem;
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

	/* ── Gear button ─────────────────────────────────────────── */
	.gear-btn {
		position: absolute;
		right: 0.55rem;
		top: 50%;
		transform: translateY(-50%);
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
</style>
