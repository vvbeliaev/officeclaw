<script lang="ts">
	import AgentAvatar from './agent-avatar.svelte';

	type AgentStatus = 'running' | 'idle' | 'error';

	type Props = {
		id: string;
		name: string;
		status: AgentStatus;
		isAdmin: boolean;
		active: boolean;
	};

	let { id, name, status, isAdmin, active }: Props = $props();

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
	href={`/agents/${id}`}
	class="agent-card"
	class:active
	aria-current={active ? 'page' : undefined}
>
	<span class="rail" aria-hidden="true"></span>

	<AgentAvatar {name} {isAdmin} size={34} />

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
</style>
