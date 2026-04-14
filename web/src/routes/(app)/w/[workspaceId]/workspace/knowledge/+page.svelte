<script lang="ts">
	import { page } from '$app/state';
	import KnowledgeGraph from '$lib/components/knowledge-graph.svelte';

	const workspaceId = $derived(page.params.workspaceId as string);

	type PageTab = 'ingest' | 'query' | 'graph';
	type InputMode = 'text' | 'file';
	type QueryMode = 'hybrid' | 'local' | 'global' | 'naive';

	let activeTab = $state<PageTab>('ingest');

	type LogEntry = {
		id: number;
		ts: string;
		kind: 'ok' | 'err' | 'info';
		msg: string;
	};

	let _seq = 0;
	function now() {
		return new Date().toLocaleTimeString('en-GB', { hour12: false });
	}
	function logEntry(msg: string, kind: LogEntry['kind'] = 'ok'): LogEntry {
		return { id: _seq++, ts: now(), kind, msg };
	}

	// ── Ingest state ──────────────────────────────────────────
	let inputMode = $state<InputMode>('text');
	let textValue = $state('');
	let metaValue = $state('');
	let file = $state<File | null>(null);
	let ingestLoading = $state(false);
	let log = $state<LogEntry[]>([]);
	let dragOver = $state(false);

	// ── Query state ───────────────────────────────────────────
	let queryText = $state('');
	let queryMode = $state<QueryMode>('hybrid');
	let queryLoading = $state(false);
	let queryAnswer = $state('');
	let queryError = $state('');

	function addLog(msg: string, kind: LogEntry['kind'] = 'ok') {
		log = [logEntry(msg, kind), ...log].slice(0, 40);
	}

	async function ingestText() {
		if (!textValue.trim() || ingestLoading) return;
		ingestLoading = true;
		try {
			let metadata: Record<string, string> = {};
			if (metaValue.trim()) {
				try {
					metadata = JSON.parse(metaValue);
				} catch {
					metadata = { tag: metaValue.trim() };
				}
			}
			const res = await fetch('/api/knowledge/ingest/text', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ workspace_id: workspaceId, text: textValue, metadata })
			});
			if (!res.ok) {
				const msg = await res.text();
				addLog(`error: ${msg || res.status}`, 'err');
				return;
			}
			addLog(`text queued — ${textValue.length} chars, indexing in background`, 'ok');
			textValue = '';
			metaValue = '';
		} catch (e) {
			addLog(`error: ${e instanceof Error ? e.message : 'unknown'}`, 'err');
		} finally {
			ingestLoading = false;
		}
	}

	async function ingestFile() {
		if (!file || ingestLoading) return;
		ingestLoading = true;
		try {
			const fd = new FormData();
			fd.append('workspace_id', workspaceId);
			fd.append('file', file);
			const res = await fetch('/api/knowledge/ingest/file', {
				method: 'POST',
				body: fd
			});
			if (!res.ok) {
				const msg = await res.text();
				addLog(`error: ${msg || res.status}`, 'err');
				return;
			}
			addLog(`file "${file.name}" queued — indexing in background`, 'ok');
			file = null;
		} catch (e) {
			addLog(`error: ${e instanceof Error ? e.message : 'unknown'}`, 'err');
		} finally {
			ingestLoading = false;
		}
	}

	function onFilePick(e: Event) {
		const input = e.target as HTMLInputElement;
		file = input.files?.[0] ?? null;
	}

	function onDrop(e: DragEvent) {
		e.preventDefault();
		dragOver = false;
		const dropped = e.dataTransfer?.files?.[0];
		if (dropped) file = dropped;
	}

	function onDragOver(e: DragEvent) {
		e.preventDefault();
		dragOver = true;
	}

	async function runQuery() {
		if (!queryText.trim() || queryLoading) return;
		queryLoading = true;
		queryAnswer = '';
		queryError = '';
		try {
			const res = await fetch('/api/knowledge/query', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ workspace_id: workspaceId, query: queryText, mode: queryMode })
			});
			if (!res.ok) {
				const msg = await res.text();
				queryError = msg || `HTTP ${res.status}`;
				return;
			}
			const data = await res.json();
			queryAnswer = data.answer ?? '';
		} catch (e) {
			queryError = e instanceof Error ? e.message : 'unknown error';
		} finally {
			queryLoading = false;
		}
	}

	function onQueryKey(e: KeyboardEvent) {
		if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) runQuery();
	}
</script>

<div class="shell">
	<header class="head">
		<div class="crumb font-mono">workspace / knowledge</div>
		<h1 class="title font-display">Knowledge</h1>
		<p class="tag">
			ingest text and files into the shared graph — agents read from the same source.
		</p>
	</header>

	<!-- ── Tab bar ─────────────────────────────────────── -->
	<div class="tab-bar">
		<button class="tab" class:active={activeTab === 'ingest'} onclick={() => (activeTab = 'ingest')}>
			ingest
		</button>
		<button class="tab" class:active={activeTab === 'query'} onclick={() => (activeTab = 'query')}>
			query
		</button>
		<button class="tab" class:active={activeTab === 'graph'} onclick={() => (activeTab = 'graph')}>
			graph
		</button>
	</div>

	<!-- ── Graph tab ────────────────────────────────────── -->
	{#if activeTab === 'graph'}
		<KnowledgeGraph {workspaceId} />
	{/if}

	<!-- ── Ingest + Query tabs ───────────────────────────── -->
	{#if activeTab !== 'graph'}
	<div class="body">
		<!-- ── Ingest panel ──────────────────────────────────── -->
		{#if activeTab === 'ingest'}
		<section class="panel">
			<div class="panel-head">
				<span class="panel-label font-mono">ingest</span>
				<div class="mode-toggle font-mono">
					<button
						class="toggle-btn"
						class:active={inputMode === 'text'}
						onclick={() => {
							inputMode = 'text';
							file = null;
						}}>text</button
					>
					<button
						class="toggle-btn"
						class:active={inputMode === 'file'}
						onclick={() => {
							inputMode = 'file';
						}}>file</button
					>
				</div>
			</div>

			{#if inputMode === 'text'}
				<div class="text-input-wrap">
					<textarea
						class="text-area font-mono"
						bind:value={textValue}
						placeholder="paste text, research notes, findings…"
						rows={10}
					></textarea>
					<div class="meta-row">
						<input
							class="meta-input font-mono"
							bind:value={metaValue}
							placeholder={'tag or {"source":"web"}'}
						/>
						<button
							class="ingest-btn font-mono"
							onclick={ingestText}
							disabled={!textValue.trim() || ingestLoading}
						>
							{#if ingestLoading}
								<span class="spin"></span>indexing…
							{:else}
								ingest ↵
							{/if}
						</button>
					</div>
				</div>
			{:else}
				<div
					class="drop-zone"
					class:drag-active={dragOver}
					ondrop={onDrop}
					ondragover={onDragOver}
					ondragleave={() => {
						dragOver = false;
					}}
					role="region"
					aria-label="File drop zone"
				>
					{#if file}
						<div class="file-ready font-mono">
							<span class="file-icon">◈</span>
							<span class="file-name">{file.name}</span>
							<span class="file-size">({(file.size / 1024).toFixed(1)} KB)</span>
							<button
								class="file-clear"
								onclick={() => {
									file = null;
								}}>×</button
							>
						</div>
					{:else}
						<p class="drop-hint font-mono">drop file here or</p>
						<label class="pick-label font-mono">
							browse
							<input type="file" accept=".txt,.md,.pdf" onchange={onFilePick} class="file-input" />
						</label>
						<p class="drop-types font-mono">.txt · .md · .pdf</p>
					{/if}
				</div>
				<div class="meta-row">
					<div class="spacer"></div>
					<button
						class="ingest-btn font-mono"
						onclick={ingestFile}
						disabled={!file || ingestLoading}
					>
						{#if ingestLoading}
							<span class="spin"></span>indexing…
						{:else}
							ingest ↵
						{/if}
					</button>
				</div>
			{/if}

			<!-- log -->
			{#if log.length > 0}
				<div class="log">
					{#each log as entry (entry.id)}
						<div class="log-line" class:log-err={entry.kind === 'err'}>
							<span class="log-ts">{entry.ts}</span>
							<span class="log-msg">{entry.msg}</span>
						</div>
					{/each}
				</div>
			{/if}
		</section>
		{/if}

		<!-- ── Query panel ───────────────────────────────────── -->
		{#if activeTab === 'query'}
		<section class="panel">
			<div class="panel-head">
				<span class="panel-label font-mono">query</span>
				<div class="mode-toggle font-mono">
					{#each ['hybrid', 'local', 'global', 'naive'] as m (m)}
						<button
							class="toggle-btn"
							class:active={queryMode === m}
							onclick={() => {
								queryMode = m as QueryMode;
							}}>{m}</button
						>
					{/each}
				</div>
			</div>

			<div class="query-row">
				<input
					class="query-input font-mono"
					bind:value={queryText}
					onkeydown={onQueryKey}
					placeholder="ask the graph… (⌘↵ to run)"
				/>
				<button
					class="ingest-btn font-mono"
					onclick={runQuery}
					disabled={!queryText.trim() || queryLoading}
				>
					{#if queryLoading}
						<span class="spin"></span>thinking…
					{:else}
						ask →
					{/if}
				</button>
			</div>

			{#if queryError}
				<div class="q-error font-mono">{queryError}</div>
			{/if}

			{#if queryAnswer}
				<div class="q-answer">{queryAnswer}</div>
			{/if}

			{#if !queryAnswer && !queryError && !queryLoading}
				<p class="q-empty font-mono">results will appear here.</p>
			{/if}
		</section>
		{/if}
	</div>
	{/if}
</div>

<style>
	.shell {
		flex: 1;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	/* ── Tab bar ───────────────────────────────────────────── */
	.tab-bar {
		display: flex;
		gap: 0;
		border-bottom: 1px solid var(--border);
		padding: 0 3rem;
		flex-shrink: 0;
	}

	.tab {
		font-family: var(--font-mono, monospace);
		font-size: 0.62rem;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		padding: 0.6rem 1rem;
		color: color-mix(in oklch, var(--foreground) 35%, transparent);
		border-bottom: 2px solid transparent;
		margin-bottom: -1px;
		transition: color 120ms ease, border-color 120ms ease;
	}

	.tab:hover {
		color: color-mix(in oklch, var(--foreground) 70%, transparent);
	}

	.tab.active {
		color: var(--foreground);
		border-bottom-color: var(--foreground);
	}

	/* ── Header ────────────────────────────────────────────── */
	.head {
		padding: 1.75rem 3rem 2rem;
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
	}

	.crumb {
		font-size: 0.62rem;
		letter-spacing: 0.16em;
		text-transform: uppercase;
		color: color-mix(in oklch, var(--foreground) 35%, transparent);
		margin-bottom: 0.75rem;
	}

	.title {
		font-size: 3.5rem;
		line-height: 1;
		font-style: italic;
		letter-spacing: -0.015em;
	}

	.tag {
		margin-top: 0.9rem;
		color: var(--muted-foreground);
		font-size: 0.95rem;
		max-width: 42rem;
	}

	/* ── Body ──────────────────────────────────────────────── */
	.body {
		flex: 1;
		display: flex;
		flex-direction: column;
		padding: 2rem 3rem;
		overflow-y: auto;
		gap: 0;
		max-width: 860px;
	}

	/* ── Panel shared ──────────────────────────────────────── */
	.panel {
		display: flex;
		flex-direction: column;
		gap: 0.9rem;
		padding-bottom: 2rem;
	}

	.panel-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
	}

	.panel-label {
		font-size: 0.58rem;
		letter-spacing: 0.18em;
		text-transform: uppercase;
		color: color-mix(in oklch, var(--foreground) 38%, transparent);
	}

	/* ── Mode toggle ────────────────────────────────────────── */
	.mode-toggle {
		display: flex;
		gap: 0.1rem;
		background: color-mix(in oklch, var(--foreground) 5%, transparent);
		border: 1px solid var(--border);
		border-radius: 0.3rem;
		padding: 0.15rem;
	}

	.toggle-btn {
		font-size: 0.65rem;
		letter-spacing: 0.06em;
		padding: 0.2rem 0.6rem;
		border-radius: 0.2rem;
		color: color-mix(in oklch, var(--foreground) 45%, transparent);
		transition:
			color 120ms ease,
			background 120ms ease;
	}

	.toggle-btn:hover {
		color: var(--foreground);
	}

	.toggle-btn.active {
		color: var(--foreground);
		background: color-mix(in oklch, var(--foreground) 10%, transparent);
	}

	/* ── Text input ─────────────────────────────────────────── */
	.text-input-wrap {
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
		border: 1px solid var(--border);
		border-radius: 0.45rem;
		overflow: hidden;
		background: color-mix(in oklch, var(--foreground) 2%, transparent);
		transition: border-color 150ms ease;
	}

	.text-input-wrap:focus-within {
		border-color: color-mix(in oklch, var(--primary) 45%, transparent);
	}

	.text-area {
		resize: none;
		background: transparent;
		border: none;
		outline: none;
		padding: 0.9rem 1rem;
		font-size: 0.8rem;
		line-height: 1.65;
		color: var(--foreground);
		width: 100%;
		letter-spacing: 0.01em;
	}

	.text-area::placeholder {
		color: color-mix(in oklch, var(--foreground) 25%, transparent);
	}

	.meta-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 0.75rem;
		border-top: 1px solid var(--border);
	}

	.text-input-wrap .meta-row {
		border-top: 1px solid color-mix(in oklch, var(--border) 60%, transparent);
		background: color-mix(in oklch, var(--foreground) 2%, transparent);
	}

	.meta-input {
		flex: 1;
		background: transparent;
		border: none;
		outline: none;
		font-size: 0.7rem;
		color: color-mix(in oklch, var(--foreground) 55%, transparent);
		letter-spacing: 0.01em;
	}

	.meta-input::placeholder {
		color: color-mix(in oklch, var(--foreground) 22%, transparent);
	}

	.spacer {
		flex: 1;
	}

	/* ── Ingest button ──────────────────────────────────────── */
	.ingest-btn {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		font-size: 0.65rem;
		letter-spacing: 0.08em;
		padding: 0.35rem 0.85rem;
		border-radius: 0.25rem;
		background: color-mix(in oklch, var(--primary) 14%, transparent);
		color: var(--primary);
		border: 1px solid color-mix(in oklch, var(--primary) 28%, transparent);
		transition:
			background 150ms ease,
			border-color 150ms ease,
			opacity 150ms ease;
		white-space: nowrap;
	}

	.ingest-btn:hover:not(:disabled) {
		background: color-mix(in oklch, var(--primary) 22%, transparent);
		border-color: color-mix(in oklch, var(--primary) 45%, transparent);
	}

	.ingest-btn:disabled {
		opacity: 0.35;
		cursor: not-allowed;
	}

	/* ── Drop zone ──────────────────────────────────────────── */
	.drop-zone {
		border: 1px dashed var(--border);
		border-radius: 0.45rem;
		padding: 2.5rem 1.5rem;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
		text-align: center;
		transition:
			border-color 150ms ease,
			background 150ms ease;
		cursor: default;
	}

	.drop-zone.drag-active {
		border-color: var(--primary);
		background: color-mix(in oklch, var(--primary) 6%, transparent);
	}

	.drop-hint {
		font-size: 0.75rem;
		color: color-mix(in oklch, var(--foreground) 38%, transparent);
		letter-spacing: 0.02em;
	}

	.pick-label {
		font-size: 0.68rem;
		letter-spacing: 0.06em;
		color: var(--primary);
		cursor: pointer;
		padding: 0.25rem 0.7rem;
		border: 1px solid color-mix(in oklch, var(--primary) 30%, transparent);
		border-radius: 0.2rem;
		background: color-mix(in oklch, var(--primary) 8%, transparent);
		transition:
			background 150ms ease,
			border-color 150ms ease;
	}

	.pick-label:hover {
		background: color-mix(in oklch, var(--primary) 15%, transparent);
		border-color: color-mix(in oklch, var(--primary) 45%, transparent);
	}

	.file-input {
		display: none;
	}

	.drop-types {
		font-size: 0.6rem;
		letter-spacing: 0.1em;
		color: color-mix(in oklch, var(--foreground) 22%, transparent);
		margin-top: 0.1rem;
	}

	.file-ready {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.75rem;
		color: var(--foreground);
	}

	.file-icon {
		color: var(--primary);
		font-size: 0.9rem;
	}

	.file-name {
		font-weight: 500;
	}

	.file-size {
		color: color-mix(in oklch, var(--foreground) 40%, transparent);
		font-size: 0.68rem;
	}

	.file-clear {
		color: color-mix(in oklch, var(--foreground) 35%, transparent);
		font-size: 1rem;
		line-height: 1;
		margin-left: 0.25rem;
		transition: color 120ms ease;
	}

	.file-clear:hover {
		color: var(--destructive, #e05555);
	}

	/* ── Log ────────────────────────────────────────────────── */
	.log {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
		border: 1px solid var(--border);
		border-radius: 0.35rem;
		padding: 0.6rem 0.8rem;
		background: color-mix(in oklch, var(--foreground) 2%, transparent);
		max-height: 10rem;
		overflow-y: auto;
	}

	.log-line {
		display: flex;
		gap: 0.75rem;
		font-size: 0.7rem;
		line-height: 1.5;
		font-family: var(--font-mono);
		color: color-mix(in oklch, var(--foreground) 70%, transparent);
	}

	.log-line.log-err {
		color: var(--destructive, #e05555);
	}

	.log-ts {
		color: color-mix(in oklch, var(--foreground) 28%, transparent);
		flex-shrink: 0;
	}

	.log-msg {
		flex: 1;
	}


	/* ── Query panel ─────────────────────────────────────────── */
	.query-row {
		display: flex;
		gap: 0.5rem;
		align-items: center;
	}

	.query-input {
		flex: 1;
		background: color-mix(in oklch, var(--foreground) 3%, transparent);
		border: 1px solid var(--border);
		border-radius: 0.35rem;
		padding: 0.55rem 0.85rem;
		font-size: 0.8rem;
		color: var(--foreground);
		outline: none;
		transition: border-color 150ms ease;
		letter-spacing: 0.01em;
	}

	.query-input::placeholder {
		color: color-mix(in oklch, var(--foreground) 25%, transparent);
	}

	.query-input:focus {
		border-color: color-mix(in oklch, var(--primary) 45%, transparent);
	}

	.q-error {
		font-size: 0.72rem;
		color: var(--destructive, #e05555);
		padding: 0.5rem 0;
	}

	.q-answer {
		border: 1px solid var(--border);
		border-radius: 0.4rem;
		padding: 1rem 1.1rem;
		font-size: 0.85rem;
		line-height: 1.7;
		color: var(--foreground);
		background: color-mix(in oklch, var(--foreground) 2%, transparent);
		white-space: pre-wrap;
		word-break: break-word;
	}

	.q-empty {
		font-size: 0.7rem;
		color: color-mix(in oklch, var(--foreground) 25%, transparent);
		letter-spacing: 0.02em;
		padding-top: 0.25rem;
	}

	/* ── Spinner ─────────────────────────────────────────────── */
	.spin {
		display: inline-block;
		width: 9px;
		height: 9px;
		border-radius: 9999px;
		border: 1.5px solid currentColor;
		border-right-color: transparent;
		animation: spin 0.75s linear infinite;
		flex-shrink: 0;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
