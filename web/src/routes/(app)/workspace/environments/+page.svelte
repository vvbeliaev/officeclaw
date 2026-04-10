<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { Icon } from '$lib/icons';

	let { data } = $props();

	type KvPair = { id: number; key: string; value: string; originalValue: string };
	let nextId = 0;

	function kv(key = '', value = '', originalValue = ''): KvPair {
		return { id: nextId++, key, value, originalValue };
	}
	function kvFromDict(dict: Record<string, string>): KvPair[] {
		const pairs = Object.entries(dict).map(([k, v]) => kv(k, '', v));
		return pairs.length ? pairs : [kv()];
	}
	function kvToDict(pairs: KvPair[]): Record<string, string> {
		const out: Record<string, string> = {};
		for (const p of pairs) {
			if (!p.key.trim()) continue;
			out[p.key.trim()] = p.value !== '' ? p.value : p.originalValue;
		}
		return out;
	}

	const envs = $derived(data.envs as { id: string; name: string; createdAt: Date }[]);

	function isLocked(env: { name: string }): boolean {
		return env.name === 'officeclaw';
	}

	// ── New env ──────────────────────────────────────────────
	let newOpen = $state(false);
	let newPairs: KvPair[] = $state([kv()]);
	let newSaving = $state(false);
	let newError: string | null = $state(null);

	const newDerivedName = $derived(newPairs[0]?.key.trim() ?? '');

	function openNew() {
		newOpen = true;
		newPairs = [kv()];
		newError = null;
	}
	function closeNew() { newOpen = false; }

	async function saveNew() {
		const name = newDerivedName;
		if (!name) { newError = 'Enter at least one key'; return; }
		newSaving = true;
		newError = null;
		try {
			const res = await fetch('/api/envs', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ name, values: kvToDict(newPairs) })
			});
			if (!res.ok) { newError = await res.text(); return; }
			newOpen = false;
			await invalidateAll();
		} catch (e) {
			newError = e instanceof Error ? e.message : 'Failed to create';
		} finally {
			newSaving = false;
		}
	}

	// ── Edit env ─────────────────────────────────────────────
	let editId: string | null = $state(null);
	let editPairs: KvPair[] = $state([]);
	let editLoading = $state(false);
	let editSaving = $state(false);
	let editError: string | null = $state(null);

	const editDerivedName = $derived(editPairs[0]?.key.trim() ?? '');

	async function openEdit(env: { id: string; name: string }) {
		editId = env.id;
		editPairs = [];
		editLoading = true;
		editError = null;
		try {
			const res = await fetch(`/api/envs/${env.id}/values`);
			if (!res.ok) throw new Error(await res.text());
			const { values } = await res.json();
			editPairs = kvFromDict(values as Record<string, string>);
		} catch (e) {
			editError = e instanceof Error ? e.message : 'Failed to load values';
		} finally {
			editLoading = false;
		}
	}
	function closeEdit() { editId = null; editError = null; }

	async function saveEdit() {
		if (!editId) return;
		const name = editDerivedName;
		if (!name) { editError = 'First key cannot be empty'; return; }
		editSaving = true;
		editError = null;
		try {
			const res = await fetch(`/api/envs/${editId}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ name, values: kvToDict(editPairs) })
			});
			if (!res.ok) { editError = await res.text(); return; }
			editId = null;
			await invalidateAll();
		} catch (e) {
			editError = e instanceof Error ? e.message : 'Failed to save';
		} finally {
			editSaving = false;
		}
	}

	// ── Delete env ───────────────────────────────────────────
	let deleteId: string | null = $state(null);
	let deleting = $state(false);
	let deleteError: string | null = $state(null);

	async function confirmDelete() {
		if (!deleteId) return;
		deleting = true;
		deleteError = null;
		try {
			const res = await fetch(`/api/envs/${deleteId}`, { method: 'DELETE' });
			if (!res.ok && res.status !== 204) { deleteError = await res.text(); return; }
			deleteId = null;
			await invalidateAll();
		} catch (e) {
			deleteError = e instanceof Error ? e.message : 'Failed to delete';
		} finally {
			deleting = false;
		}
	}

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
		<div class="crumb font-mono">workspace / environments</div>
		<h1 class="title font-display">Environments</h1>
		<p class="tag">secrets and configuration — encrypted at rest, scoped per agent.</p>
		<div class="enc-note font-mono">
			<Icon icon="tabler:lock-filled" width={10} height={10} />
			<span>values are encrypted before storage</span>
		</div>
	</header>

	<div class="body">
		<!-- ── New env form ──────────────────────────────────────── -->
		{#if newOpen}
			<div class="form-card">
				<div class="kv-section">
					<div class="kv-head">
						<span class="kv-col-label font-mono">KEY</span>
						<span class="kv-col-label font-mono">VALUE</span>
					</div>
					{#each newPairs as pair (pair.id)}
						<div class="kv-row">
							<input class="kv-input kv-key font-mono" bind:value={pair.key} placeholder="VARIABLE_NAME" spellcheck="false" />
							<span class="kv-sep font-mono">=</span>
							<input class="kv-input kv-value font-mono" type="password" bind:value={pair.value} placeholder="••••••••" spellcheck="false" autocomplete="new-password" />
							<button class="kv-remove" type="button" aria-label="Remove" onclick={() => { newPairs = newPairs.filter(p => p.id !== pair.id); }} disabled={newPairs.length === 1}>×</button>
						</div>
					{/each}
					<button class="kv-add font-mono" type="button" onclick={() => { newPairs = [...newPairs, kv()]; }}>+ add variable</button>
				</div>
				{#if newError}<p class="form-error font-mono">{newError}</p>{/if}
				<div class="form-actions">
					<button class="btn-primary font-mono" type="button" onclick={saveNew} disabled={newSaving}>
						{#if newSaving}<span class="spinner"></span>saving…{:else}Save{/if}
					</button>
					<button class="btn-ghost font-mono" type="button" onclick={closeNew}>Cancel</button>
				</div>
			</div>
		{/if}

		<!-- ── List header ──────────────────────────────────────── -->
		<div class="list-head">
			<span class="list-count font-mono">{envs.length} environment{envs.length !== 1 ? 's' : ''}</span>
			{#if !newOpen}
				<button class="btn-add font-mono" type="button" onclick={openNew}>
					<Icon icon="oc:spawn" width={11} height={11} />
					New environment
				</button>
			{/if}
		</div>

		<!-- ── Env list ──────────────────────────────────────────── -->
		{#if envs.length === 0}
			<div class="empty-state">
				<div class="empty-icon">
					<Icon icon="tabler:lock" width={22} height={22} />
				</div>
				<p class="empty-title">No environments yet</p>
				<p class="empty-sub">Create named groups of env vars — API keys, tokens, secrets. They're encrypted at rest and scoped to agents you attach them to.</p>
			</div>
		{:else}
			<div class="env-list">
				{#each envs as env (env.id)}
					<div class="env-item" class:expanded={editId === env.id || deleteId === env.id} class:locked={isLocked(env)}>
						<div class="env-row">
							<span class="env-lock" class:env-lock--system={isLocked(env)}>
								<Icon icon={isLocked(env) ? 'tabler:lock-filled' : 'tabler:lock'} width={13} height={13} />
							</span>
							<span class="env-name font-mono">{env.name}</span>
							{#if isLocked(env)}<span class="env-system-badge font-mono">system</span>{/if}
							<span class="env-date font-mono">{relDate(env.createdAt)}</span>
							{#if !isLocked(env)}
								<div class="env-actions">
									<button class="env-btn font-mono" type="button" onclick={() => { if (editId === env.id) { closeEdit(); } else { deleteId = null; openEdit(env); } }}>
										{editId === env.id ? 'close' : 'edit'}
									</button>
									<button class="env-btn env-btn--danger font-mono" type="button" onclick={() => { editId = null; deleteId = deleteId === env.id ? null : env.id; deleteError = null; }}>delete</button>
								</div>
							{/if}
						</div>

						{#if editId === env.id}
							<div class="env-panel">
								{#if editLoading}
									<div class="panel-loading font-mono"><span class="spinner spinner--sm"></span> loading values…</div>
								{:else}
									<div class="kv-section">
										<div class="kv-head">
											<span class="kv-col-label font-mono">KEY</span>
											<span class="kv-col-label font-mono">VALUE <span class="kv-hint">(blank = keep)</span></span>
										</div>
										{#each editPairs as pair (pair.id)}
											<div class="kv-row">
												<input class="kv-input kv-key font-mono" bind:value={pair.key} placeholder="VARIABLE_NAME" spellcheck="false" />
												<span class="kv-sep font-mono">=</span>
												<input class="kv-input kv-value font-mono" type="password" bind:value={pair.value} placeholder="••••••••" spellcheck="false" autocomplete="new-password" />
												<button class="kv-remove" type="button" aria-label="Remove" onclick={() => { editPairs = editPairs.filter(p => p.id !== pair.id); }} disabled={editPairs.length === 1}>×</button>
											</div>
										{/each}
										<button class="kv-add font-mono" type="button" onclick={() => { editPairs = [...editPairs, kv()]; }}>+ add variable</button>
									</div>
									{#if editError}<p class="form-error font-mono">{editError}</p>{/if}
									<div class="form-actions">
										<button class="btn-primary font-mono" type="button" onclick={saveEdit} disabled={editSaving}>
											{#if editSaving}<span class="spinner"></span>saving…{:else}Save changes{/if}
										</button>
										<button class="btn-ghost font-mono" type="button" onclick={closeEdit}>Cancel</button>
									</div>
								{/if}
							</div>
						{/if}

						{#if deleteId === env.id}
							<div class="env-panel env-panel--danger">
								<p class="delete-msg font-mono">Delete <strong>{env.name}</strong>? This cannot be undone — agents using it will lose access to these secrets.</p>
								{#if deleteError}<p class="form-error font-mono">{deleteError}</p>{/if}
								<div class="form-actions">
									<button class="btn-danger font-mono" type="button" onclick={confirmDelete} disabled={deleting}>
										{#if deleting}<span class="spinner spinner--danger"></span>deleting…{:else}Yes, delete{/if}
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

	/* ── Header ─────────────────────────────────────────────── */
	.head { padding: 1.75rem 3rem 2rem; border-bottom: 1px solid var(--border); flex-shrink: 0; }
	.crumb {
		font-size: 0.62rem;
		letter-spacing: 0.16em;
		text-transform: uppercase;
		color: color-mix(in oklch, var(--foreground) 35%, transparent);
		margin-bottom: 0.75rem;
	}
	.title { font-size: 3.5rem; line-height: 1; font-style: italic; letter-spacing: -0.015em; }
	.tag { margin-top: 0.9rem; color: var(--muted-foreground); font-size: 0.95rem; max-width: 36rem; }
	.enc-note {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		margin-top: 0.85rem;
		font-size: 0.6rem;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: color-mix(in oklch, var(--primary) 65%, var(--muted-foreground));
	}

	/* ── Body ────────────────────────────────────────────────── */
	.body { flex: 1; padding: 1.75rem 3rem 4rem; display: flex; flex-direction: column; gap: 1rem; }

	/* ── List header ──────────────────────────────────────── */
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

	/* ── New env form card ───────────────────────────────────── */
	.form-card {
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.45rem;
		padding: 1.25rem 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
		position: relative;
	}
	.form-card::before {
		content: '';
		position: absolute;
		top: -1px;
		left: 1.5rem;
		right: 1.5rem;
		height: 2px;
		background: var(--primary);
		opacity: 0.5;
		border-radius: 0 0 2px 2px;
	}

	/* ── Env list ──────────────────────────────────────────── */
	.env-list { display: flex; flex-direction: column; }
	.env-item {
		border-bottom: 1px solid color-mix(in oklch, var(--border) 70%, transparent);
		border-left: 2px solid transparent;
		padding-left: 0.85rem;
		transition: background 150ms ease, border-left-color 150ms ease;
	}
	.env-item:first-child { border-top: 1px solid color-mix(in oklch, var(--border) 70%, transparent); }
	.env-item:not(.locked):hover {
		background: color-mix(in oklch, var(--primary) 4%, transparent);
		border-left-color: color-mix(in oklch, var(--primary) 40%, transparent);
	}
	.env-item.expanded {
		background: color-mix(in oklch, var(--card) 60%, transparent);
		border-left-color: color-mix(in oklch, var(--primary) 55%, transparent);
	}
	.env-item.locked {
		border-left-color: color-mix(in oklch, var(--primary) 25%, transparent);
	}
	.env-row { display: flex; align-items: center; gap: 0.85rem; padding: 0.9rem 0; }
	.env-lock { color: color-mix(in oklch, var(--primary) 50%, var(--muted-foreground)); flex-shrink: 0; }
	.env-lock--system { color: var(--primary); }
	.env-system-badge {
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
	.env-item.locked .env-name { color: color-mix(in oklch, var(--foreground) 65%, transparent); }
	.env-name { flex: 1; font-size: 0.82rem; letter-spacing: 0.04em; color: var(--foreground); }
	.env-date { font-size: 0.65rem; letter-spacing: 0.02em; color: var(--muted-foreground); flex-shrink: 0; }
	.env-actions { display: flex; gap: 0.25rem; flex-shrink: 0; }
	.env-btn {
		font-size: 0.65rem;
		letter-spacing: 0.06em;
		padding: 0.28rem 0.65rem;
		border-radius: 0.2rem;
		color: var(--muted-foreground);
		transition: color 150ms ease, background 150ms ease;
	}
	.env-btn:hover { color: var(--foreground); background: var(--muted); }
	.env-btn--danger:hover {
		color: var(--destructive);
		background: color-mix(in oklch, var(--destructive) 8%, transparent);
	}

	/* ── Expanded panel ────────────────────────────────────── */
	.env-panel { padding: 0.75rem 0 1.25rem 1.75rem; display: flex; flex-direction: column; gap: 0.9rem; }
	.env-panel--danger { padding: 0.5rem 0 1rem 1.75rem; }
	.panel-loading { display: flex; align-items: center; gap: 0.5rem; font-size: 0.7rem; color: var(--muted-foreground); }

	/* ── KV editor ─────────────────────────────────────────── */
	.kv-section {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		background: color-mix(in oklch, var(--background) 65%, var(--muted));
		border: 1px solid color-mix(in oklch, var(--border) 60%, transparent);
		border-radius: 0.3rem;
		padding: 0.75rem 0.85rem;
	}
	.kv-head {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.5rem;
		padding: 0 1.6rem 0.35rem 0;
		margin-bottom: 0.1rem;
		border-bottom: 1px solid color-mix(in oklch, var(--border) 50%, transparent);
	}
	.kv-col-label {
		font-size: 0.56rem;
		text-transform: uppercase;
		letter-spacing: 0.18em;
		color: color-mix(in oklch, var(--primary) 55%, var(--muted-foreground));
	}
	.kv-hint { text-transform: none; letter-spacing: 0; opacity: 0.6; }
	.kv-row { display: flex; align-items: center; gap: 0.4rem; }
	.kv-input {
		flex: 1;
		padding: 0.35rem 0.55rem;
		background: var(--background);
		border: 1px solid color-mix(in oklch, var(--border) 70%, transparent);
		border-radius: 0.2rem;
		font-size: 0.75rem;
		color: var(--foreground);
		letter-spacing: 0.02em;
		transition: border-color 120ms ease;
		min-width: 0;
	}
	.kv-input:focus { border-color: color-mix(in oklch, var(--primary) 45%, var(--border)); }
	.kv-key { color: color-mix(in oklch, var(--primary) 80%, var(--foreground)); }
	.kv-value { color: color-mix(in oklch, var(--foreground) 75%, var(--muted-foreground)); }
	.kv-sep { font-size: 0.75rem; color: var(--muted-foreground); opacity: 0.45; flex-shrink: 0; }
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
		margin-top: 0.2rem;
		padding: 0.15rem 0;
		transition: opacity 150ms ease;
	}
	.kv-add:hover { opacity: 0.75; }

	/* ── Buttons ──────────────────────────────────────────── */
	.btn-primary {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.45rem 0.9rem;
		background: var(--primary);
		color: var(--primary-foreground);
		font-size: 0.68rem;
		letter-spacing: 0.04em;
		border-radius: 0.25rem;
		transition: filter 150ms ease;
	}
	.btn-primary:hover:not(:disabled) { filter: brightness(1.08); }
	.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
	.btn-ghost {
		padding: 0.45rem 0.75rem;
		font-size: 0.68rem;
		letter-spacing: 0.04em;
		color: var(--muted-foreground);
		border-radius: 0.25rem;
		transition: color 150ms ease, background 150ms ease;
	}
	.btn-ghost:hover { color: var(--foreground); background: var(--muted); }
	.btn-danger {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.45rem 0.9rem;
		background: color-mix(in oklch, var(--destructive) 10%, transparent);
		color: var(--destructive);
		border: 1px solid color-mix(in oklch, var(--destructive) 30%, transparent);
		font-size: 0.68rem;
		letter-spacing: 0.04em;
		border-radius: 0.25rem;
		transition: background 150ms ease;
	}
	.btn-danger:hover:not(:disabled) { background: color-mix(in oklch, var(--destructive) 16%, transparent); }
	.btn-danger:disabled { opacity: 0.6; cursor: not-allowed; }

	.form-error { font-size: 0.68rem; color: var(--destructive); letter-spacing: 0.02em; }
	.form-actions { display: flex; align-items: center; gap: 0.5rem; }
	.delete-msg { font-size: 0.72rem; color: var(--muted-foreground); letter-spacing: 0.01em; line-height: 1.5; }
	.delete-msg strong { color: var(--foreground); }

	/* ── Empty state ─────────────────────────────────────── */
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
		padding: 4rem 2rem;
		gap: 0.85rem;
	}
	.empty-icon {
		width: 46px; height: 46px;
		display: flex; align-items: center; justify-content: center;
		background: color-mix(in oklch, var(--primary) 9%, var(--card));
		border: 1px solid color-mix(in oklch, var(--primary) 18%, var(--border));
		border-radius: 0.4rem;
		color: var(--primary);
		opacity: 0.8;
		margin-bottom: 0.5rem;
		box-shadow: 0 0 20px color-mix(in oklch, var(--primary) 12%, transparent);
	}
	.empty-title { font-size: 1rem; font-weight: 500; color: var(--foreground); }
	.empty-sub { font-size: 0.85rem; line-height: 1.6; color: var(--muted-foreground); max-width: 30rem; }

	/* ── Spinner ──────────────────────────────────────────── */
	.spinner {
		display: inline-block;
		width: 10px; height: 10px;
		border-radius: 9999px;
		border: 1.5px solid currentColor;
		border-right-color: transparent;
		animation: spin 0.8s linear infinite;
	}
	.spinner--sm { width: 8px; height: 8px; border-width: 1px; }
	.spinner--danger { border-color: var(--destructive); border-right-color: transparent; }
	@keyframes spin { to { transform: rotate(360deg); } }
</style>
