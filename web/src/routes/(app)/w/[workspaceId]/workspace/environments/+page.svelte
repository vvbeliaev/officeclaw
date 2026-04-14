<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { Icon } from '$lib/icons';

	let { data } = $props();

	type EnvRecord = { id: string; name: string; category: string | null; createdAt: Date };
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

	const allEnvs = $derived(data.envs as EnvRecord[]);
	const llmEnvs = $derived(allEnvs.filter((e) => e.category === 'llm-provider'));
	const genericEnvs = $derived(allEnvs.filter((e) => e.category !== 'llm-provider'));

	function isLocked(env: EnvRecord): boolean {
		return env.category === 'system';
	}

	// ── LLM form state ────────────────────────────────────────
	type LlmFields = { apiKey: string; baseUrl: string; model: string };
	let llmNewOpen = $state(false);
	let llmNewFields: LlmFields = $state({ apiKey: '', baseUrl: '', model: '' });
	let llmNewName = $state('');
	let llmNewSaving = $state(false);
	let llmNewError: string | null = $state(null);

	function openLlmNew() {
		llmNewOpen = true;
		llmNewFields = { apiKey: '', baseUrl: '', model: '' };
		llmNewName = '';
		llmNewError = null;
	}
	function closeLlmNew() { llmNewOpen = false; }

	async function saveLlmNew() {
		if (!llmNewName.trim()) { llmNewError = 'Name is required'; return; }
		llmNewSaving = true;
		llmNewError = null;
		try {
			const res = await fetch('/api/envs', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					name: llmNewName.trim(),
					category: 'llm-provider',
					values: {
						OFFICECLAW_LLM_API_KEY: llmNewFields.apiKey,
						OFFICECLAW_LLM_BASE_URL: llmNewFields.baseUrl,
						OFFICECLAW_LLM_MODEL: llmNewFields.model,
					}
				})
			});
			if (!res.ok) { llmNewError = await res.text(); return; }
			llmNewOpen = false;
			await invalidateAll();
		} catch (e) {
			llmNewError = e instanceof Error ? e.message : 'Failed to create';
		} finally {
			llmNewSaving = false;
		}
	}

	// ── LLM edit ─────────────────────────────────────────────
	let llmEditId: string | null = $state(null);
	let llmEditName = $state('');
	let llmEditFields: LlmFields = $state({ apiKey: '', baseUrl: '', model: '' });
	let llmEditLoading = $state(false);
	let llmEditSaving = $state(false);
	let llmEditError: string | null = $state(null);

	async function openLlmEdit(env: EnvRecord) {
		llmEditId = env.id;
		llmEditName = env.name;
		llmEditFields = { apiKey: '', baseUrl: '', model: '' };
		llmEditLoading = true;
		llmEditError = null;
		try {
			const res = await fetch(`/api/envs/${env.id}/values`);
			if (!res.ok) throw new Error(await res.text());
			const { values } = await res.json() as { values: Record<string, string> };
			llmEditFields = {
				apiKey: values['OFFICECLAW_LLM_API_KEY'] ?? '',
				baseUrl: values['OFFICECLAW_LLM_BASE_URL'] ?? '',
				model: values['OFFICECLAW_LLM_MODEL'] ?? '',
			};
		} catch (e) {
			llmEditError = e instanceof Error ? e.message : 'Failed to load';
		} finally {
			llmEditLoading = false;
		}
	}
	function closeLlmEdit() { llmEditId = null; llmEditError = null; }

	async function saveLlmEdit() {
		if (!llmEditId) return;
		llmEditSaving = true;
		llmEditError = null;
		try {
			const res = await fetch(`/api/envs/${llmEditId}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					name: llmEditName,
					values: {
						OFFICECLAW_LLM_API_KEY: llmEditFields.apiKey,
						OFFICECLAW_LLM_BASE_URL: llmEditFields.baseUrl,
						OFFICECLAW_LLM_MODEL: llmEditFields.model,
					}
				})
			});
			if (!res.ok) { llmEditError = await res.text(); return; }
			llmEditId = null;
			await invalidateAll();
		} catch (e) {
			llmEditError = e instanceof Error ? e.message : 'Failed to save';
		} finally {
			llmEditSaving = false;
		}
	}

	// ── Generic env new ───────────────────────────────────────
	let newOpen = $state(false);
	let newPairs: KvPair[] = $state([kv()]);
	let newSaving = $state(false);
	let newError: string | null = $state(null);

	const newDerivedName = $derived(newPairs[0]?.key.trim() ?? '');

	function openNew() { newOpen = true; newPairs = [kv()]; newError = null; }
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

	// ── Generic env edit ──────────────────────────────────────
	let editId: string | null = $state(null);
	let editPairs: KvPair[] = $state([]);
	let editLoading = $state(false);
	let editSaving = $state(false);
	let editError: string | null = $state(null);

	const editDerivedName = $derived(editPairs[0]?.key.trim() ?? '');

	async function openEdit(env: EnvRecord) {
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

	// ── Delete (shared) ───────────────────────────────────────
	let deleteId: string | null = $state(null);
	let deleteName = $state('');
	let deleting = $state(false);
	let deleteError: string | null = $state(null);

	function openDelete(env: EnvRecord) {
		editId = null;
		llmEditId = null;
		deleteId = env.id;
		deleteName = env.name;
		deleteError = null;
	}

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

		<!-- ════════════════════════════════════════════════════
		     LLM PROVIDERS SECTION
		     ════════════════════════════════════════════════════ -->
		<section class="section">
			<div class="section-head">
				<div class="section-title-row">
					<div class="section-icon">
						<Icon icon="tabler:brain" width={14} height={14} />
					</div>
					<div>
						<h2 class="section-title font-mono">LLM Providers</h2>
						<p class="section-sub">OpenAI-compatible endpoints — API key, base URL, and model for your agents.</p>
					</div>
				</div>
				{#if !llmNewOpen}
					<button class="btn-add font-mono" type="button" onclick={openLlmNew}>
						<Icon icon="oc:spawn" width={11} height={11} />
						Add provider
					</button>
				{/if}
			</div>

			<!-- New LLM form -->
			{#if llmNewOpen}
				<div class="llm-form-card">
					<div class="llm-form-name-row">
						<label class="llm-label font-mono" for="llm-new-name">NAME</label>
						<input
							id="llm-new-name"
							class="llm-name-input font-mono"
							bind:value={llmNewName}
							placeholder="my-provider"
							spellcheck="false"
						/>
					</div>
					<div class="llm-fields">
						<div class="llm-field">
							<label class="llm-label font-mono" for="llm-new-base-url">BASE URL</label>
							<input
								id="llm-new-base-url"
								class="llm-input font-mono"
								bind:value={llmNewFields.baseUrl}
								placeholder="https://api.openai.com/v1"
								spellcheck="false"
								autocomplete="off"
							/>
						</div>
						<div class="llm-field">
							<label class="llm-label font-mono" for="llm-new-model">MODEL</label>
							<input
								id="llm-new-model"
								class="llm-input font-mono"
								bind:value={llmNewFields.model}
								placeholder="gpt-4o-mini"
								spellcheck="false"
								autocomplete="off"
							/>
						</div>
						<div class="llm-field llm-field--full">
							<label class="llm-label font-mono" for="llm-new-api-key">API KEY</label>
							<input
								id="llm-new-api-key"
								class="llm-input font-mono"
								type="password"
								bind:value={llmNewFields.apiKey}
								placeholder="sk-••••••••"
								spellcheck="false"
								autocomplete="new-password"
							/>
						</div>
					</div>
					{#if llmNewError}<p class="form-error font-mono">{llmNewError}</p>{/if}
					<div class="form-actions">
						<button class="btn-primary font-mono" type="button" onclick={saveLlmNew} disabled={llmNewSaving}>
							{#if llmNewSaving}<span class="spinner"></span>saving…{:else}Save provider{/if}
						</button>
						<button class="btn-ghost font-mono" type="button" onclick={closeLlmNew}>Cancel</button>
					</div>
				</div>
			{/if}

			<!-- LLM provider list -->
			{#if llmEnvs.length === 0 && !llmNewOpen}
				<div class="llm-empty font-mono">
					No LLM providers yet — add one to let agents call a language model.
				</div>
			{:else}
				<div class="llm-list">
					{#each llmEnvs as env (env.id)}
						<div class="llm-item" class:expanded={llmEditId === env.id || deleteId === env.id}>
							<div class="llm-row">
								<div class="llm-row-left">
									<span class="llm-dot"></span>
									<span class="llm-name font-mono">{env.name}</span>
								</div>
								<div class="llm-row-right">
									<span class="llm-date font-mono">{relDate(env.createdAt)}</span>
									<div class="env-actions">
										<button class="env-btn font-mono" type="button" onclick={() => {
											if (llmEditId === env.id) { closeLlmEdit(); }
											else { deleteId = null; openLlmEdit(env); }
										}}>
											{llmEditId === env.id ? 'close' : 'edit'}
										</button>
										<button class="env-btn env-btn--danger font-mono" type="button" onclick={() => {
											closeLlmEdit();
											if (deleteId === env.id) { deleteId = null; }
											else { openDelete(env); }
										}}>delete</button>
									</div>
								</div>
							</div>

							{#if llmEditId === env.id}
								<div class="env-panel">
									{#if llmEditLoading}
										<div class="panel-loading font-mono"><span class="spinner spinner--sm"></span> loading…</div>
									{:else}
										<div class="llm-fields">
											<div class="llm-field">
												<label class="llm-label font-mono">BASE URL</label>
												<input class="llm-input font-mono" bind:value={llmEditFields.baseUrl} placeholder="https://api.openai.com/v1" spellcheck="false" autocomplete="off" />
											</div>
											<div class="llm-field">
												<label class="llm-label font-mono">MODEL</label>
												<input class="llm-input font-mono" bind:value={llmEditFields.model} placeholder="gpt-4o-mini" spellcheck="false" autocomplete="off" />
											</div>
											<div class="llm-field llm-field--full">
												<label class="llm-label font-mono">API KEY <span class="kv-hint">(blank = keep)</span></label>
												<input class="llm-input font-mono" type="password" bind:value={llmEditFields.apiKey} placeholder="sk-••••••••" spellcheck="false" autocomplete="new-password" />
											</div>
										</div>
										{#if llmEditError}<p class="form-error font-mono">{llmEditError}</p>{/if}
										<div class="form-actions">
											<button class="btn-primary font-mono" type="button" onclick={saveLlmEdit} disabled={llmEditSaving}>
												{#if llmEditSaving}<span class="spinner"></span>saving…{:else}Save changes{/if}
											</button>
											<button class="btn-ghost font-mono" type="button" onclick={closeLlmEdit}>Cancel</button>
										</div>
									{/if}
								</div>
							{/if}

							{#if deleteId === env.id}
								<div class="env-panel env-panel--danger">
									<p class="delete-msg font-mono">Delete <strong>{deleteName}</strong>? Agents using this provider will lose LLM access.</p>
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
		</section>

		<div class="section-divider"></div>

		<!-- ════════════════════════════════════════════════════
		     GENERIC ENVS SECTION
		     ════════════════════════════════════════════════════ -->
		<section class="section">
			<div class="section-head">
				<div class="section-title-row">
					<div class="section-icon">
						<Icon icon="tabler:lock" width={14} height={14} />
					</div>
					<div>
						<h2 class="section-title font-mono">Secret Environments</h2>
						<p class="section-sub">Named groups of env vars — API keys, tokens, credentials.</p>
					</div>
				</div>
				{#if !newOpen}
					<button class="btn-add font-mono" type="button" onclick={openNew}>
						<Icon icon="oc:spawn" width={11} height={11} />
						New environment
					</button>
				{/if}
			</div>

			<!-- New generic env form -->
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

			<!-- Generic env list -->
			{#if genericEnvs.length === 0 && !newOpen}
				<div class="empty-state">
					<div class="empty-icon">
						<Icon icon="tabler:lock" width={22} height={22} />
					</div>
					<p class="empty-title">No environments yet</p>
					<p class="empty-sub">Create named groups of env vars — API keys, tokens, secrets. Encrypted at rest and scoped to agents you attach them to.</p>
				</div>
			{:else}
				<div class="env-list">
					{#each genericEnvs as env (env.id)}
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
										<button class="env-btn font-mono" type="button" onclick={() => {
											if (editId === env.id) { closeEdit(); }
											else { deleteId = null; openEdit(env); }
										}}>
											{editId === env.id ? 'close' : 'edit'}
										</button>
										<button class="env-btn env-btn--danger font-mono" type="button" onclick={() => {
											editId = null;
											if (deleteId === env.id) { deleteId = null; }
											else { openDelete(env); }
										}}>delete</button>
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
									<p class="delete-msg font-mono">Delete <strong>{deleteName}</strong>? This cannot be undone — agents using it will lose access to these secrets.</p>
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
		</section>
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
	.body { flex: 1; padding: 1.75rem 3rem 4rem; display: flex; flex-direction: column; gap: 0; }

	/* ── Sections ────────────────────────────────────────────── */
	.section { display: flex; flex-direction: column; gap: 1rem; padding: 1.5rem 0; }
	.section-divider { height: 1px; background: var(--border); opacity: 0.5; }

	.section-head {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 1rem;
	}
	.section-title-row {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
	}
	.section-icon {
		width: 30px; height: 30px;
		flex-shrink: 0;
		display: flex; align-items: center; justify-content: center;
		background: color-mix(in oklch, var(--primary) 9%, var(--card));
		border: 1px solid color-mix(in oklch, var(--primary) 18%, var(--border));
		border-radius: 0.35rem;
		color: var(--primary);
		margin-top: 0.1rem;
	}
	.section-title {
		font-size: 0.72rem;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--foreground);
		margin-bottom: 0.2rem;
	}
	.section-sub { font-size: 0.78rem; color: var(--muted-foreground); line-height: 1.5; max-width: 34rem; }

	/* ── LLM provider cards ──────────────────────────────────── */
	.llm-list { display: flex; flex-direction: column; gap: 0.5rem; }
	.llm-item {
		border: 1px solid color-mix(in oklch, var(--border) 70%, transparent);
		border-radius: 0.4rem;
		overflow: hidden;
		transition: border-color 150ms ease;
	}
	.llm-item:hover { border-color: color-mix(in oklch, var(--primary) 35%, var(--border)); }
	.llm-item.expanded { border-color: color-mix(in oklch, var(--primary) 55%, var(--border)); }
	.llm-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.75rem 1rem;
		gap: 1rem;
	}
	.llm-row-left { display: flex; align-items: center; gap: 0.6rem; }
	.llm-dot {
		width: 7px; height: 7px;
		border-radius: 9999px;
		background: color-mix(in oklch, var(--primary) 60%, transparent);
		flex-shrink: 0;
	}
	.llm-name { font-size: 0.82rem; letter-spacing: 0.04em; color: var(--foreground); }
	.llm-row-right { display: flex; align-items: center; gap: 0.75rem; }
	.llm-date { font-size: 0.65rem; color: var(--muted-foreground); }

	.llm-empty {
		font-size: 0.72rem;
		letter-spacing: 0.02em;
		color: var(--muted-foreground);
		padding: 1.25rem 0;
	}

	/* ── LLM form ────────────────────────────────────────────── */
	.llm-form-card {
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.45rem;
		padding: 1.25rem 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
		position: relative;
	}
	.llm-form-card::before {
		content: '';
		position: absolute;
		top: -1px; left: 1.5rem; right: 1.5rem;
		height: 2px;
		background: var(--primary);
		opacity: 0.5;
		border-radius: 0 0 2px 2px;
	}
	.llm-form-name-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}
	.llm-name-input {
		flex: 1;
		max-width: 18rem;
		padding: 0.38rem 0.6rem;
		background: var(--background);
		border: 1px solid color-mix(in oklch, var(--border) 70%, transparent);
		border-radius: 0.2rem;
		font-size: 0.78rem;
		color: var(--foreground);
		letter-spacing: 0.04em;
		transition: border-color 120ms ease;
	}
	.llm-name-input:focus { border-color: color-mix(in oklch, var(--primary) 45%, var(--border)); }

	.llm-fields {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.75rem;
		background: color-mix(in oklch, var(--background) 65%, var(--muted));
		border: 1px solid color-mix(in oklch, var(--border) 60%, transparent);
		border-radius: 0.3rem;
		padding: 0.85rem 1rem;
	}
	.llm-field { display: flex; flex-direction: column; gap: 0.3rem; }
	.llm-field--full { grid-column: 1 / -1; }
	.llm-label {
		font-size: 0.56rem;
		text-transform: uppercase;
		letter-spacing: 0.18em;
		color: color-mix(in oklch, var(--primary) 55%, var(--muted-foreground));
	}
	.llm-input {
		padding: 0.38rem 0.6rem;
		background: var(--background);
		border: 1px solid color-mix(in oklch, var(--border) 70%, transparent);
		border-radius: 0.2rem;
		font-size: 0.75rem;
		color: var(--foreground);
		letter-spacing: 0.02em;
		transition: border-color 120ms ease;
	}
	.llm-input:focus { border-color: color-mix(in oklch, var(--primary) 45%, var(--border)); }

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
		top: -1px; left: 1.5rem; right: 1.5rem;
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
	.env-item.locked { border-left-color: color-mix(in oklch, var(--primary) 25%, transparent); }
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
		flex-shrink: 0;
	}
	.btn-add:hover { background: color-mix(in oklch, var(--primary) 10%, transparent); }
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
		padding: 3rem 2rem;
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
