<script lang="ts">
	import { SvelteSet } from 'svelte/reactivity';
	import { resolve } from '$app/paths';
	import { applyAction } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import AgentAvatar from '$lib/components/agent-avatar.svelte';
	import CodeEditor from '$lib/components/code-editor.svelte';
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
	let selectedPath = $state<string | null>(null);

	function findNode(nodes: TreeNode[], path: string): TreeNode | null {
		for (const n of nodes) {
			if (n.fullPath === path) return n;
			const found = findNode(n.children, path);
			if (found) return found;
		}
		return null;
	}

	const selectedFile = $derived(selectedPath ? findNode(tree, selectedPath) : null);

	// Track dirty (unsaved) content per path
	let dirtyContent = $state<Record<string, string>>({});
	let saving = $state(false);
	let saveError = $state<string | null>(null);
	let savedPath = $state<string | null>(null);

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

	// Current editor content: dirty version if exists, else DB version
	const editorContent = $derived(
		selectedFile
			? (dirtyContent[selectedFile.fullPath] ?? selectedFile.content ?? '')
			: ''
	);

	const isDirty = $derived(
		selectedFile != null &&
		selectedFile.fullPath in dirtyContent &&
		dirtyContent[selectedFile.fullPath] !== (selectedFile.content ?? '')
	);

	function onEditorChange(content: string) {
		if (!selectedFile) return;
		dirtyContent = { ...dirtyContent, [selectedFile.fullPath]: content };
	}

	async function saveFile(content: string) {
		if (!selectedFile) return;
		saving = true;
		saveError = null;
		savedPath = null;

		const form = new FormData();
		form.set('path', selectedFile.fullPath);
		form.set('content', content);

		const res = await fetch('?/save', { method: 'POST', body: form });
		const result = await res.json();
		await applyAction(result);

		if (result.type === 'failure') {
			saveError = result.data?.error ?? 'Save failed';
		} else {
			const path = selectedFile.fullPath;
			const { [path]: _, ...rest } = dirtyContent;
			dirtyContent = rest;
			savedPath = path;
			setTimeout(() => { savedPath = null; }, 2000);
			await invalidateAll();
		}
		saving = false;
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
					<div class="file-actions">
						{#if saveError}
							<span class="save-error font-mono">{saveError}</span>
						{:else if savedPath === selectedFile.fullPath}
							<span class="save-ok font-mono">saved</span>
						{:else if isDirty}
							<span class="save-hint font-mono">unsaved</span>
						{/if}
						<button
							class="save-btn font-mono"
							class:dirty={isDirty}
							disabled={saving || !isDirty}
							onclick={() => saveFile(dirtyContent[selectedFile!.fullPath])}
						>
							{#if saving}
								<span class="spinner"></span>
							{:else}
								<Icon icon="tabler:device-floppy" width={12} height={12} />
							{/if}
							<span>Save</span>
						</button>
					</div>
				</div>
				<div class="editor-wrap">
					{#key selectedFile.fullPath}
						<CodeEditor
							path={selectedFile.fullPath}
							content={editorContent}
							onsave={saveFile}
							onchange={onEditorChange}
						/>
					{/key}
				</div>
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
				class:dirty={node.fullPath in dirtyContent && dirtyContent[node.fullPath] !== (node.content ?? '')}
				style="padding-left: {0.6 + depth * 1.1}rem"
				onclick={() => { selectedPath = node.fullPath; }}
			>
				<Icon icon={extIcon(node.name)} width={12} height={12} class="tree-icon" />
				<span class="tree-name">{node.name}</span>
				{#if node.fullPath in dirtyContent && dirtyContent[node.fullPath] !== (node.content ?? '')}
					<span class="dirty-dot"></span>
				{/if}
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

	.dirty-dot {
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background: var(--primary);
		flex-shrink: 0;
		opacity: 0.7;
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
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.45rem 0.75rem 0.45rem 1rem;
		border-bottom: 1px solid var(--border);
		background: var(--card);
		gap: 0.75rem;
	}

	.file-content-path {
		font-size: 0.68rem;
		color: var(--muted-foreground);
		letter-spacing: 0.01em;
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.file-actions {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-shrink: 0;
	}

	.save-hint {
		font-size: 0.62rem;
		color: var(--muted-foreground);
		opacity: 0.55;
		letter-spacing: 0.04em;
	}

	.save-ok {
		font-size: 0.62rem;
		color: var(--primary);
		opacity: 0.8;
		letter-spacing: 0.04em;
	}

	.save-error {
		font-size: 0.62rem;
		color: var(--destructive);
		letter-spacing: 0.02em;
	}

	.save-btn {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.28rem 0.65rem;
		font-size: 0.65rem;
		border-radius: 0.3rem;
		border: 1px solid var(--border);
		color: var(--muted-foreground);
		transition: background 150ms ease, color 150ms ease, border-color 150ms ease;
	}

	.save-btn.dirty {
		border-color: color-mix(in oklch, var(--primary) 40%, var(--border));
		color: var(--foreground);
	}

	.save-btn.dirty:hover {
		background: color-mix(in oklch, var(--primary) 10%, transparent);
		color: var(--primary);
		border-color: color-mix(in oklch, var(--primary) 60%, var(--border));
	}

	.save-btn:disabled {
		opacity: 0.35;
		cursor: not-allowed;
	}

	.spinner {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		border: 1.5px solid currentColor;
		border-right-color: transparent;
		animation: spin 0.7s linear infinite;
	}
	@keyframes spin { to { transform: rotate(360deg); } }

	.editor-wrap {
		flex: 1;
		overflow: hidden;
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
