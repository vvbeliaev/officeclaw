<script lang="ts">
	import { SvelteSet } from 'svelte/reactivity';
	import { deserialize } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
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
				// SKILL.md always first at root
				if (a.type === 'file' && a.name === 'SKILL.md') return -1;
				if (b.type === 'file' && b.name === 'SKILL.md') return 1;
				if (a.type !== b.type) return a.type === 'dir' ? -1 : 1;
				return a.name.localeCompare(b.name);
			});
			for (const n of ns) sortNodes(n.children);
			return ns;
		}
		return sortNodes(root);
	}

	let files = $state<FileEntry[]>([]);
	$effect(() => {
		files = data.files ?? [];
	});
	const tree = $derived(buildTree(files));

	const expandedDirs = new SvelteSet<string>();
	let initialized = false;
	let selectedPath = $state<string | null>('/SKILL.md');

	function findNode(nodes: TreeNode[], path: string): TreeNode | null {
		for (const n of nodes) {
			if (n.fullPath === path) return n;
			const found = findNode(n.children, path);
			if (found) return found;
		}
		return null;
	}

	const selectedFile = $derived(selectedPath ? findNode(tree, selectedPath) : null);

	// Dirty + saved overlays (mirrors agents/files behavior).
	let dirtyContent = $state<Record<string, string>>({});
	let savedContent = $state<Record<string, string>>({});
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

	const editorContent = $derived(
		selectedFile
			? (dirtyContent[selectedFile.fullPath] ??
					savedContent[selectedFile.fullPath] ??
					selectedFile.content ??
					'')
			: ''
	);

	const effectiveDbContent = $derived(
		selectedFile ? (savedContent[selectedFile.fullPath] ?? selectedFile.content ?? '') : ''
	);

	const isDirty = $derived(
		selectedFile != null &&
			selectedFile.fullPath in dirtyContent &&
			dirtyContent[selectedFile.fullPath] !== effectiveDbContent
	);

	$effect(() => {
		if (!selectedFile) return;
		const path = selectedFile.fullPath;
		if (path in savedContent && selectedFile.content === savedContent[path]) {
			const next = { ...savedContent };
			delete next[path];
			savedContent = next;
		}
	});

	function onEditorChange(content: string) {
		if (!selectedFile) return;
		dirtyContent = { ...dirtyContent, [selectedFile.fullPath]: content };
	}

	// Strip the synthetic leading slash we add to tree paths before round-tripping to the API.
	function apiPath(fullPath: string): string {
		return fullPath.startsWith('/') ? fullPath.slice(1) : fullPath;
	}

	async function saveFile(content: string) {
		if (!selectedFile) return;
		const fullPath = selectedFile.fullPath;
		saving = true;
		saveError = null;
		savedPath = null;

		const form = new FormData();
		form.set('path', apiPath(fullPath));
		form.set('content', content);

		const res = await fetch('?/save', { method: 'POST', body: form });
		const result = deserialize(await res.text());

		if (result.type === 'failure') {
			saveError = (result.data as { error?: string } | undefined)?.error ?? 'Save failed';
			saving = false;
			return;
		}

		savedContent = { ...savedContent, [fullPath]: content };
		const nextDirty = { ...dirtyContent };
		delete nextDirty[fullPath];
		dirtyContent = nextDirty;

		savedPath = fullPath;
		setTimeout(() => {
			savedPath = null;
		}, 2000);

		await invalidateAll();
		saving = false;
	}

	// ── New file ──────────────────────────────────────────────
	let newFileOpen = $state(false);
	let newFilePath = $state('');
	let newFileError = $state<string | null>(null);
	let newFileSaving = $state(false);

	function openNewFile() {
		newFileOpen = true;
		newFilePath = '';
		newFileError = null;
	}
	function closeNewFile() {
		newFileOpen = false;
	}

	async function createFile() {
		const path = newFilePath.trim();
		if (!path) {
			newFileError = 'Path is required';
			return;
		}
		if (path.startsWith('/') || path.includes('..')) {
			newFileError = 'Path must be relative with no ".." segments';
			return;
		}
		if (files.some((f) => f.path === path)) {
			newFileError = 'A file with this path already exists';
			return;
		}
		newFileSaving = true;
		newFileError = null;

		const form = new FormData();
		form.set('path', path);
		form.set('content', '');
		const res = await fetch('?/save', { method: 'POST', body: form });
		const result = deserialize(await res.text());
		newFileSaving = false;

		if (result.type === 'failure') {
			newFileError = (result.data as { error?: string } | undefined)?.error ?? 'Failed';
			return;
		}
		newFileOpen = false;
		selectedPath = '/' + path;
		await invalidateAll();
	}

	// ── Delete file ───────────────────────────────────────────
	let deleteFilePath = $state<string | null>(null);
	let deletingFile = $state(false);

	async function deleteFile() {
		if (!deleteFilePath) return;
		deletingFile = true;
		const form = new FormData();
		form.set('path', apiPath(deleteFilePath));
		const res = await fetch('?/deleteFile', { method: 'POST', body: form });
		const result = deserialize(await res.text());
		deletingFile = false;

		if (result.type === 'failure') {
			saveError =
				(result.data as { error?: string } | undefined)?.error ?? 'Failed to delete file';
			deleteFilePath = null;
			return;
		}
		if (selectedPath === deleteFilePath) selectedPath = '/SKILL.md';
		deleteFilePath = null;
		await invalidateAll();
	}

	// ── Meta edit ─────────────────────────────────────────────
	let metaOpen = $state(false);
	let metaName = $state('');
	let metaDescription = $state('');
	let metaEmoji = $state('');
	let metaHomepage = $state('');
	let metaAlways = $state(false);
	let metaBins = $state('');
	let metaEnvs = $state('');
	let metaSaving = $state(false);
	let metaError = $state<string | null>(null);

	function parseCsvList(raw: string): string[] {
		return raw
			.split(/[\s,]+/)
			.map((s) => s.trim())
			.filter(Boolean);
	}

	function openMeta() {
		metaOpen = true;
		metaName = data.skill.name;
		metaDescription = data.skill.description;
		metaEmoji = data.skill.emoji ?? '';
		metaHomepage = data.skill.homepage ?? '';
		metaAlways = data.skill.always;
		metaBins = (data.skill.requiredBins ?? []).join(', ');
		metaEnvs = (data.skill.requiredEnvs ?? []).join(', ');
		metaError = null;
	}
	function closeMeta() {
		metaOpen = false;
	}

	async function saveMeta() {
		metaSaving = true;
		metaError = null;
		const form = new FormData();
		form.set('name', metaName);
		form.set('description', metaDescription);
		form.set('emoji', metaEmoji);
		form.set('homepage', metaHomepage);
		form.set('always', metaAlways ? 'true' : 'false');
		form.set('required_bins', JSON.stringify(parseCsvList(metaBins)));
		form.set('required_envs', JSON.stringify(parseCsvList(metaEnvs)));
		const res = await fetch('?/updateMeta', { method: 'POST', body: form });
		const result = deserialize(await res.text());
		metaSaving = false;

		if (result.type === 'failure') {
			metaError = (result.data as { metaError?: string } | undefined)?.metaError ?? 'Failed';
			return;
		}
		metaOpen = false;
		await invalidateAll();
	}

	// ── Delete skill ──────────────────────────────────────────
	let deleteSkillOpen = $state(false);

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
	<!-- ── Header ───────────────────────────────────────────── -->
	<header class="files-header">
		<div class="header-left">
			<a
				href={`/w/${data.workspace.id}/workspace/skills`}
				class="back-btn"
				aria-label="Back to skills"
			>
				<Icon icon="tabler:arrow-left" width={14} height={14} />
				<span>Back</span>
			</a>
			<div class="header-divider"></div>
			<div class="skill-icon">
				{#if data.skill.emoji}
					<span class="skill-emoji">{data.skill.emoji}</span>
				{:else}
					<Icon icon="oc:tool" width={14} height={14} />
				{/if}
			</div>
			<h1 class="skill-name font-display">{data.skill.name}</h1>
			{#if data.skill.always}
				<span class="hdr-badge hdr-badge--always font-mono" title="Always loaded into every system prompt"
					>always</span
				>
			{/if}
			{#if data.attachedAgents.length > 0}
				<span class="agents-badge font-mono" title={data.attachedAgents.map((a) => a.name).join(', ')}>
					<Icon icon="tabler:robot" width={10} height={10} />
					{data.attachedAgents.length}
				</span>
			{/if}
		</div>
		<div class="header-right">
			<button class="hdr-btn font-mono" type="button" onclick={openMeta}>
				<Icon icon="tabler:edit" width={11} height={11} />
				Edit
			</button>
			<button
				class="hdr-btn hdr-btn--danger font-mono"
				type="button"
				onclick={() => (deleteSkillOpen = true)}
			>
				<Icon icon="tabler:trash" width={11} height={11} />
				Delete
			</button>
		</div>
	</header>

	<!-- ── Meta edit banner ─────────────────────────────────── -->
	{#if metaOpen}
		<div class="meta-banner">
			<div class="meta-row">
				<label class="meta-lbl font-mono" for="skill-meta-name">NAME</label>
				<input
					id="skill-meta-name"
					class="meta-inp font-mono"
					bind:value={metaName}
					spellcheck="false"
				/>
			</div>
			<div class="meta-row">
				<label class="meta-lbl font-mono" for="skill-meta-desc">DESCRIPTION</label>
				<input
					id="skill-meta-desc"
					class="meta-inp"
					bind:value={metaDescription}
					placeholder="What does this skill do? (drives agent's trigger decisions)"
				/>
			</div>
			<div class="meta-row meta-row--split">
				<div class="meta-split-item">
					<label class="meta-lbl font-mono" for="skill-meta-emoji">EMOJI</label>
					<input
						id="skill-meta-emoji"
						class="meta-inp meta-inp--tiny"
						bind:value={metaEmoji}
						placeholder="📋"
						maxlength={4}
					/>
				</div>
				<div class="meta-split-item meta-split-item--wide">
					<label class="meta-lbl font-mono" for="skill-meta-homepage">HOMEPAGE</label>
					<input
						id="skill-meta-homepage"
						class="meta-inp font-mono"
						bind:value={metaHomepage}
						placeholder="https://…"
						autocomplete="off"
					/>
				</div>
			</div>
			<div class="meta-row">
				<label class="meta-lbl font-mono" for="skill-meta-always">ALWAYS</label>
				<label class="meta-toggle">
					<input
						id="skill-meta-always"
						type="checkbox"
						bind:checked={metaAlways}
					/>
					<span class="meta-toggle-hint">
						pin this skill into every system prompt (skip progressive disclosure)
					</span>
				</label>
			</div>
			<div class="meta-row">
				<label class="meta-lbl font-mono" for="skill-meta-bins">REQUIRES · BINS</label>
				<input
					id="skill-meta-bins"
					class="meta-inp font-mono"
					bind:value={metaBins}
					placeholder="jq, gh (comma-separated CLI binaries)"
					spellcheck="false"
				/>
			</div>
			<div class="meta-row">
				<label class="meta-lbl font-mono" for="skill-meta-envs">REQUIRES · ENV</label>
				<input
					id="skill-meta-envs"
					class="meta-inp font-mono"
					bind:value={metaEnvs}
					placeholder="TRELLO_API_KEY, TRELLO_TOKEN"
					spellcheck="false"
				/>
			</div>
			{#if metaError}<p class="meta-err font-mono">{metaError}</p>{/if}
			<div class="meta-actions">
				<button class="btn-primary font-mono" type="button" onclick={saveMeta} disabled={metaSaving}>
					{#if metaSaving}<span class="spinner"></span>saving…{:else}Save{/if}
				</button>
				<button class="btn-ghost font-mono" type="button" onclick={closeMeta}>Cancel</button>
			</div>
		</div>
	{/if}

	<!-- ── Description + requires row (when not editing) ──── -->
	{#if !metaOpen && (data.skill.description || data.skill.homepage || data.skill.requiredBins.length || data.skill.requiredEnvs.length)}
		<div class="desc-banner">
			{#if data.skill.description}
				<span class="desc-text">{data.skill.description}</span>
			{/if}
			<div class="desc-chips">
				{#if data.skill.homepage}
					<a class="chip chip--link font-mono" href={data.skill.homepage} target="_blank" rel="noopener">
						<Icon icon="tabler:external-link" width={10} height={10} />
						homepage
					</a>
				{/if}
				{#each data.skill.requiredBins as bin}
					<span class="chip chip--req font-mono" title="Required CLI binary">
						<Icon icon="tabler:terminal-2" width={10} height={10} />
						{bin}
					</span>
				{/each}
				{#each data.skill.requiredEnvs as env}
					<span class="chip chip--req font-mono" title="Required environment variable">
						<Icon icon="tabler:key" width={10} height={10} />
						{env}
					</span>
				{/each}
			</div>
		</div>
	{/if}

	<!-- ── Delete confirm ──────────────────────────────────── -->
	{#if deleteSkillOpen}
		<div class="delete-banner">
			<span class="font-mono">
				Delete <em>{data.skill.name}</em>?
				{#if data.attachedAgents.length > 0}
					It's attached to {data.attachedAgents.length}
					{data.attachedAgents.length === 1 ? 'agent' : 'agents'} — will detach automatically.
				{/if}
			</span>
			<form method="POST" action="?/deleteSkill" class="delete-actions">
				<button class="btn-danger font-mono" type="submit">Delete skill</button>
				<button
					class="btn-ghost font-mono"
					type="button"
					onclick={() => (deleteSkillOpen = false)}>Cancel</button
				>
			</form>
		</div>
	{/if}

	<!-- ── Body ─────────────────────────────────────────────── -->
	<div class="files-body">
		<aside class="file-tree">
			<div class="tree-head">
				<span class="tree-label font-mono">files</span>
				<button
					class="tree-new"
					type="button"
					onclick={openNewFile}
					aria-label="New file"
				>
					<Icon icon="tabler:plus" width={11} height={11} />
				</button>
			</div>

			{#if newFileOpen}
				<div class="newfile-form">
					<input
						class="newfile-inp font-mono"
						bind:value={newFilePath}
						placeholder="e.g. references/schema.md"
						spellcheck="false"
						autocomplete="off"
					/>
					{#if newFileError}<p class="newfile-err font-mono">{newFileError}</p>{/if}
					<div class="newfile-actions">
						<button
							class="newfile-btn font-mono"
							type="button"
							onclick={createFile}
							disabled={newFileSaving}
						>
							{#if newFileSaving}<span class="spinner"></span>{:else}Create{/if}
						</button>
						<button class="newfile-btn font-mono newfile-btn--ghost" type="button" onclick={closeNewFile}>Cancel</button>
					</div>
				</div>
			{/if}

			{#if tree.length === 0}
				<p class="tree-empty font-mono">no files yet</p>
			{:else}
				{@render treeNodes(tree, 0)}
			{/if}
		</aside>

		<div class="file-content">
			{#if selectedFile}
				<div class="file-content-header">
					<span class="file-content-path font-mono">{selectedFile.fullPath.replace(/^\//, '')}</span>
					<div class="file-actions">
						{#if saveError}
							<span class="save-error font-mono">{saveError}</span>
						{:else if savedPath === selectedFile.fullPath}
							<span class="save-ok font-mono">saved</span>
						{:else if isDirty}
							<span class="save-hint font-mono">unsaved</span>
						{/if}
						{#if selectedFile.name !== 'SKILL.md'}
							<button
								class="file-del-btn"
								type="button"
								onclick={() => (deleteFilePath = selectedFile!.fullPath)}
								aria-label="Delete file"
							>
								<Icon icon="tabler:trash" width={11} height={11} />
							</button>
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

				{#if deleteFilePath === selectedFile.fullPath}
					<div class="file-del-banner">
						<span class="font-mono">
							Delete <em>{selectedFile.fullPath.replace(/^\//, '')}</em>?
						</span>
						<div class="file-del-actions">
							<button
								class="btn-danger font-mono"
								type="button"
								onclick={deleteFile}
								disabled={deletingFile}
							>
								{#if deletingFile}<span class="spinner"></span>{:else}Delete{/if}
							</button>
							<button
								class="btn-ghost font-mono"
								type="button"
								onclick={() => (deleteFilePath = null)}>Cancel</button
							>
						</div>
					</div>
				{/if}

				<div class="editor-wrap">
					{#key selectedFile.fullPath}
						<CodeEditor
							path={selectedFile.fullPath}
							content={editorContent}
							readOnly={false}
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
					width={12}
					height={12}
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
				class:dirty={node.fullPath in dirtyContent &&
					dirtyContent[node.fullPath] !== (node.content ?? '')}
				class:primary={node.name === 'SKILL.md'}
				style="padding-left: {0.6 + depth * 1.1}rem"
				onclick={() => {
					selectedPath = node.fullPath;
				}}
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
	.skill-icon {
		width: 24px;
		height: 24px;
		border-radius: 0.3rem;
		background: color-mix(in oklch, var(--primary) 12%, transparent);
		color: var(--primary);
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.skill-name {
		font-size: 1rem;
		font-variation-settings: 'opsz' 24, 'wght' 650;
		line-height: 1;
		letter-spacing: -0.01em;
	}
	.agents-badge {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.2rem 0.45rem;
		font-size: 0.6rem;
		border-radius: 0.25rem;
		background: var(--muted);
		color: var(--muted-foreground);
		letter-spacing: 0.04em;
	}
	.header-right {
		display: flex;
		gap: 0.35rem;
	}
	.hdr-btn {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.35rem 0.65rem;
		font-size: 0.65rem;
		letter-spacing: 0.04em;
		border-radius: 0.3rem;
		color: var(--muted-foreground);
		transition: background 120ms ease, color 120ms ease;
	}
	.hdr-btn:hover {
		background: var(--muted);
		color: var(--foreground);
	}
	.hdr-btn--danger:hover {
		color: var(--destructive);
		background: color-mix(in oklch, var(--destructive) 10%, transparent);
	}

	.meta-banner {
		flex-shrink: 0;
		padding: 0.85rem 1.25rem;
		background: var(--card);
		border-bottom: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
	}
	.meta-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}
	.meta-lbl {
		font-size: 0.58rem;
		letter-spacing: 0.1em;
		color: var(--muted-foreground);
		width: 5.5rem;
		flex-shrink: 0;
	}
	.meta-inp {
		flex: 1;
		padding: 0.4rem 0.6rem;
		font-size: 0.8rem;
		background: var(--background);
		border: 1px solid var(--border);
		border-radius: 0.3rem;
		color: var(--foreground);
	}
	.meta-inp:focus {
		outline: none;
		border-color: var(--primary);
	}
	.meta-err {
		font-size: 0.7rem;
		color: var(--destructive);
	}
	.meta-actions {
		display: flex;
		gap: 0.5rem;
	}

	.desc-banner {
		flex-shrink: 0;
		padding: 0.55rem 1.25rem;
		font-size: 0.75rem;
		color: var(--muted-foreground);
		border-bottom: 1px solid var(--border);
		background: color-mix(in oklch, var(--muted) 40%, var(--background));
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-wrap: wrap;
	}
	.desc-text {
		flex: 1;
		min-width: 0;
	}
	.desc-chips {
		display: flex;
		gap: 0.35rem;
		flex-wrap: wrap;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.15rem 0.45rem;
		font-size: 0.6rem;
		letter-spacing: 0.04em;
		border-radius: 0.2rem;
		background: var(--card);
		border: 1px solid var(--border);
		color: var(--muted-foreground);
	}
	.chip--req {
		color: color-mix(in oklch, var(--primary) 60%, var(--muted-foreground));
	}
	.chip--link {
		color: var(--primary);
		text-decoration: none;
	}
	.chip--link:hover {
		background: color-mix(in oklch, var(--primary) 10%, transparent);
	}
	.skill-emoji {
		font-size: 1rem;
		line-height: 1;
	}
	.hdr-badge {
		padding: 0.2rem 0.45rem;
		font-size: 0.55rem;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		border-radius: 0.2rem;
	}
	.hdr-badge--always {
		background: color-mix(in oklch, var(--primary) 15%, transparent);
		color: var(--primary);
	}
	.meta-row--split {
		gap: 0.75rem;
	}
	.meta-split-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-shrink: 0;
	}
	.meta-split-item--wide {
		flex: 1;
	}
	.meta-inp--tiny {
		width: 4rem;
		flex: 0 0 auto;
		text-align: center;
		font-size: 1rem;
	}
	.meta-toggle {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		cursor: pointer;
	}
	.meta-toggle input {
		accent-color: var(--primary);
	}
	.meta-toggle-hint {
		font-size: 0.7rem;
		color: var(--muted-foreground);
	}

	.delete-banner {
		flex-shrink: 0;
		padding: 0.75rem 1.25rem;
		background: color-mix(in oklch, var(--destructive) 8%, var(--background));
		border-bottom: 1px solid var(--destructive);
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		font-size: 0.75rem;
	}
	.delete-banner em {
		color: var(--foreground);
		font-style: italic;
	}
	.delete-actions {
		display: flex;
		gap: 0.45rem;
	}

	.btn-primary {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.4rem 0.8rem;
		font-size: 0.68rem;
		letter-spacing: 0.04em;
		border-radius: 0.3rem;
		background: var(--primary);
		color: var(--primary-foreground);
		border: 1px solid var(--primary);
	}
	.btn-primary:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}
	.btn-ghost {
		padding: 0.4rem 0.8rem;
		font-size: 0.68rem;
		letter-spacing: 0.04em;
		border-radius: 0.3rem;
		color: var(--muted-foreground);
	}
	.btn-ghost:hover {
		background: var(--muted);
		color: var(--foreground);
	}
	.btn-danger {
		padding: 0.4rem 0.8rem;
		font-size: 0.68rem;
		letter-spacing: 0.04em;
		border-radius: 0.3rem;
		background: var(--destructive);
		color: white;
		border: 1px solid var(--destructive);
	}
	.btn-danger:disabled {
		opacity: 0.6;
	}

	.files-body {
		flex: 1;
		display: flex;
		min-height: 0;
		overflow: hidden;
	}

	.file-tree {
		width: 240px;
		flex-shrink: 0;
		overflow-y: auto;
		border-right: 1px solid var(--border);
		padding: 0.5rem 0;
	}
	.tree-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.35rem 0.9rem 0.55rem;
	}
	.tree-label {
		font-size: 0.58rem;
		letter-spacing: 0.12em;
		color: var(--muted-foreground);
		text-transform: uppercase;
		opacity: 0.6;
	}
	.tree-new {
		width: 18px;
		height: 18px;
		border-radius: 0.2rem;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--muted-foreground);
	}
	.tree-new:hover {
		background: var(--muted);
		color: var(--primary);
	}
	.newfile-form {
		padding: 0.4rem 0.9rem 0.65rem;
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
		border-bottom: 1px solid var(--border);
		margin-bottom: 0.35rem;
	}
	.newfile-inp {
		padding: 0.35rem 0.5rem;
		font-size: 0.7rem;
		border: 1px solid var(--border);
		border-radius: 0.25rem;
		background: var(--background);
		color: var(--foreground);
	}
	.newfile-inp:focus {
		outline: none;
		border-color: var(--primary);
	}
	.newfile-err {
		font-size: 0.6rem;
		color: var(--destructive);
	}
	.newfile-actions {
		display: flex;
		gap: 0.3rem;
	}
	.newfile-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.25rem;
		padding: 0.25rem 0.55rem;
		font-size: 0.6rem;
		letter-spacing: 0.04em;
		border-radius: 0.25rem;
		background: var(--primary);
		color: var(--primary-foreground);
	}
	.newfile-btn:disabled {
		opacity: 0.6;
	}
	.newfile-btn--ghost {
		background: transparent;
		color: var(--muted-foreground);
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
	.tree-node:hover {
		background: var(--muted);
	}
	.tree-file.selected {
		background: color-mix(in oklch, var(--primary) 10%, transparent);
		color: var(--primary);
	}
	.tree-file.primary {
		font-weight: 500;
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
	:global(.tree-icon) {
		flex-shrink: 0;
		opacity: 0.7;
	}
	:global(.tree-icon-dir) {
		color: var(--primary);
		opacity: 0.75;
	}

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
	}
	.save-ok {
		font-size: 0.62rem;
		color: var(--primary);
		opacity: 0.8;
	}
	.save-error {
		font-size: 0.62rem;
		color: var(--destructive);
	}
	.file-del-btn {
		width: 22px;
		height: 22px;
		border-radius: 0.25rem;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--muted-foreground);
	}
	.file-del-btn:hover {
		color: var(--destructive);
		background: color-mix(in oklch, var(--destructive) 10%, transparent);
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
	}
	.save-btn.dirty {
		border-color: color-mix(in oklch, var(--primary) 40%, var(--border));
		color: var(--foreground);
	}
	.save-btn.dirty:hover {
		background: color-mix(in oklch, var(--primary) 10%, transparent);
		color: var(--primary);
	}
	.save-btn:disabled {
		opacity: 0.35;
		cursor: not-allowed;
	}

	.file-del-banner {
		flex-shrink: 0;
		padding: 0.6rem 1rem;
		background: color-mix(in oklch, var(--destructive) 8%, var(--background));
		border-bottom: 1px solid var(--destructive);
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		font-size: 0.72rem;
	}
	.file-del-banner em {
		color: var(--foreground);
		font-style: italic;
	}
	.file-del-actions {
		display: flex;
		gap: 0.4rem;
	}

	.spinner {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		border: 1.5px solid currentColor;
		border-right-color: transparent;
		animation: spin 0.7s linear infinite;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
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
