<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { Icon } from '$lib/icons';

	let { data } = $props();

	type McpType = 'stdio' | 'http';
	type McpRecord = { id: string; name: string; type: McpType; createdAt: Date };

	const mcps = $derived(data.mcps as McpRecord[]);

	// ── KV helper ─────────────────────────────────────────────
	type KvPair = { id: number; key: string; value: string };
	let nextId = 0;
	function kv(key = '', value = ''): KvPair { return { id: nextId++, key, value }; }
	function kvToDict(pairs: KvPair[]): Record<string, string> {
		const out: Record<string, string> = {};
		for (const p of pairs) {
			if (p.key.trim()) out[p.key.trim()] = p.value;
		}
		return out;
	}

	// ── Add wizard ────────────────────────────────────────────
	let addOpen = $state(false);
	let addStep: 'pick' | McpType = $state('pick');
	let saving = $state(false);
	let saveError: string | null = $state(null);

	// stdio fields
	let stdioName = $state('');
	let stdioCommand = $state('');
	let stdioArgs = $state('');
	let stdioEnvPairs: KvPair[] = $state([kv()]);

	// http fields
	let httpName = $state('');
	let httpUrl = $state('');
	let httpHeaderPairs: KvPair[] = $state([kv()]);

	function openAdd() {
		addOpen = true;
		addStep = 'pick';
		saveError = null;
		stdioName = ''; stdioCommand = ''; stdioArgs = ''; stdioEnvPairs = [kv()];
		httpName = ''; httpUrl = ''; httpHeaderPairs = [kv()];
	}
	function closeAdd() { addOpen = false; }
	function pickType(t: McpType) { addStep = t; saveError = null; }

	function parseArgs(raw: string): string[] {
		return raw.split('\n').map(s => s.trim()).filter(Boolean);
	}

	async function saveMcp() {
		saveError = null;
		let name: string;
		let type: McpType;
		let config: Record<string, unknown>;

		if (addStep === 'stdio') {
			name = stdioName.trim();
			if (!name) { saveError = 'Name is required'; return; }
			if (!stdioCommand.trim()) { saveError = 'Command is required'; return; }
			type = 'stdio';
			const args = parseArgs(stdioArgs);
			const env = kvToDict(stdioEnvPairs);
			config = { command: stdioCommand.trim(), ...(args.length ? { args } : {}), ...(Object.keys(env).length ? { env } : {}) };
		} else if (addStep === 'http') {
			name = httpName.trim();
			if (!name) { saveError = 'Name is required'; return; }
			if (!httpUrl.trim()) { saveError = 'URL is required'; return; }
			type = 'http';
			const headers = kvToDict(httpHeaderPairs);
			config = { url: httpUrl.trim(), ...(Object.keys(headers).length ? { headers } : {}) };
		} else {
			return;
		}

		saving = true;
		try {
			const res = await fetch('/api/mcp', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ name, type, config, workspace_id: data.workspace.id })
			});
			if (!res.ok) { saveError = await res.text(); return; }
			addOpen = false;
			await invalidateAll();
		} catch (e) {
			saveError = e instanceof Error ? e.message : 'Failed to create MCP server';
		} finally {
			saving = false;
		}
	}

	// ── Delete ────────────────────────────────────────────────
	let deleteId: string | null = $state(null);
	let deleting = $state(false);
	let deleteError: string | null = $state(null);

	async function confirmDelete() {
		if (!deleteId) return;
		deleting = true;
		deleteError = null;
		try {
			const res = await fetch(`/api/mcp/${deleteId}`, { method: 'DELETE' });
			if (!res.ok && res.status !== 204) { deleteError = await res.text(); return; }
			deleteId = null;
			await invalidateAll();
		} catch (e) {
			deleteError = e instanceof Error ? e.message : 'Failed to delete';
		} finally {
			deleting = false;
		}
	}

	function isSystem(mcp: McpRecord): boolean { return mcp.name === 'officeclaw'; }

	function relDate(d: Date | string): string {
		const ms = Date.now() - new Date(d).getTime();
		const s = Math.floor(ms / 1000);
		if (s < 60) return 'just now';
		const m = Math.floor(s / 60);
		if (m < 60) return `${m}m ago`;
		const h = Math.floor(m / 60);
		if (h < 24) return `${h}h ago`;
		const dd = Math.floor(h / 24);
		if (dd < 30) return `${dd}d ago`;
		return `${Math.floor(dd / 30)}mo ago`;
	}
</script>

<div class="shell">
	<header class="head">
		<div class="crumb font-mono">workspace / mcp</div>
		<h1 class="title font-display">MCP Servers</h1>
		<p class="tag">tool integrations for your agents — connect any MCP-compatible service.</p>
	</header>

	<div class="body">

		<!-- ── Add wizard ──────────────────────────────────────── -->
		{#if addOpen}
			<div class="form-card">

				{#if addStep === 'pick'}
					<p class="pick-label font-mono">choose transport type</p>
					<div class="type-grid">
						<button class="type-btn" type="button" onclick={() => pickType('stdio')}>
							<span class="type-icon font-mono">&gt;_</span>
							<div class="type-info">
								<span class="type-name font-mono">stdio</span>
								<span class="type-desc font-mono">local process — npx, uvx, etc.</span>
							</div>
						</button>
						<button class="type-btn" type="button" onclick={() => pickType('http')}>
							<span class="type-icon font-mono">⌁</span>
							<div class="type-info">
								<span class="type-name font-mono">http / SSE</span>
								<span class="type-desc font-mono">remote server via URL</span>
							</div>
						</button>
					</div>
					<div class="form-actions">
						<button class="btn-ghost font-mono" type="button" onclick={closeAdd}>Cancel</button>
					</div>

				{:else if addStep === 'stdio'}
					<div class="form-header">
						<span class="form-type font-mono">&gt;_ stdio</span>
					</div>

					<div class="field">
						<label class="field-label font-mono" for="stdio-name">Name</label>
						<input id="stdio-name" class="field-input font-mono" type="text" bind:value={stdioName} placeholder="github" spellcheck="false" />
						<p class="field-hint font-mono">Identifier for this server — used as the key in agent config.</p>
					</div>

					<div class="field">
						<label class="field-label font-mono" for="stdio-cmd">Command</label>
						<input id="stdio-cmd" class="field-input font-mono" type="text" bind:value={stdioCommand} placeholder="npx" spellcheck="false" />
					</div>

					<div class="field">
						<label class="field-label font-mono" for="stdio-args">Args <span class="field-opt">(one per line)</span></label>
						<textarea id="stdio-args" class="field-textarea font-mono" bind:value={stdioArgs} placeholder="-y&#10;@modelcontextprotocol/server-github" rows={3} spellcheck="false"></textarea>
					</div>

					<div class="field">
						<span class="field-label font-mono">Environment variables <span class="field-opt">(optional)</span></span>
						<div class="kv-section">
							{#each stdioEnvPairs as pair (pair.id)}
								<div class="kv-row">
									<input class="kv-input font-mono" bind:value={pair.key} placeholder="GITHUB_TOKEN" spellcheck="false" />
									<span class="kv-sep font-mono">=</span>
									<input class="kv-input font-mono" type="password" bind:value={pair.value} placeholder="••••••••" spellcheck="false" autocomplete="new-password" />
									<button class="kv-remove" type="button" onclick={() => { stdioEnvPairs = stdioEnvPairs.filter(p => p.id !== pair.id); }} disabled={stdioEnvPairs.length === 1}>×</button>
								</div>
							{/each}
							<button class="kv-add font-mono" type="button" onclick={() => { stdioEnvPairs = [...stdioEnvPairs, kv()]; }}>+ add variable</button>
						</div>
					</div>

				{:else if addStep === 'http'}
					<div class="form-header">
						<span class="form-type font-mono">⌁ http / SSE</span>
					</div>

					<div class="field">
						<label class="field-label font-mono" for="http-name">Name</label>
						<input id="http-name" class="field-input font-mono" type="text" bind:value={httpName} placeholder="stripe" spellcheck="false" />
						<p class="field-hint font-mono">Identifier for this server — used as the key in agent config.</p>
					</div>

					<div class="field">
						<label class="field-label font-mono" for="http-url">URL</label>
						<input id="http-url" class="field-input font-mono" type="text" bind:value={httpUrl} placeholder="https://mcp.example.com/sse" spellcheck="false" />
					</div>

					<div class="field">
						<span class="field-label font-mono">Headers <span class="field-opt">(optional)</span></span>
						<div class="kv-section">
							{#each httpHeaderPairs as pair (pair.id)}
								<div class="kv-row">
									<input class="kv-input font-mono" bind:value={pair.key} placeholder="Authorization" spellcheck="false" />
									<span class="kv-sep font-mono">=</span>
									<input class="kv-input font-mono" type="password" bind:value={pair.value} placeholder="Bearer ••••••••" spellcheck="false" autocomplete="new-password" />
									<button class="kv-remove" type="button" onclick={() => { httpHeaderPairs = httpHeaderPairs.filter(p => p.id !== pair.id); }} disabled={httpHeaderPairs.length === 1}>×</button>
								</div>
							{/each}
							<button class="kv-add font-mono" type="button" onclick={() => { httpHeaderPairs = [...httpHeaderPairs, kv()]; }}>+ add header</button>
						</div>
					</div>
				{/if}

				{#if addStep !== 'pick'}
					{#if saveError}<p class="form-error font-mono">{saveError}</p>{/if}
					<div class="form-actions">
						<button class="btn-primary font-mono" type="button" onclick={saveMcp} disabled={saving}>
							{#if saving}<span class="spinner"></span>saving…{:else}Add server{/if}
						</button>
						<button class="btn-ghost font-mono" type="button" onclick={closeAdd}>Cancel</button>
					</div>
				{/if}

			</div>
		{/if}

		<!-- ── List header ─────────────────────────────────────── -->
		<div class="list-head">
			<span class="list-count font-mono">{mcps.length} server{mcps.length !== 1 ? 's' : ''}</span>
			{#if !addOpen}
				<button class="btn-add font-mono" type="button" onclick={openAdd}>
					<Icon icon="oc:spawn" width={11} height={11} />
					Add server
				</button>
			{/if}
		</div>

		<!-- ── Empty state ─────────────────────────────────────── -->
		{#if mcps.length === 0}
			<div class="empty-state">
				<div class="empty-icon">
					<Icon icon="oc:configure" width={22} height={22} />
				</div>
				<p class="empty-title">No MCP servers yet</p>
				<p class="empty-sub">Add MCP servers to give your agents access to external tools — GitHub, databases, APIs, and more.</p>
			</div>

		{:else}
			<div class="mcp-list">
				{#each mcps as mcp (mcp.id)}
					<div class="mcp-item" class:mcp-deleting={deleteId === mcp.id}>
						<div class="mcp-row">
							<span class="mcp-badge font-mono" class:mcp-badge--http={mcp.type === 'http'}>
								{mcp.type === 'http' ? '⌁' : '>_'}
							</span>
							<span class="mcp-name font-mono">{mcp.name}</span>
							{#if isSystem(mcp)}
								<span class="system-badge font-mono">system</span>
							{/if}
							<span class="mcp-type font-mono">{mcp.type}</span>
							<span class="mcp-date font-mono">{relDate(mcp.createdAt)}</span>
							{#if !isSystem(mcp)}
								<button
									class="mcp-del font-mono"
									type="button"
									onclick={() => { deleteId = deleteId === mcp.id ? null : mcp.id; deleteError = null; }}
								>delete</button>
							{/if}
						</div>

						{#if deleteId === mcp.id}
							<div class="danger-panel">
								<p class="delete-msg font-mono">
									Remove <strong>{mcp.name}</strong>? Agents using it will lose this tool.
								</p>
								{#if deleteError}<p class="form-error font-mono">{deleteError}</p>{/if}
								<div class="form-actions">
									<button class="btn-danger font-mono" type="button" onclick={confirmDelete} disabled={deleting}>
										{#if deleting}<span class="spinner spinner--danger"></span>removing…{:else}Yes, remove{/if}
									</button>
									<button class="btn-ghost font-mono" type="button" onclick={() => { deleteId = null; deleteError = null; }}>Cancel</button>
								</div>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>

<style>
	.shell { flex: 1; display: flex; flex-direction: column; overflow-y: auto; }

	.head { padding: 3rem 3rem 2rem; border-bottom: 1px solid var(--border); flex-shrink: 0; }
	.crumb {
		font-size: 0.62rem;
		letter-spacing: 0.16em;
		text-transform: uppercase;
		color: color-mix(in oklch, var(--foreground) 35%, transparent);
		margin-bottom: 0.75rem;
	}
	.title { font-size: 3.25rem; line-height: 1; font-style: italic; letter-spacing: -0.015em; }
	.tag { margin-top: 0.85rem; color: var(--muted-foreground); font-size: 0.95rem; max-width: 36rem; }

	.body { flex: 1; padding: 2rem 3rem 4rem; display: flex; flex-direction: column; gap: 1rem; }

	/* ── List header ──────────────────────────────────────────── */
	.list-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding-bottom: 0.75rem;
		border-bottom: 1px solid var(--border);
	}
	.list-count {
		font-size: 0.62rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: color-mix(in oklch, var(--foreground) 40%, transparent);
	}
	.btn-add {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.68rem;
		letter-spacing: 0.04em;
		color: var(--primary);
		padding: 0.3rem 0.6rem;
		border-radius: 0.25rem;
		transition: background 150ms ease;
	}
	.btn-add:hover { background: color-mix(in oklch, var(--primary) 10%, transparent); }

	/* ── Form card ───────────────────────────────────────────── */
	.form-card {
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.4rem;
		padding: 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
		position: relative;
	}
	.form-card::before {
		content: '';
		position: absolute;
		top: -1px; left: 1.5rem; right: 1.5rem;
		height: 2px;
		background: var(--primary);
		opacity: 0.55;
		border-radius: 0 0 2px 2px;
	}

	.pick-label {
		font-size: 0.62rem;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--muted-foreground);
	}
	.type-grid { display: flex; gap: 0.75rem; flex-wrap: wrap; }
	.type-btn {
		display: flex;
		align-items: center;
		gap: 0.85rem;
		padding: 0.85rem 1.25rem;
		border: 1px solid var(--border);
		border-radius: 0.4rem;
		background: var(--background);
		cursor: pointer;
		transition: border-color 150ms ease, background 150ms ease;
		min-width: 180px;
	}
	.type-btn:hover {
		border-color: var(--primary);
		background: color-mix(in oklch, var(--primary) 5%, var(--background));
	}
	.type-icon {
		font-size: 1rem;
		color: var(--primary);
		opacity: 0.8;
		flex-shrink: 0;
		width: 20px;
		text-align: center;
	}
	.type-info { display: flex; flex-direction: column; gap: 0.15rem; text-align: left; }
	.type-name { font-size: 0.75rem; letter-spacing: 0.04em; color: var(--foreground); }
	.type-desc { font-size: 0.62rem; color: var(--muted-foreground); letter-spacing: 0.02em; }

	.form-header { display: flex; align-items: center; gap: 0.6rem; }
	.form-type { font-size: 0.72rem; letter-spacing: 0.08em; color: var(--primary); opacity: 0.9; }

	.field { display: flex; flex-direction: column; gap: 0.4rem; }
	.field-label {
		font-size: 0.62rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: color-mix(in oklch, var(--foreground) 60%, transparent);
	}
	.field-opt { text-transform: none; letter-spacing: 0; opacity: 0.65; }
	.field-input, .field-textarea {
		padding: 0.42rem 0.65rem;
		background: var(--background);
		border: 1px solid color-mix(in oklch, var(--border) 80%, transparent);
		border-radius: 0.2rem;
		font-size: 0.75rem;
		color: var(--foreground);
		letter-spacing: 0.02em;
		transition: border-color 120ms ease;
	}
	.field-textarea { resize: vertical; }
	.field-input:focus, .field-textarea:focus {
		border-color: color-mix(in oklch, var(--primary) 50%, var(--border));
		outline: none;
	}
	.field-hint { font-size: 0.65rem; color: var(--muted-foreground); letter-spacing: 0.01em; line-height: 1.5; }

	/* ── KV editor ─────────────────────────────────────────── */
	.kv-section { display: flex; flex-direction: column; gap: 0.25rem; }
	.kv-row { display: flex; align-items: center; gap: 0.4rem; }
	.kv-input {
		flex: 1;
		padding: 0.38rem 0.6rem;
		background: var(--background);
		border: 1px solid color-mix(in oklch, var(--border) 80%, transparent);
		border-radius: 0.2rem;
		font-size: 0.75rem;
		color: var(--foreground);
		letter-spacing: 0.02em;
		transition: border-color 120ms ease;
		min-width: 0;
	}
	.kv-input:focus { border-color: color-mix(in oklch, var(--primary) 45%, var(--border)); outline: none; }
	.kv-sep { font-size: 0.75rem; color: var(--muted-foreground); opacity: 0.5; flex-shrink: 0; }
	.kv-remove {
		width: 20px; height: 20px;
		display: flex; align-items: center; justify-content: center;
		font-size: 0.85rem;
		color: color-mix(in oklch, var(--muted-foreground) 50%, transparent);
		border-radius: 3px;
		flex-shrink: 0;
		transition: color 120ms ease, background 120ms ease;
	}
	.kv-remove:hover:not(:disabled) {
		color: var(--destructive);
		background: color-mix(in oklch, var(--destructive) 10%, transparent);
	}
	.kv-remove:disabled { opacity: 0.2; cursor: not-allowed; }
	.kv-add {
		font-size: 0.65rem;
		letter-spacing: 0.06em;
		color: var(--primary);
		margin-top: 0.15rem;
		padding: 0.15rem 0;
		transition: opacity 150ms ease;
	}
	.kv-add:hover { opacity: 0.75; }

	/* ── MCP list ──────────────────────────────────────────── */
	.mcp-list { display: flex; flex-direction: column; }
	.mcp-item {
		border-bottom: 1px solid color-mix(in oklch, var(--border) 70%, transparent);
		transition: background 150ms ease;
	}
	.mcp-item:first-child { border-top: 1px solid color-mix(in oklch, var(--border) 70%, transparent); }
	.mcp-item.mcp-deleting { background: color-mix(in oklch, var(--card) 60%, transparent); }
	.mcp-row { display: flex; align-items: center; gap: 0.85rem; padding: 0.85rem 0; }

	.mcp-badge {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 22px;
		font-size: 0.72rem;
		color: color-mix(in oklch, var(--primary) 65%, var(--muted-foreground));
		flex-shrink: 0;
	}
	.mcp-badge--http { color: color-mix(in oklch, var(--primary) 85%, transparent); }

	.mcp-name { flex: 1; font-size: 0.82rem; letter-spacing: 0.04em; color: var(--foreground); }
	.system-badge {
		font-size: 0.56rem;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--primary);
		background: color-mix(in oklch, var(--primary) 10%, transparent);
		border: 1px solid color-mix(in oklch, var(--primary) 22%, transparent);
		border-radius: 0.2rem;
		padding: 0.1rem 0.4rem;
		flex-shrink: 0;
	}
	.mcp-type {
		font-size: 0.62rem;
		letter-spacing: 0.08em;
		color: color-mix(in oklch, var(--muted-foreground) 70%, transparent);
		flex-shrink: 0;
	}
	.mcp-date { font-size: 0.65rem; letter-spacing: 0.02em; color: var(--muted-foreground); flex-shrink: 0; }
	.mcp-del {
		font-size: 0.65rem;
		letter-spacing: 0.06em;
		padding: 0.28rem 0.65rem;
		border-radius: 0.2rem;
		color: var(--muted-foreground);
		flex-shrink: 0;
		transition: color 150ms ease, background 150ms ease;
	}
	.mcp-del:hover { color: var(--destructive); background: color-mix(in oklch, var(--destructive) 8%, transparent); }
	.danger-panel { padding: 0.5rem 0 1rem 1.75rem; display: flex; flex-direction: column; gap: 0.9rem; }

	/* ── Buttons ──────────────────────────────────────────── */
	.btn-primary {
		display: inline-flex; align-items: center; gap: 0.4rem;
		padding: 0.45rem 0.9rem;
		background: var(--primary); color: var(--primary-foreground);
		font-size: 0.68rem; letter-spacing: 0.04em;
		border-radius: 0.25rem; transition: filter 150ms ease;
	}
	.btn-primary:hover:not(:disabled) { filter: brightness(1.08); }
	.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
	.btn-ghost {
		padding: 0.45rem 0.75rem;
		font-size: 0.68rem; letter-spacing: 0.04em;
		color: var(--muted-foreground); border-radius: 0.25rem;
		transition: color 150ms ease, background 150ms ease;
	}
	.btn-ghost:hover { color: var(--foreground); background: var(--muted); }
	.btn-danger {
		display: inline-flex; align-items: center; gap: 0.4rem;
		padding: 0.45rem 0.9rem;
		background: color-mix(in oklch, var(--destructive) 10%, transparent);
		color: var(--destructive);
		border: 1px solid color-mix(in oklch, var(--destructive) 30%, transparent);
		font-size: 0.68rem; letter-spacing: 0.04em;
		border-radius: 0.25rem; transition: background 150ms ease;
	}
	.btn-danger:hover:not(:disabled) { background: color-mix(in oklch, var(--destructive) 16%, transparent); }
	.btn-danger:disabled { opacity: 0.6; cursor: not-allowed; }

	.form-error { font-size: 0.68rem; color: var(--destructive); letter-spacing: 0.02em; }
	.form-actions { display: flex; align-items: center; gap: 0.5rem; }
	.delete-msg { font-size: 0.72rem; color: var(--muted-foreground); letter-spacing: 0.01em; line-height: 1.5; }
	.delete-msg strong { color: var(--foreground); }

	/* ── Empty state ─────────────────────────────────────── */
	.empty-state {
		display: flex; flex-direction: column; align-items: center;
		text-align: center; padding: 4rem 2rem; gap: 0.85rem;
	}
	.empty-icon {
		width: 44px; height: 44px;
		display: flex; align-items: center; justify-content: center;
		background: color-mix(in oklch, var(--primary) 9%, var(--card));
		border: 1px solid color-mix(in oklch, var(--primary) 18%, var(--border));
		border-radius: 0.35rem;
		color: var(--primary); opacity: 0.75; margin-bottom: 0.5rem;
	}
	.empty-title { font-size: 1rem; font-weight: 500; color: var(--foreground); }
	.empty-sub { font-size: 0.85rem; line-height: 1.6; color: var(--muted-foreground); max-width: 28rem; }

	/* ── Spinner ──────────────────────────────────────────── */
	.spinner {
		display: inline-block; width: 10px; height: 10px;
		border-radius: 9999px; border: 1.5px solid currentColor;
		border-right-color: transparent; animation: spin 0.8s linear infinite;
	}
	.spinner--danger { border-color: var(--destructive); border-right-color: transparent; }
	@keyframes spin { to { transform: rotate(360deg); } }
</style>
