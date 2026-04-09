<script lang="ts">
	import { onMount } from 'svelte';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Card, CardContent, CardFooter, CardHeader } from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Separator } from '$lib/components/ui/separator';
	import { Avatar, AvatarFallback } from '$lib/components/ui/avatar';
	import { Switch } from '$lib/components/ui/switch';
	import { Tabs, TabsContent, TabsList, TabsTrigger } from '$lib/components/ui/tabs';
	import { Progress } from '$lib/components/ui/progress';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Icon from '@iconify/svelte';
	import { addCollection } from '@iconify/svelte';

	// Register custom OfficeClaw icons
	import ocIcons from '$lib/icons/oc.json';
	addCollection(ocIcons);

	let dark = $state(true);
	let mounted = $state(false);

	onMount(() => { mounted = true; });

	const agents = [
		{ id: 'AGT-001', name: 'Admin',   role: 'Fleet Manager',   status: 'running', tasks: 12, uptime: '6h 42m', tools: 8,  init: 'AD', model: 'sonnet-4-6' },
		{ id: 'AGT-002', name: 'Scout',   role: 'Web Research',    status: 'running', tasks: 4,  uptime: '2h 15m', tools: 3,  init: 'SC', model: 'haiku-4-5' },
		{ id: 'AGT-003', name: 'Scribe',  role: 'Content Writer',  status: 'idle',    tasks: 0,  uptime: '45m',    tools: 2,  init: 'SW', model: 'sonnet-4-6' },
		{ id: 'AGT-004', name: 'Coder',   role: 'Code Assistant',  status: 'pending', tasks: 2,  uptime: '—',      tools: 5,  init: 'CD', model: 'opus-4-6' },
		{ id: 'AGT-005', name: 'Analyst', role: 'Data Analysis',   status: 'error',   tasks: 0,  uptime: '12m',    tools: 4,  init: 'AN', model: 'sonnet-4-6' },
		{ id: 'AGT-006', name: 'Ops',     role: 'Infrastructure',  status: 'stopped', tasks: 0,  uptime: '—',      tools: 6,  init: 'OP', model: 'haiku-4-5' },
	];

	const statusIcon: Record<string, string> = {
		running: 'oc:running',
		idle: 'oc:idle',
		error: 'oc:error',
		stopped: 'oc:stopped',
		pending: 'oc:pending',
	};

	const statusLabel: Record<string, string> = {
		running: 'Running',
		idle:    'Idle',
		error:   'Error',
		stopped: 'Stopped',
		pending: 'Queued',
	};

	const logs = [
		{ time: '14:32:01', level: 'INFO',  msg: 'Scout agent initialized with 3 tools' },
		{ time: '14:32:04', level: 'INFO',  msg: 'Starting: web_search("typescript 5.4 changes")' },
		{ time: '14:32:07', level: 'DEBUG', msg: 'Fetching https://typescriptlang.org/docs/handbook' },
		{ time: '14:32:09', level: 'INFO',  msg: 'Extracted 2,841 tokens from source' },
		{ time: '14:32:11', level: 'WARN',  msg: 'Rate limit at 87% — throttling requests' },
		{ time: '14:32:14', level: 'INFO',  msg: 'Summary generated, writing to memory' },
		{ time: '14:32:16', level: 'ERROR', msg: 'write_memory failed: db connection timeout' },
		{ time: '14:32:18', level: 'INFO',  msg: 'Retrying (2/3)...' },
		{ time: '14:32:19', level: 'INFO',  msg: 'Write successful — task complete ✓' },
	];

	const lvlStyle: Record<string, string> = {
		INFO:  'text-[oklch(0.72_0.12_220)]',
		DEBUG: 'text-[oklch(0.55_0.014_242)]',
		WARN:  'text-[oklch(0.80_0.155_68)]',
		ERROR: 'text-[oklch(0.65_0.21_25)]',
	};
</script>

<div class={dark ? 'dark' : ''}>
<div class="min-h-screen bg-background text-foreground selection:bg-primary/20">

<!-- ── Topbar ──────────────────────────────────────────── -->
<header class="sticky top-0 z-50 border-b border-border bg-background/90 backdrop-blur-md">
	<div class="mx-auto flex max-w-6xl items-center gap-5 px-8 py-4">
		<!-- Wordmark -->
		<a href="/" class="flex items-center gap-3 no-underline">
			<!-- Icon mark: amber square with claw -->
			<div class="flex size-8 items-center justify-center bg-primary text-primary-foreground"
				style="clip-path: polygon(0 0, 100% 0, 100% 75%, 75% 100%, 0 100%)">
				<Icon icon="oc:claw" class="size-4" />
			</div>
			<!-- Wordmark: two weights, no serif, no italic -->
			<span class="text-sm font-sans">
				<span class="font-medium text-foreground tracking-tight">Office</span><span class="font-bold text-foreground tracking-tight">Claw</span>
			</span>
		</a>
		<Badge variant="outline" class="text-[10px] border-border/50 text-muted-foreground">design preview</Badge>
		<div class="ml-auto flex items-center gap-3">
			<span class="text-xs text-muted-foreground">dark</span>
			<Switch bind:checked={dark} />
		</div>
	</div>
</header>

<main class="mx-auto max-w-6xl px-8 pb-20 pt-14 space-y-18">

<!-- ── Hero ─────────────────────────────────────────────── -->
<section class="space-y-8">
	<!-- Eyebrow -->
	<div class="flex items-center gap-2">
		<div class="flex items-center gap-1.5 rounded-full border border-border/50 bg-card px-3 py-1.5 text-xs text-muted-foreground">
			<span class="status-dot status-running size-1.5"></span>
			<span>6 agents online</span>
		</div>
		<div class="flex items-center gap-1.5 rounded-full border border-border/50 bg-card px-3 py-1.5 text-xs text-muted-foreground">
			<Icon icon="oc:open" class="size-3 text-primary" />
			<span>open · no lock-in</span>
		</div>
	</div>

	<!-- Headline -->
	<div class="space-y-5">
		<h1 class="font-display text-[3.75rem] font-normal tracking-tight leading-[1.05] text-foreground">
			Your agents,<br><em class="text-primary">working.</em>
		</h1>
		<p class="max-w-md text-lg text-muted-foreground leading-relaxed">
			Spawn a fleet of AI agents, give them tools and goals, and let them run.
			No lock-in. No code required.
		</p>
	</div>

	<!-- CTAs -->
	<div class="flex flex-wrap items-center gap-4">
		<Button class="rounded-full glow-amber gap-2 px-6 h-10 text-sm">
			<Icon icon="oc:spawn" class="size-4" />
			Spawn your first agent
		</Button>
		<Button variant="outline" class="rounded-full gap-2 px-5 h-10 text-sm">
			<Icon icon="oc:fleet" class="size-4" />
			Browse templates
		</Button>
	</div>

	<!-- Stat strip -->
	<div class="flex flex-wrap gap-8 text-xs text-muted-foreground font-mono">
		<span>2 running</span>
		<span>18 tasks today</span>
		<span>claude-sonnet-4-6 · haiku-4-5</span>
		<span>free · open source</span>
	</div>
</section>

<Separator />

<!-- ── Fleet Grid ────────────────────────────────────────── -->
<section class="space-y-7">
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-3">
			<Icon icon="oc:fleet" class="size-5 text-muted-foreground" />
			<h2 class="text-lg font-semibold tracking-tight">Fleet</h2>
			<span class="text-sm text-muted-foreground font-mono">{agents.length} agents</span>
		</div>
		<div class="flex items-center gap-2">
			<Input placeholder="Search fleet..." class="h-8 w-44 text-xs" />
			<Button variant="outline" size="sm" class="h-8 gap-1.5 text-xs">
				<Icon icon="oc:configure" class="size-3.5" />
				Filter
			</Button>
			<Button size="sm" class="h-8 gap-1.5 rounded-full text-xs">
				<Icon icon="oc:spawn" class="size-3.5" />
				New
			</Button>
		</div>
	</div>

	<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
		{#each agents as a}
			<Card class={`group relative transition-all duration-200 hover:-translate-y-0.5 ${a.status === 'running' ? 'card-running' : ''} ${a.status === 'stopped' || a.status === 'error' ? 'opacity-60' : ''}`}>
				<CardHeader class="pb-3 pt-5 px-5">
					<div class="flex items-start justify-between">
						<div class="flex items-center gap-3">
							<Avatar class="size-9 rounded-md">
								<AvatarFallback class="rounded-md text-[10px] font-mono font-semibold bg-secondary text-secondary-foreground">
									{a.init}
								</AvatarFallback>
							</Avatar>
							<div>
								<p class="text-sm font-semibold leading-none">{a.name}</p>
								<p class="mt-1 text-xs text-muted-foreground">{a.role}</p>
							</div>
						</div>
						<div class="flex items-center gap-1.5 pt-0.5">
							<Icon
								icon={statusIcon[a.status]}
								class="size-3.5"
								style={`color: var(--status-${a.status})`}
							/>
							<span class="text-[11px] text-muted-foreground">{statusLabel[a.status]}</span>
						</div>
					</div>
				</CardHeader>

				<CardContent class="px-5 pb-4">
					<div class="flex items-center gap-3 text-xs font-mono text-muted-foreground">
						<span>{a.tasks} tasks</span>
						<span class="opacity-30">·</span>
						<span>{a.uptime}</span>
						<span class="opacity-30">·</span>
						<span>{a.tools} tools</span>
					</div>
					<div class="mt-2 flex items-center gap-2">
						<span class="text-[10px] font-mono text-muted-foreground/40">{a.id}</span>
						<span class="text-[10px] font-mono text-muted-foreground/30">{a.model}</span>
					</div>
				</CardContent>

				<CardFooter class="flex gap-1.5 px-5 pb-5 pt-0">
					<Button variant="ghost" size="sm" class="h-7 gap-1 px-2 text-xs">
						<Icon icon="oc:log" class="size-3" />
						Logs
					</Button>
					<Button variant="ghost" size="sm" class="h-7 gap-1 px-2 text-xs">
						<Icon icon="oc:configure" class="size-3" />
						Config
					</Button>
					{#if a.status === 'running'}
						<Button variant="destructive" size="sm" class="ml-auto h-7 gap-1 px-2 text-xs">
							<Icon icon="oc:stopped" class="size-3" />
							Stop
						</Button>
					{:else if a.status === 'idle' || a.status === 'stopped'}
						<Button size="sm" class="ml-auto h-7 gap-1 rounded-full px-3 text-xs">
							<Icon icon="oc:running" class="size-3" />
							Start
						</Button>
					{:else if a.status === 'error'}
						<Button variant="outline" size="sm" class="ml-auto h-7 gap-1 px-2 text-xs text-destructive border-destructive/30">
							Retry
						</Button>
					{/if}
				</CardFooter>
			</Card>
		{/each}
	</div>
</section>

<Separator />

<!-- ── Agent Detail ──────────────────────────────────────── -->
<section class="space-y-4">
	<div class="flex items-center gap-2.5">
		<Avatar class="size-8 rounded-md">
			<AvatarFallback class="rounded-md text-[10px] font-mono font-semibold bg-primary text-primary-foreground">SC</AvatarFallback>
		</Avatar>
		<div>
			<p class="text-sm font-medium">Scout</p>
			<p class="text-xs text-muted-foreground font-mono">AGT-002 · running · 2h 15m</p>
		</div>
		<div class="ml-auto">
			<span class="status-dot status-running size-2"></span>
		</div>
	</div>

	<Tabs value="logs">
		<TabsList class="h-8">
			<TabsTrigger value="logs" class="text-xs gap-1.5">
				<Icon icon="oc:log" class="size-3.5" />Logs
			</TabsTrigger>
			<TabsTrigger value="config" class="text-xs gap-1.5">
				<Icon icon="oc:configure" class="size-3.5" />Config
			</TabsTrigger>
			<TabsTrigger value="tools" class="text-xs gap-1.5">
				<Icon icon="oc:tool" class="size-3.5" />Tools
			</TabsTrigger>
			<TabsTrigger value="memory" class="text-xs gap-1.5">
				<Icon icon="oc:memory" class="size-3.5" />Memory
			</TabsTrigger>
		</TabsList>

		<!-- Logs tab -->
		<TabsContent value="logs" class="mt-3">
			<div class="surface-terminal p-4 space-y-1.5">
				{#each logs as l}
					<div class="flex gap-4">
						<span class="shrink-0 text-muted-foreground/60 tabular-nums">{l.time}</span>
						<span class={`shrink-0 w-11 ${lvlStyle[l.level]}`}>{l.level}</span>
						<span class="text-foreground/75">{l.msg}</span>
					</div>
				{/each}
				<div class="flex gap-4 mt-1">
					<span class="shrink-0 text-muted-foreground/40">14:32:20</span>
					<span class="w-11"></span>
					<span class="animate-pulse text-primary">▌</span>
				</div>
			</div>
		</TabsContent>

		<!-- Config tab -->
		<TabsContent value="config" class="mt-3">
			<Card>
				<CardContent class="pt-5 space-y-4">
					<div class="grid gap-4 sm:grid-cols-2">
						<div class="space-y-1.5">
							<Label class="text-xs">Model</Label>
							<Input value="claude-haiku-4-5" class="text-sm font-mono" />
						</div>
						<div class="space-y-1.5">
							<Label class="text-xs">Max tokens</Label>
							<Input value="4096" class="text-sm font-mono" />
						</div>
					</div>
					<div class="space-y-1.5">
						<Label class="text-xs">System prompt</Label>
						<Input value="You are a focused web research assistant. Find, summarize, save." class="text-sm" />
					</div>
					<Separator />
					<div class="space-y-3">
						{#each [
							{ label: 'Auto-restart on error', desc: 'Restart if agent crashes unexpectedly', on: true },
							{ label: 'Verbose logging', desc: 'Include DEBUG messages in log stream', on: false },
							{ label: 'Rate limit protection', desc: 'Throttle requests when quota is >80%', on: true },
						] as s}
							<div class="flex items-center justify-between">
								<div>
									<p class="text-xs font-medium">{s.label}</p>
									<p class="text-xs text-muted-foreground">{s.desc}</p>
								</div>
								<Switch checked={s.on} />
							</div>
						{/each}
					</div>
					<Button size="sm" class="rounded-full gap-1.5">Save changes</Button>
				</CardContent>
			</Card>
		</TabsContent>

		<!-- Tools tab -->
		<TabsContent value="tools" class="mt-3">
			<div class="space-y-2">
				{#each [
					{ name: 'web_search', desc: 'Search the web via DuckDuckGo', enabled: true },
					{ name: 'read_url',   desc: 'Fetch and parse a URL', enabled: true },
					{ name: 'write_memory', desc: 'Write to agent knowledge base', enabled: true },
					{ name: 'send_email', desc: 'Send email via SMTP', enabled: false },
				] as tool}
					<div class="flex items-center justify-between rounded-lg border border-border p-3">
						<div class="flex items-center gap-2.5">
							<div class="flex size-7 items-center justify-center rounded-md bg-secondary">
								<Icon icon="oc:tool" class="size-3.5 text-muted-foreground" />
							</div>
							<div>
								<p class="text-xs font-mono font-medium">{tool.name}</p>
								<p class="text-[11px] text-muted-foreground">{tool.desc}</p>
							</div>
						</div>
						<Switch checked={tool.enabled} />
					</div>
				{/each}
			</div>
		</TabsContent>

		<!-- Memory tab -->
		<TabsContent value="memory" class="mt-3">
			<Card>
				<CardContent class="pt-5 space-y-4">
					<div class="space-y-1.5">
						<div class="flex justify-between text-xs">
							<span class="text-muted-foreground">Context window</span>
							<span class="font-mono">68%  ·  69,632 / 100,000 tokens</span>
						</div>
						<Progress value={68} class="h-1.5" />
					</div>
					<div class="space-y-1.5">
						<div class="flex justify-between text-xs">
							<span class="text-muted-foreground">Knowledge entries</span>
							<span class="font-mono">12 / 50</span>
						</div>
						<Progress value={24} class="h-1.5" />
					</div>
					<Separator />
					<div class="space-y-1.5">
						{#each [
							'typescript-5.4-summary.md',
							'svelte-5-runes-notes.md',
							'tailwind-v4-migration.md',
						] as entry}
							<div class="flex items-center justify-between rounded-md border border-border/50 px-3 py-2">
								<div class="flex items-center gap-2">
									<Icon icon="oc:memory" class="size-3.5 text-muted-foreground" />
									<span class="text-xs font-mono">{entry}</span>
								</div>
								<span class="text-[10px] text-muted-foreground">2h ago</span>
							</div>
						{/each}
					</div>
				</CardContent>
			</Card>
		</TabsContent>
	</Tabs>
</section>

<Separator />

<!-- ── Palette ───────────────────────────────────────────── -->
<section class="space-y-10">
	<div>
		<h2 class="font-display text-3xl font-normal tracking-tight">
			Component <em class="text-primary">palette</em>
		</h2>
		<p class="mt-2 text-base text-muted-foreground">All building blocks. Toggle dark/light above.</p>
	</div>

	<!-- Typography showcase -->
	<div class="space-y-3 rounded-xl border border-border p-8">
		<p class="mb-4 text-[10px] font-medium uppercase tracking-widest text-muted-foreground">Typography</p>
		<p class="font-display text-5xl font-normal leading-tight tracking-tight">
			Your fleet, <em class="text-primary">always on.</em>
		</p>
		<p class="text-xl font-medium tracking-tight">Agent Configuration — Scout</p>
		<p class="text-base text-muted-foreground">
			Give your agents tools, memory, and a purpose. They run so you don't have to.
		</p>
		<p class="text-sm text-muted-foreground">Secondary text — metadata, timestamps, helper copy.</p>
		<div class="flex flex-wrap gap-4 pt-2 text-xs text-muted-foreground font-mono">
			<span class="text-primary">#AGT-002</span>
			<span>claude-haiku-4-5</span>
			<span>14:32:01 INFO</span>
			<span>2h 15m uptime</span>
		</div>
	</div>

	<!-- Buttons -->
	<div class="space-y-4">
		<p class="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">Buttons</p>
		<div class="flex flex-wrap gap-2">
			<Button class="rounded-full gap-2 glow-amber">
				<Icon icon="oc:spawn" class="size-4" />Spawn Agent
			</Button>
			<Button variant="secondary">Secondary</Button>
			<Button variant="outline" class="gap-2">
				<Icon icon="oc:configure" class="size-4" />Outline
			</Button>
			<Button variant="ghost">Ghost</Button>
			<Button variant="destructive" class="gap-2">
				<Icon icon="oc:stopped" class="size-4" />Stop
			</Button>
			<Button disabled>Disabled</Button>
			<Button size="sm">Small</Button>
			<Button size="lg" variant="outline" class="rounded-full">Large Pill</Button>
		</div>
	</div>

	<!-- Badges & Status -->
	<div class="space-y-3">
		<p class="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">Badges & Status</p>
		<div class="flex flex-wrap items-center gap-2">
			<Badge>Default</Badge>
			<Badge variant="secondary">Secondary</Badge>
			<Badge variant="outline">Outline</Badge>
			<Badge variant="destructive">Error</Badge>
			<!-- Custom status badges -->
			{#each ['running', 'idle', 'error', 'stopped', 'pending'] as s}
				<span
					class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-medium border"
					style="color:var(--status-{s}); border-color:color-mix(in oklch, var(--status-{s}) 30%, transparent); background:color-mix(in oklch, var(--status-{s}) 10%, transparent)"
				>
					<Icon icon={statusIcon[s]} class="size-3" />
					{statusLabel[s]}
				</span>
			{/each}
		</div>
	</div>

	<!-- Custom icons -->
	<div class="space-y-3">
		<p class="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">Icons — <span class="font-mono normal-case text-primary">oc:</span> collection</p>
		<div class="flex flex-wrap gap-1">
			{#each [
				{ icon: 'oc:agent',     label: 'agent' },
				{ icon: 'oc:fleet',     label: 'fleet' },
				{ icon: 'oc:claw',      label: 'claw' },
				{ icon: 'oc:tool',      label: 'tool' },
				{ icon: 'oc:memory',    label: 'memory' },
				{ icon: 'oc:running',   label: 'running' },
				{ icon: 'oc:idle',      label: 'idle' },
				{ icon: 'oc:stopped',   label: 'stopped' },
				{ icon: 'oc:error',     label: 'error' },
				{ icon: 'oc:pending',   label: 'pending' },
				{ icon: 'oc:configure', label: 'configure' },
				{ icon: 'oc:log',       label: 'log' },
				{ icon: 'oc:spawn',     label: 'spawn' },
				{ icon: 'oc:open',      label: 'open' },
			] as item}
				<div class="flex flex-col items-center gap-1.5 rounded-lg border border-border/50 p-3 w-[72px]">
					<Icon icon={item.icon} class="size-5 text-foreground" />
					<span class="text-[9px] font-mono text-muted-foreground text-center">{item.label}</span>
				</div>
			{/each}
		</div>
	</div>

	<!-- Inputs -->
	<div class="space-y-3">
		<p class="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">Inputs</p>
		<div class="grid gap-3 sm:grid-cols-3">
			<div class="space-y-1.5">
				<Label class="text-xs">Agent Name</Label>
				<Input placeholder="e.g. Scout, Scribe..." />
			</div>
			<div class="space-y-1.5">
				<Label class="text-xs">Model</Label>
				<Input placeholder="claude-sonnet-4-6" class="font-mono text-sm" />
			</div>
			<div class="space-y-1.5">
				<Label class="text-xs">Search Fleet</Label>
				<Input placeholder="Filter agents..." />
			</div>
		</div>
	</div>

	<!-- Colors -->
	<div class="space-y-3">
		<p class="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">Color Tokens</p>
		<div class="flex flex-wrap gap-2">
			{#each [
				{ l: 'Background', c: 'bg-background border border-border' },
				{ l: 'Card',       c: 'bg-card border border-border' },
				{ l: 'Secondary',  c: 'bg-secondary' },
				{ l: 'Muted',      c: 'bg-muted' },
				{ l: 'Primary',    c: 'bg-primary' },
				{ l: 'Destructive',c: 'bg-destructive' },
			] as sw}
				<div class="space-y-1.5">
					<div class={`size-10 rounded-md ${sw.c}`}></div>
					<p class="text-[10px] text-muted-foreground">{sw.l}</p>
				</div>
			{/each}
			{#each ['running','idle','error','stopped','pending'] as s}
				<div class="space-y-1.5">
					<div class="size-10 rounded-md" style="background:var(--status-{s})"></div>
					<p class="text-[10px] text-muted-foreground capitalize">{s}</p>
				</div>
			{/each}
		</div>
	</div>

	<!-- Skeletons -->
	<div class="space-y-3">
		<p class="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">Loading State</p>
		<div class="grid gap-3 sm:grid-cols-3">
			{#each [0,1,2] as _}
				<Card>
					<CardContent class="pt-4 space-y-3">
						<div class="flex gap-2.5">
							<Skeleton class="size-8 rounded-md" />
							<div class="space-y-1.5 flex-1">
								<Skeleton class="h-3 w-20" />
								<Skeleton class="h-2.5 w-14" />
							</div>
						</div>
						<Skeleton class="h-2.5 w-full" />
						<Skeleton class="h-2.5 w-2/3" />
					</CardContent>
				</Card>
			{/each}
		</div>
	</div>
</section>

</main>

<!-- ── Footer ────────────────────────────────────────────── -->
<footer class="border-t border-border px-8 py-7">
	<div class="mx-auto max-w-6xl flex items-center justify-between">
		<div class="flex items-center gap-2">
			<Icon icon="oc:claw" class="size-4 text-primary" />
			<span class="text-xs font-mono text-muted-foreground">OfficeClaw · Open Craft design system</span>
		</div>
		<span class="text-xs text-muted-foreground">Instrument Serif · DM Sans · DM Mono</span>
	</div>
</footer>

</div>
</div>
