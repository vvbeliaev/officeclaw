<script lang="ts">
	import { page } from '$app/state';
	import { Icon } from '$lib/icons';

	type Props = {
		workspaceId: string;
		counts: {
			skills: number;
			envs: number;
			channels: number;
			mcp: number;
			knowledge: number;
			prompts: number;
			crons: number;
		};
	};

	let { workspaceId, counts }: Props = $props();

	const items: { href: string; label: string; icon: string; count: number | null }[] = $derived([
		{ href: `/w/${workspaceId}/workspace/skills`, label: 'Skills', icon: 'oc:tool', count: counts.skills },
		{ href: `/w/${workspaceId}/workspace/environments`, label: 'Environments', icon: 'oc:configure', count: counts.envs },
		{ href: `/w/${workspaceId}/workspace/channels`, label: 'Channels', icon: 'oc:log', count: counts.channels },
		{ href: `/w/${workspaceId}/workspace/mcp`, label: 'MCP Servers', icon: 'oc:memory', count: counts.mcp },
		{ href: `/w/${workspaceId}/workspace/cron`, label: 'Cron', icon: 'tabler:clock', count: counts.crons },
		{ href: `/w/${workspaceId}/workspace/knowledge`, label: 'Knowledge', icon: 'oc:memory', count: counts.knowledge },
		{ href: `/w/${workspaceId}/prompts`, label: 'Prompts', icon: 'tabler:file-text', count: counts.prompts }
	]);

	function isActive(href: string): boolean {
		return page.url.pathname.startsWith(href);
	}
</script>

<nav class="workspace-nav">
	{#each items as item}
		{@const active = isActive(item.href)}
		<a href={item.href} class="item" class:active>
			<Icon icon={item.icon} width={14} height={14} class="item-icon" />
			<span class="label">{item.label}</span>
			{#if item.count !== null}
				<span class="count font-mono" class:muted={item.count === 0}>
					{item.count === 0 ? '–' : item.count}
				</span>
			{/if}
		</a>
	{/each}
</nav>

<style>
	.workspace-nav {
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
		padding: 0 0.25rem;
	}

	.item {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		padding: 0.4rem 0.75rem;
		border-radius: 0.25rem;
		color: color-mix(in oklch, var(--sidebar-foreground) 55%, transparent);
		font-size: 0.8rem;
		text-decoration: none;
		transition: color 150ms ease, background 150ms ease;
	}

	.item:hover {
		color: var(--sidebar-foreground);
		background: color-mix(in oklch, var(--sidebar-accent) 50%, transparent);
	}

	.item.active {
		color: var(--sidebar-foreground);
		background: var(--sidebar-accent);
	}

	.label {
		flex: 1;
		letter-spacing: 0.005em;
	}

	.count {
		font-size: 0.65rem;
		color: color-mix(in oklch, var(--sidebar-foreground) 40%, transparent);
		font-variant-numeric: tabular-nums;
	}

	.count.muted {
		color: color-mix(in oklch, var(--sidebar-foreground) 25%, transparent);
	}
</style>
