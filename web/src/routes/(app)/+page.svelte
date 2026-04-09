<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Icon } from '$lib/icons';

	let { data } = $props();

	type AgentStatus = 'running' | 'idle' | 'error' | 'stopped' | 'pending';

	const statusIcon: Record<AgentStatus, string> = {
		running: 'oc:running',
		idle: 'oc:idle',
		error: 'oc:error',
		stopped: 'oc:stopped',
		pending: 'oc:pending'
	};

	const statusClass: Record<AgentStatus, string> = {
		running: 'text-status-running',
		idle: 'text-status-idle',
		error: 'text-status-error',
		stopped: 'text-status-stopped',
		pending: 'text-status-pending'
	};
</script>

<div class="flex flex-col h-full">
	<!-- Header -->
	<header class="h-14 flex items-center justify-between px-6 border-b border-border shrink-0">
		<h1 class="text-sm font-medium">Fleet</h1>
		<Button size="sm" class="gap-1.5 text-xs">
			<Icon icon="oc:spawn" width={13} height={13} />
			Spawn agent
		</Button>
	</header>

	<!-- Content -->
	<div class="flex-1 overflow-y-auto p-6">
		<!-- Session status banner -->
		<div
			class="mb-6 flex items-center gap-2.5 text-xs bg-muted/40 border border-border rounded px-4 py-2.5"
		>
			<div class="status-dot status-running shrink-0"></div>
			<span class="text-muted-foreground">
				Session active ·
				<span class="text-foreground font-medium">{data.user?.email}</span>
			</span>
			{#if (data.user as Record<string, unknown>)?.officeclawToken}
				<span class="ml-auto flex items-center gap-1.5 text-muted-foreground">
					<Icon icon="tabler:key" width={12} height={12} />
					Token active
				</span>
			{:else}
				<span class="ml-auto text-muted-foreground/60">Token pending bootstrap</span>
			{/if}
		</div>

		<!-- Agent grid or empty state -->
		{#if data.agents.length === 0}
			<div class="flex flex-col items-center justify-center py-28 text-center">
				<div
					class="w-12 h-12 bg-muted rounded-lg flex items-center justify-center mb-4 text-muted-foreground"
				>
					<Icon icon="oc:fleet" width={22} height={22} />
				</div>
				<p class="text-sm font-medium mb-1">No agents yet</p>
				<p class="text-xs text-muted-foreground mb-5 max-w-xs">
					Your Admin agent will appear here once bootstrap completes. You can also spawn agents
					manually.
				</p>
				<Button variant="outline" size="sm" class="gap-1.5 text-xs">
					<Icon icon="oc:spawn" width={13} height={13} />
					Spawn agent
				</Button>
			</div>
		{:else}
			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
				{#each data.agents as agent}
					{@const status = agent.status as AgentStatus}
					<div
						class="bg-card border border-border rounded-lg p-4 transition-colors hover:border-border/60
						       {status === 'running' ? 'card-running' : ''}"
					>
						<div class="flex items-start justify-between mb-3">
							<div class="flex items-center gap-2.5">
								<div
									class="w-8 h-8 bg-muted rounded flex items-center justify-center text-muted-foreground"
								>
									<Icon icon="oc:agent" width={15} height={15} />
								</div>
								<div>
									<p class="text-sm font-medium leading-tight">{agent.name}</p>
									{#if agent.isAdmin}
										<span class="text-xs text-muted-foreground">Admin</span>
									{/if}
								</div>
							</div>
							<div class="flex items-center gap-1.5 {statusClass[status]}">
								<Icon icon={statusIcon[status]} width={13} height={13} />
								<span class="text-xs capitalize">{status}</span>
							</div>
						</div>

						<p class="text-xs text-muted-foreground font-mono truncate mb-3">{agent.image}</p>

						<div class="pt-3 border-t border-border flex gap-2">
							<Button variant="outline" size="sm" class="flex-1 text-xs h-7 gap-1">
								<Icon icon="oc:open" width={12} height={12} />
								Open
							</Button>
							<Button variant="ghost" size="sm" class="text-xs h-7 gap-1 text-muted-foreground">
								<Icon icon="oc:log" width={12} height={12} />
								Logs
							</Button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
