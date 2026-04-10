<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { Icon } from '$lib/icons';

	let { data } = $props();

	// ── Key-value pair type used in the editor ───────────────
	// originalValue: what came from the server (used to keep unchanged values)
	// value: what the user has typed (empty = unchanged)
	type KvPair = { id: number; key: string; value: string; originalValue: string };

	let nextId = 0;
	function kv(key = '', value = '', originalValue = ''): KvPair {
		return { id: nextId++, key, value, originalValue };
	}
	function kvFromDict(dict: Record<string, string>): KvPair[] {
		const pairs = Object.entries(dict).map(([k, v]) => kv(k, '', v));
		return pairs.length ? pairs : [kv()];
	}
	// Merge: if user left value blank → keep originalValue; if typed → use new value
	function kvToDict(pairs: KvPair[]): Record<string, string> {
		const out: Record<string, string> = {};
		for (const p of pairs) {
			if (!p.key.trim()) continue;
			out[p.key.trim()] = p.value !== '' ? p.value : p.originalValue;
		}
		return out;
	}

	// ── New env form ─────────────────────────────────────────
	let newOpen = $state(false);
	let newPairs: KvPair[] = $state([kv()]);
	let newSaving = $state(false);
	let newError: string | null = $state(null);

	// Name = first key typed by the user
	const newDerivedName = $derived(newPairs[0]?.key.trim() ?? '');

	function openNew() {
		newOpen = true;
		newPairs = [kv()];
		newError = null;
	}
	function closeNew() {
		newOpen = false;
	}

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

	// ── Edit env form ────────────────────────────────────────
	let editId: string | null = $state(null);
	let editPairs: KvPair[] = $state([]);
	let editLoading = $state(false);
	let editSaving = $state(false);
	let editError: string | null = $state(null);

	// Name follows first key (kept in sync)
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

	function closeEdit() {
		editId = null;
		editError = null;
	}

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

	// ── Relative date helper ─────────────────────────────────
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
		const mo = Math.floor(dd / 30);
		return `${mo}mo ago`;
	}

	const isEnvs = $derived(data.key === 'environments');
	const envs = $derived(data.envs as { id: string; name: string; createdAt: Date }[] | null);

	function isLocked(env: { name: string }): boolean {
		return env.name === 'officeclaw';
	}
</script>

<div class="shell">
	<header class="head">
		<div class="crumb font-mono">workspace / {data.key}</div>
		<h1 class="title font-display">{data.section.title}</h1>
		<p class="tag">{data.section.tagline}</p>
	</header>

	{#if isEnvs && envs !== null}
		<!-- ── Environments section ──────────────────────────── -->
		<div class="env-body">

			<!-- New env form (appears at top when open) -->
			{#if newOpen}
				<div class="env-form-card">
					<div class="kv-section">
						<div class="kv-head">
							<span class="kv-col-label font-mono">KEY</span>
							<span class="kv-col-label font-mono">VALUE</span>
						</div>
						{#each newPairs as pair (pair.id)}
							<div class="kv-row">
								<input
									class="kv-input font-mono"
									bind:value={pair.key}
									placeholder="VARIABLE_NAME"
									spellcheck="false"
								/>
								<span class="kv-sep font-mono">=</span>
								<input
									class="kv-input kv-value font-mono"
									type="password"
									bind:value={pair.value}
									placeholder="••••••••"
									spellcheck="false"
									autocomplete="new-password"
								/>
								<button
									class="kv-remove"
									type="button"
									aria-label="Remove"
									onclick={() => { newPairs = newPairs.filter(p => p.id !== pair.id); }}
									disabled={newPairs.length === 1}
								>×</button>
							</div>
						{/each}
						<button
							class="kv-add font-mono"
							type="button"
							onclick={() => { newPairs = [...newPairs, kv()]; }}
						>+ add variable</button>
					</div>

					{#if newError}
						<p class="form-error font-mono">{newError}</p>
					{/if}

					<div class="form-actions">
						<button class="btn-primary font-mono" type="button" onclick={saveNew} disabled={newSaving}>
							{#if newSaving}<span class="spinner"></span>saving…{:else}Save{/if}
						</button>
						<button class="btn-ghost font-mono" type="button" onclick={closeNew}>Cancel</button>
					</div>
				</div>
			{/if}

			<!-- Header row with action -->
			<div class="list-head">
				<span class="list-count font-mono">
					{envs.length} environment{envs.length !== 1 ? 's' : ''}
				</span>
				{#if !newOpen}
					<button class="btn-add font-mono" type="button" onclick={openNew}>
						<Icon icon="oc:spawn" width={11} height={11} />
						New environment
					</button>
				{/if}
			</div>

			<!-- Empty state -->
			{#if envs.length === 0}
				<div class="empty-state">
					<div class="empty-icon">
						<Icon icon="tabler:lock" width={22} height={22} />
					</div>
					<p class="empty-title">No environments yet</p>
					<p class="empty-sub">
						Create named groups of env vars — API keys, tokens, secrets.
						They're encrypted at rest and scoped to agents you attach them to.
					</p>
				</div>
			{:else}
				<div class="env-list">
					{#each envs as env (env.id)}
						<div class="env-item" class:expanded={editId === env.id || deleteId === env.id} class:locked={isLocked(env)}>
							<!-- Main row -->
							<div class="env-row">
								<span class="env-lock" class:env-lock--system={isLocked(env)}>
									<Icon icon={isLocked(env) ? 'tabler:lock-filled' : 'tabler:lock'} width={13} height={13} />
								</span>
								<span class="env-name font-mono">{env.name}</span>
								{#if isLocked(env)}
									<span class="env-system-badge font-mono">system</span>
								{/if}
								<span class="env-date font-mono">{relDate(env.createdAt)}</span>
								{#if !isLocked(env)}
									<div class="env-actions">
										<button
											class="env-btn font-mono"
											type="button"
											onclick={() => {
												if (editId === env.id) { closeEdit(); }
												else { deleteId = null; openEdit(env); }
											}}
										>
											{editId === env.id ? 'close' : 'edit'}
										</button>
										<button
											class="env-btn env-btn--danger font-mono"
											type="button"
											onclick={() => {
												editId = null;
												deleteId = deleteId === env.id ? null : env.id;
												deleteError = null;
											}}
										>delete</button>
									</div>
								{/if}
							</div>

							<!-- Edit panel -->
							{#if editId === env.id}
								<div class="env-panel">
									{#if editLoading}
										<div class="panel-loading font-mono">
											<span class="spinner spinner--sm"></span> loading values…
										</div>
									{:else}
										<div class="kv-section">
											<div class="kv-head">
												<span class="kv-col-label font-mono">KEY</span>
												<span class="kv-col-label font-mono">VALUE <span class="kv-hint">(blank = keep)</span></span>
											</div>
											{#each editPairs as pair (pair.id)}
												<div class="kv-row">
													<input
														class="kv-input font-mono"
														bind:value={pair.key}
														placeholder="VARIABLE_NAME"
														spellcheck="false"
													/>
													<span class="kv-sep font-mono">=</span>
													<input
														class="kv-input kv-value font-mono"
														type="password"
														bind:value={pair.value}
														placeholder="••••••••"
														spellcheck="false"
														autocomplete="new-password"
													/>
													<button
														class="kv-remove"
														type="button"
														aria-label="Remove"
														onclick={() => { editPairs = editPairs.filter(p => p.id !== pair.id); }}
														disabled={editPairs.length === 1}
													>×</button>
												</div>
											{/each}
											<button
												class="kv-add font-mono"
												type="button"
												onclick={() => { editPairs = [...editPairs, kv()]; }}
											>+ add variable</button>
										</div>

										{#if editError}
											<p class="form-error font-mono">{editError}</p>
										{/if}

										<div class="form-actions">
											<button class="btn-primary font-mono" type="button" onclick={saveEdit} disabled={editSaving}>
												{#if editSaving}<span class="spinner"></span>saving…{:else}Save changes{/if}
											</button>
											<button class="btn-ghost font-mono" type="button" onclick={closeEdit}>Cancel</button>
										</div>
									{/if}
								</div>
							{/if}

							<!-- Delete confirmation panel -->
							{#if deleteId === env.id}
								<div class="env-panel env-panel--danger">
									<p class="delete-msg font-mono">
										Delete <strong>{env.name}</strong>? This cannot be undone — agents using it will lose access to these secrets.
									</p>
									{#if deleteError}
										<p class="form-error font-mono">{deleteError}</p>
									{/if}
									<div class="form-actions">
										<button class="btn-danger font-mono" type="button" onclick={confirmDelete} disabled={deleting}>
											{#if deleting}<span class="spinner spinner--danger"></span>deleting…{:else}Yes, delete{/if}
										</button>
										<button class="btn-ghost font-mono" type="button" onclick={() => { deleteId = null; deleteError = null; }}>
											Cancel
										</button>
									</div>
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		</div>

	{:else}
		<!-- ── Stub for other sections ───────────────────────── -->
		<div class="empty">
			<div class="empty-card">
				<div class="quote font-display">
					<em>"Ask your Admin"</em>
				</div>
				<p class="desc">
					This surface is intentionally read-only. Most configuration in OfficeClaw
					happens through conversation with your Admin agent — <em>"add a GitHub
					skill to my research agent"</em>, <em>"connect my Slack"</em>, and so on.
					This page will soon show what Admin has set up for you.
				</p>
				<a href="/" class="back font-mono">← back to Admin</a>
			</div>
		</div>
	{/if}
</div>

<style>
	.shell {
		flex: 1;
		display: flex;
		flex-direction: column;
		overflow-y: auto;
	}

	/* ── Header ─────────────────────────────────────────────── */
	.head {
		padding: 3rem 3rem 2rem;
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
		font-size: 3.25rem;
		line-height: 1;
		font-style: italic;
		letter-spacing: -0.015em;
	}

	.tag {
		margin-top: 0.85rem;
		color: var(--muted-foreground);
		font-size: 0.95rem;
		max-width: 36rem;
	}

	/* ── Env body ─────────────────────────────────────────── */
	.env-body {
		flex: 1;
		padding: 2rem 3rem 4rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

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

	.btn-add:hover {
		background: color-mix(in oklch, var(--primary) 10%, transparent);
	}

	/* ── New env form card ───────────────────────────────── */
	.env-form-card {
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.4rem;
		padding: 1.25rem 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
		position: relative;
	}

	.env-form-card::before {
		content: '';
		position: absolute;
		top: -1px;
		left: 1.5rem;
		right: 1.5rem;
		height: 2px;
		background: var(--primary);
		opacity: 0.55;
		border-radius: 0 0 2px 2px;
	}

	/* ── Env list ─────────────────────────────────────────── */
	.env-list {
		display: flex;
		flex-direction: column;
		gap: 0;
	}

	.env-item {
		border-bottom: 1px solid color-mix(in oklch, var(--border) 70%, transparent);
		transition: background 150ms ease;
	}

	.env-item:first-child {
		border-top: 1px solid color-mix(in oklch, var(--border) 70%, transparent);
	}

	.env-item.expanded {
		background: color-mix(in oklch, var(--card) 60%, transparent);
	}

	.env-row {
		display: flex;
		align-items: center;
		gap: 0.85rem;
		padding: 0.85rem 0;
	}

	.env-lock {
		color: color-mix(in oklch, var(--primary) 55%, var(--muted-foreground));
		flex-shrink: 0;
	}

	.env-lock--system {
		color: var(--primary);
	}

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

	.env-item.locked .env-name {
		color: color-mix(in oklch, var(--foreground) 65%, transparent);
	}

	.env-name {
		flex: 1;
		font-size: 0.82rem;
		letter-spacing: 0.04em;
		color: var(--foreground);
	}

	.env-date {
		font-size: 0.65rem;
		letter-spacing: 0.02em;
		color: var(--muted-foreground);
		flex-shrink: 0;
	}

	.env-actions {
		display: flex;
		gap: 0.25rem;
		flex-shrink: 0;
	}

	.env-btn {
		font-size: 0.65rem;
		letter-spacing: 0.06em;
		padding: 0.28rem 0.65rem;
		border-radius: 0.2rem;
		color: var(--muted-foreground);
		transition: color 150ms ease, background 150ms ease;
	}

	.env-btn:hover {
		color: var(--foreground);
		background: var(--muted);
	}

	.env-btn--danger:hover {
		color: var(--destructive);
		background: color-mix(in oklch, var(--destructive) 8%, transparent);
	}

	/* ── Expanded panel ───────────────────────────────────── */
	.env-panel {
		padding: 0.75rem 0 1.25rem 1.75rem;
		display: flex;
		flex-direction: column;
		gap: 0.9rem;
	}

	.env-panel--danger {
		padding: 0.5rem 0 1rem 1.75rem;
	}

	.panel-loading {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.7rem;
		color: var(--muted-foreground);
	}

	/* ── Form elements ────────────────────────────────────── */
	.form-error {
		font-size: 0.68rem;
		color: var(--destructive);
		letter-spacing: 0.02em;
	}

	.form-actions {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	/* ── KV editor ────────────────────────────────────────── */
	.kv-section {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.kv-head {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.5rem;
		padding: 0 1.6rem 0.25rem 0;
		margin-bottom: 0.15rem;
	}

	.kv-col-label {
		font-size: 0.56rem;
		text-transform: uppercase;
		letter-spacing: 0.18em;
		color: color-mix(in oklch, var(--muted-foreground) 60%, transparent);
	}

	.kv-hint {
		text-transform: none;
		letter-spacing: 0;
		opacity: 0.6;
	}

	.kv-row {
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}

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

	.kv-input:focus {
		border-color: color-mix(in oklch, var(--primary) 45%, var(--border));
	}

	.kv-value {
		color: color-mix(in oklch, var(--foreground) 75%, var(--muted-foreground));
	}

	.kv-sep {
		font-size: 0.75rem;
		color: var(--muted-foreground);
		opacity: 0.5;
		flex-shrink: 0;
	}

	.kv-remove {
		width: 20px;
		height: 20px;
		display: flex;
		align-items: center;
		justify-content: center;
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

	.kv-remove:disabled {
		opacity: 0.2;
		cursor: not-allowed;
	}

	.kv-add {
		font-size: 0.65rem;
		letter-spacing: 0.06em;
		color: var(--primary);
		margin-top: 0.15rem;
		padding: 0.15rem 0;
		transition: opacity 150ms ease;
	}

	.kv-add:hover {
		opacity: 0.75;
	}

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

	.btn-primary:hover:not(:disabled) {
		filter: brightness(1.08);
	}

	.btn-primary:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.btn-ghost {
		padding: 0.45rem 0.75rem;
		font-size: 0.68rem;
		letter-spacing: 0.04em;
		color: var(--muted-foreground);
		border-radius: 0.25rem;
		transition: color 150ms ease, background 150ms ease;
	}

	.btn-ghost:hover {
		color: var(--foreground);
		background: var(--muted);
	}

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

	.btn-danger:hover:not(:disabled) {
		background: color-mix(in oklch, var(--destructive) 16%, transparent);
	}

	.btn-danger:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.delete-msg {
		font-size: 0.72rem;
		color: var(--muted-foreground);
		letter-spacing: 0.01em;
		line-height: 1.5;
	}

	.delete-msg strong {
		color: var(--foreground);
	}

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
		width: 44px;
		height: 44px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: color-mix(in oklch, var(--primary) 9%, var(--card));
		border: 1px solid color-mix(in oklch, var(--primary) 18%, var(--border));
		border-radius: 0.35rem;
		color: var(--primary);
		opacity: 0.75;
		margin-bottom: 0.5rem;
	}

	.empty-title {
		font-size: 1rem;
		font-weight: 500;
		color: var(--foreground);
	}

	.empty-sub {
		font-size: 0.85rem;
		line-height: 1.6;
		color: var(--muted-foreground);
		max-width: 28rem;
	}

	/* ── Spinner ─────────────────────────────────────────── */
	.spinner {
		display: inline-block;
		width: 10px;
		height: 10px;
		border-radius: 9999px;
		border: 1.5px solid currentColor;
		border-right-color: transparent;
		animation: spin 0.8s linear infinite;
	}

	.spinner--sm {
		width: 8px;
		height: 8px;
		border-width: 1px;
	}

	.spinner--danger {
		border-color: var(--destructive);
		border-right-color: transparent;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* ── Stub sections (non-env) ──────────────────────────── */
	.empty {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 3rem;
	}

	.empty-card {
		max-width: 32rem;
		text-align: center;
		padding: 2.5rem 2rem;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.35rem;
		position: relative;
	}

	.empty-card::before {
		content: '';
		position: absolute;
		top: -1px;
		left: 2rem;
		right: 2rem;
		height: 2px;
		background: var(--primary);
		opacity: 0.6;
	}

	.quote {
		font-size: 1.75rem;
		line-height: 1.1;
		color: var(--foreground);
		margin-bottom: 1.25rem;
	}

	.quote em {
		color: var(--primary);
	}

	.desc {
		color: var(--muted-foreground);
		font-size: 0.88rem;
		line-height: 1.65;
		margin-bottom: 2rem;
	}

	.desc em {
		color: var(--foreground);
		font-style: italic;
	}

	.back {
		font-size: 0.7rem;
		color: var(--primary);
		letter-spacing: 0.04em;
		text-decoration: none;
	}

	.back:hover {
		text-decoration: underline;
		text-underline-offset: 4px;
	}
</style>
