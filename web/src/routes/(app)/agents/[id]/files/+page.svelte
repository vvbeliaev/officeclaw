<script lang="ts">
	import { SvelteSet } from 'svelte/reactivity';
	import { resolve } from '$app/paths';
	import AgentAvatar from '$lib/components/agent-avatar.svelte';
	import { Icon } from '$lib/icons';

	let { data } = $props();

	type FileEntry = { path: string; content: string; updatedAt: Date };
	type TreeNode = {
		name: string;
		fullPath: string;
		type: 'dir' | 'file';
		content?: string;
		children: TreeNode[];
	};

	function buildTree(files: FileEntry[]): TreeNode[] {
		const root: TreeNode[] = [];
		for (const file of files) {
			const parts = file.path.replace(/^\//, '').split('/');
			let nodes = root;
			let accumulated = '';
			for (let i = 0; i < parts.length; i++) {
				const part = parts[i];
				accumulated += '/' + part;
				const isFile = i === parts.length - 1;
				let node = nodes.find((n) => n.name === part);
				if (!node) {
					node = {
						name: part,
						fullPath: accumulated,
						type: isFile ? 'file' : 'dir',
						children: [],
						...(isFile ? { content: file.content } : {})
					};
					nodes.push(node);
				}
				nodes = node.children;
			}
		}
		function sortNodes(ns: TreeNode[]): TreeNode[] {
			ns.sort((a, b) => {
				if (a.type !== b.type) return a.type === 'dir' ? -1 : 1;
				return a.name.localeCompare(b.name);
			});
			for (const n of ns) sortNodes(n.children);
			return ns;
		}
		return sortNodes(root);
	}

	const tree = $derived(buildTree(data.files ?? []));

	const expandedDirs = new SvelteSet<string>();
	let initialized = false;
	let selectedFile: TreeNode | null = $state(null);

	$effect(() => {
		if (!initialized && tree.length > 0) {
			initialized = true;
			function collectDirs(nodes: TreeNode[]) {
				for (const n of nodes) {
					if (n.type === 'dir') {
						expandedDirs.add(n.fullPath);
						collectDirs(n.children);
					}
				}
			}
			collectDirs(tree);
		}
	});

	function toggleDir(path: string) {
		if (expandedDirs.has(path)) expandedDirs.delete(path);
		else expandedDirs.add(path);
	}

	function extIcon(name: string): string {
		const ext = name.split('.').at(-1) ?? '';
		const map: Record<string, string> = {
			py: 'tabler:brand-python',
			md: 'tabler:markdown',
			txt: 'tabler:file-text',
			json: 'tabler:braces',
			yaml: 'tabler:file-code',
			yml: 'tabler:file-code',
			toml: 'tabler:file-code',
			sh: 'tabler:terminal-2',
			ts: 'tabler:brand-typescript',
			js: 'tabler:brand-javascript'
		};
		return map[ext] ?? 'tabler:file';
	}
</script>

<div class="files-shell">
	<!-- ── Header ──────────────────────────────────────────────── -->
	<header class="files-header">
		<div class="header-left">
			<a href={resolve(`/agents/${data.agent.id}`)} class="back-btn" aria-label="Back to chat">
				<Icon icon="tabler:arrow-left" width={14} height={14} />
				<span>Back</span>
			</a>
			<div class="header-divider"></div>
			<AgentAvatar name={data.agent.name} isAdmin={data.agent.isAdmin} size={28} />
			<h1 class="agent-name font-display">{data.agent.name}</h1>
		</div>
		<span class="files-label font-mono">files</span>
	</header>

	<!-- ── Body ────────────────────────────────────────────────── -->
	<div class="files-body">
		<aside class="file-tree">
			{#if tree.length === 0}
				<p class="tree-empty font-mono">no files yet</p>
			{:else}
				{@render treeNodes(tree, 0)}
			{/if}
		</aside>

		<div class="file-content">
			{#if selectedFile}
				<div class="file-content-header">
					<span class="file-content-path font-mono">{selectedFile.fullPath}</span>
				</div>
				<pre class="file-content-body font-mono">{selectedFile.content}</pre>
			{:else}
				<div class="file-content-empty">
					<Icon icon="tabler:file-search" width={28} height={28} />
					<p class="font-mono">select a file</p>
				</div>
			{/if}
		</div>
	</div>
</div>

{#snippet treeNodes(nodes: TreeNode[], depth: number)}
	{#each nodes as node (node.fullPath)}
		{#if node.type === 'dir'}
			<button
				class="tree-node tree-dir"
				style="padding-left: {0.6 + depth * 1.1}rem"
				onclick={() => toggleDir(node.fullPath)}
			>
				<Icon
					icon={expandedDirs.has(node.fullPath) ? 'tabler:folder-open' : 'tabler:folder'}
					width={12} height={12}
					class="tree-icon tree-icon-dir"
				/>
				<span class="tree-name">{node.name}</span>
			</button>
			{#if expandedDirs.has(node.fullPath)}
				{@render treeNodes(node.children, depth + 1)}
			{/if}
		{:else}
			<button
				class="tree-node tree-file"
				class:selected={selectedFile?.fullPath === node.fullPath}
				style="padding-left: {0.6 + depth * 1.1}rem"
				onclick={() => { selectedFile = node; }}
			>
				<Icon icon={extIcon(node.name)} width={12} height={12} class="tree-icon" />
				<span class="tree-name">{node.name}</span>
			</button>
		{/if}
	{/each}
{/snippet}

<style>
	.files-shell {
		display: flex;
		flex-direction: column;
		height: 100vh;
		background: var(--background);
	}

	/* ── Header ────────────────────────────────────────────── */
	.files-header {
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

	.back-btn {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.35rem 0.6rem;
		font-size: 0.7rem;
		border-radius: 0.3rem;
		color: var(--muted-foreground);
		transition: background 150ms ease, color 150ms ease;
	}
	.back-btn:hover {
		background: var(--muted);
		color: var(--foreground);
	}

	.header-divider {
		width: 1px;
		height: 16px;
		background: var(--border);
	}

	.agent-name {
		font-size: 1rem;
		font-variation-settings: 'opsz' 24, 'wght' 650;
		line-height: 1;
		letter-spacing: -0.01em;
	}

	.files-label {
		font-size: 0.65rem;
		letter-spacing: 0.1em;
		color: var(--muted-foreground);
		opacity: 0.55;
	}

	/* ── Body ──────────────────────────────────────────────── */
	.files-body {
		flex: 1;
		display: flex;
		min-height: 0;
		overflow: hidden;
	}

	/* ── Tree ──────────────────────────────────────────────── */
	.file-tree {
		width: 220px;
		flex-shrink: 0;
		overflow-y: auto;
		border-right: 1px solid var(--border);
		padding: 0.5rem 0;
	}

	.tree-empty {
		font-size: 0.68rem;
		color: var(--muted-foreground);
		padding: 0.75rem 0.9rem;
		opacity: 0.55;
	}

	.tree-node {
		display: flex;
		align-items: center;
		gap: 0.45rem;
		width: 100%;
		text-align: left;
		font-size: 0.72rem;
		padding-top: 0.28rem;
		padding-bottom: 0.28rem;
		padding-right: 0.6rem;
		color: var(--foreground);
		transition: background 120ms ease;
		white-space: nowrap;
		overflow: hidden;
	}

	.tree-node:hover { background: var(--muted); }

	.tree-file.selected {
		background: color-mix(in oklch, var(--primary) 10%, transparent);
		color: var(--primary);
	}

	.tree-name {
		overflow: hidden;
		text-overflow: ellipsis;
		flex: 1;
	}

	:global(.tree-icon) { flex-shrink: 0; opacity: 0.7; }
	:global(.tree-icon-dir) { color: var(--primary); opacity: 0.75; }

	/* ── Content ───────────────────────────────────────────── */
	.file-content {
		flex: 1;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.file-content-header {
		flex-shrink: 0;
		padding: 0.55rem 1rem;
		border-bottom: 1px solid var(--border);
		background: var(--card);
	}

	.file-content-path {
		font-size: 0.68rem;
		color: var(--muted-foreground);
		letter-spacing: 0.01em;
	}

	.file-content-body {
		flex: 1;
		overflow: auto;
		margin: 0;
		padding: 1rem 1.25rem;
		font-size: 0.76rem;
		line-height: 1.65;
		color: var(--foreground);
		white-space: pre;
		tab-size: 4;
	}

	.file-content-empty {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		color: var(--muted-foreground);
		opacity: 0.4;
	}

	.file-content-empty p {
		font-size: 0.7rem;
		letter-spacing: 0.04em;
	}
</style>
