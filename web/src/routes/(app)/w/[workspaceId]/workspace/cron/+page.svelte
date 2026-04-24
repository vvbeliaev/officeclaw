<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { Icon } from '$lib/icons';

	let { data } = $props();

	type Kind = 'at' | 'every' | 'cron';
	type CronRecord = {
		id: string;
		name: string;
		scheduleKind: Kind;
		scheduleAtMs: number | null;
		scheduleEveryMs: number | null;
		scheduleExpr: string | null;
		scheduleTz: string | null;
		message: string;
		deliver: boolean;
		channel: string | null;
		recipient: string | null;
		deleteAfterRun: boolean;
		createdAt: Date;
		updatedAt: Date;
	};

	const crons = $derived(data.crons as CronRecord[]);

	// ── Add wizard ──────────────────────────────────────────────
	let addOpen = $state(false);
	let saving = $state(false);
	let saveError: string | null = $state(null);

	let formName = $state('');
	let formKind: Kind = $state('every');
	let formEveryMin = $state(60);
	let formAtDate = $state('');
	let formCronExpr = $state('0 * * * *');
	let formTz = $state('UTC');
	let formMessage = $state('');
	let formDeliver = $state(false);
	let formChannel = $state('');
	let formRecipient = $state('');
	let formDeleteAfterRun = $state(false);

	// ── Edit ───────────────────────────────────────────────────
	let editId: string | null = $state(null);
	let editSaving = $state(false);
	let editError: string | null = $state(null);

	// ── Delete ─────────────────────────────────────────────────
	let deleteId: string | null = $state(null);
	let deleting = $state(false);
	let deleteError: string | null = $state(null);

	function openAdd() {
		addOpen = true;
		saveError = null;
		formName = '';
		formKind = 'every';
		formEveryMin = 60;
		formAtDate = '';
		formCronExpr = '0 * * * *';
		formTz = 'UTC';
		formMessage = '';
		formDeliver = false;
		formChannel = '';
		formRecipient = '';
		formDeleteAfterRun = false;
	}

	function closeAdd() {
		addOpen = false;
	}

	function buildPayload(): Record<string, unknown> | { error: string } {
		const name = formName.trim();
		if (!name) return { error: 'Name is required' };
		const base: Record<string, unknown> = {
			workspace_id: data.workspace.id,
			name,
			schedule_kind: formKind,
			message: formMessage,
			deliver: formDeliver,
			channel: formDeliver && formChannel.trim() ? formChannel.trim() : null,
			recipient: formDeliver && formRecipient.trim() ? formRecipient.trim() : null,
			delete_after_run: formDeleteAfterRun
		};
		if (formKind === 'every') {
			if (!formEveryMin || formEveryMin < 1) return { error: 'Interval must be ≥ 1 minute' };
			base.schedule_every_ms = Math.round(formEveryMin * 60_000);
		} else if (formKind === 'at') {
			if (!formAtDate) return { error: 'Date/time is required' };
			const ts = new Date(formAtDate).getTime();
			if (!Number.isFinite(ts)) return { error: 'Invalid date/time' };
			base.schedule_at_ms = ts;
		} else {
			if (!formCronExpr.trim()) return { error: 'Cron expression required' };
			base.schedule_expr = formCronExpr.trim();
			if (formTz.trim()) base.schedule_tz = formTz.trim();
		}
		return base;
	}

	async function saveCron() {
		saveError = null;
		const payload = buildPayload();
		if ('error' in payload) {
			saveError = payload.error;
			return;
		}
		saving = true;
		try {
			const res = await fetch('/api/crons', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});
			if (!res.ok) {
				saveError = (await res.text()) || 'Failed to create cron';
				return;
			}
			addOpen = false;
			await invalidateAll();
		} catch (e) {
			saveError = e instanceof Error ? e.message : 'Failed to create cron';
		} finally {
			saving = false;
		}
	}

	function openEdit(c: CronRecord) {
		editId = c.id;
		editError = null;
		formName = c.name;
		formKind = c.scheduleKind;
		formEveryMin = c.scheduleEveryMs ? Math.max(1, Math.round(c.scheduleEveryMs / 60_000)) : 60;
		formAtDate = c.scheduleAtMs ? new Date(c.scheduleAtMs).toISOString().slice(0, 16) : '';
		formCronExpr = c.scheduleExpr ?? '0 * * * *';
		formTz = c.scheduleTz ?? 'UTC';
		formMessage = c.message;
		formDeliver = c.deliver;
		formChannel = c.channel ?? '';
		formRecipient = c.recipient ?? '';
		formDeleteAfterRun = c.deleteAfterRun;
	}

	function closeEdit() {
		editId = null;
	}

	async function saveEdit() {
		if (!editId) return;
		editError = null;
		const payload = buildPayload();
		if ('error' in payload) {
			editError = payload.error;
			return;
		}
		delete payload.workspace_id;
		editSaving = true;
		try {
			const res = await fetch(`/api/crons/${editId}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});
			if (!res.ok) {
				editError = (await res.text()) || 'Failed to update';
				return;
			}
			editId = null;
			await invalidateAll();
		} catch (e) {
			editError = e instanceof Error ? e.message : 'Failed to update';
		} finally {
			editSaving = false;
		}
	}

	async function confirmDelete() {
		if (!deleteId) return;
		deleting = true;
		deleteError = null;
		try {
			const res = await fetch(`/api/crons/${deleteId}`, { method: 'DELETE' });
			if (!res.ok && res.status !== 204) {
				deleteError = (await res.text()) || 'Failed to delete';
				return;
			}
			deleteId = null;
			await invalidateAll();
		} catch (e) {
			deleteError = e instanceof Error ? e.message : 'Failed to delete';
		} finally {
			deleting = false;
		}
	}

	function scheduleSummary(c: CronRecord): string {
		if (c.scheduleKind === 'cron') return `cron • ${c.scheduleExpr ?? ''}${c.scheduleTz ? ` (${c.scheduleTz})` : ''}`;
		if (c.scheduleKind === 'every' && c.scheduleEveryMs) {
			const min = Math.round(c.scheduleEveryMs / 60_000);
			if (min < 60) return `every ${min}m`;
			const h = Math.round(min / 60);
			if (h < 24) return `every ${h}h`;
			return `every ${Math.round(h / 24)}d`;
		}
		if (c.scheduleKind === 'at' && c.scheduleAtMs) {
			return `at ${new Date(c.scheduleAtMs).toLocaleString()}`;
		}
		return c.scheduleKind;
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
		<div class="crumb font-mono">workspace / cron</div>
		<h1 class="title font-display">Cron Jobs</h1>
		<p class="tag">scheduled prompts — attach jobs to agents to run periodically or at a specific time.</p>
	</header>

	<div class="body">
		{#if addOpen || editId}
			<div class="form-card">
				<div class="form-header">
					<span class="form-type font-mono">{editId ? '✎ edit' : '＋ new'} cron job</span>
				</div>

				<div class="field">
					<label class="field-label font-mono" for="cron-name">Name</label>
					<input id="cron-name" class="field-input font-mono" type="text" bind:value={formName} placeholder="daily-digest" spellcheck="false" />
				</div>

				<div class="field">
					<span class="field-label font-mono">Schedule</span>
					<div class="type-grid">
						<button class="type-btn" class:type-btn--on={formKind === 'every'} type="button" onclick={() => (formKind = 'every')}>
							<span class="type-icon font-mono">⟳</span>
							<div class="type-info">
								<span class="type-name font-mono">every</span>
								<span class="type-desc font-mono">fixed interval</span>
							</div>
						</button>
						<button class="type-btn" class:type-btn--on={formKind === 'cron'} type="button" onclick={() => (formKind = 'cron')}>
							<span class="type-icon font-mono">✱</span>
							<div class="type-info">
								<span class="type-name font-mono">cron</span>
								<span class="type-desc font-mono">crontab expression</span>
							</div>
						</button>
						<button class="type-btn" class:type-btn--on={formKind === 'at'} type="button" onclick={() => (formKind = 'at')}>
							<span class="type-icon font-mono">⏱</span>
							<div class="type-info">
								<span class="type-name font-mono">at</span>
								<span class="type-desc font-mono">one-shot timestamp</span>
							</div>
						</button>
					</div>
				</div>

				{#if formKind === 'every'}
					<div class="field">
						<label class="field-label font-mono" for="cron-every">Interval (minutes)</label>
						<input id="cron-every" class="field-input font-mono" type="number" min="1" step="1" bind:value={formEveryMin} />
					</div>
				{:else if formKind === 'cron'}
					<div class="field">
						<label class="field-label font-mono" for="cron-expr">Crontab expression</label>
						<input id="cron-expr" class="field-input font-mono" type="text" bind:value={formCronExpr} placeholder="0 9 * * *" spellcheck="false" />
						<p class="field-hint font-mono">Standard 5-field crontab. Example: <code>0 9 * * *</code> = daily at 09:00.</p>
					</div>
					<div class="field">
						<label class="field-label font-mono" for="cron-tz">Timezone (IANA)</label>
						<input id="cron-tz" class="field-input font-mono" type="text" bind:value={formTz} placeholder="Europe/Berlin" spellcheck="false" />
					</div>
				{:else}
					<div class="field">
						<label class="field-label font-mono" for="cron-at">Run at</label>
						<input id="cron-at" class="field-input font-mono" type="datetime-local" bind:value={formAtDate} />
					</div>
				{/if}

				<div class="field">
					<label class="field-label font-mono" for="cron-msg">Message <span class="field-opt">(what the agent receives)</span></label>
					<textarea id="cron-msg" class="field-textarea font-mono" bind:value={formMessage} rows={3} spellcheck="false" placeholder="Summarise unread messages and email a brief."></textarea>
				</div>

				<div class="field field--row">
					<label class="toggle-inline">
						<input type="checkbox" bind:checked={formDeliver} />
						<span class="toggle-inline-label font-mono">deliver result to channel</span>
					</label>
					<label class="toggle-inline">
						<input type="checkbox" bind:checked={formDeleteAfterRun} />
						<span class="toggle-inline-label font-mono">delete after run (one-shot only)</span>
					</label>
				</div>

				{#if formDeliver}
					<div class="field">
						<label class="field-label font-mono" for="cron-channel">Channel</label>
						<input id="cron-channel" class="field-input font-mono" type="text" bind:value={formChannel} placeholder="telegram" spellcheck="false" />
					</div>
					<div class="field">
						<label class="field-label font-mono" for="cron-to">Recipient</label>
						<input id="cron-to" class="field-input font-mono" type="text" bind:value={formRecipient} placeholder="chat-id or user handle" spellcheck="false" />
					</div>
				{/if}

				{#if editId && editError}<p class="form-error font-mono">{editError}</p>{/if}
				{#if !editId && saveError}<p class="form-error font-mono">{saveError}</p>{/if}

				<div class="form-actions">
					{#if editId}
						<button class="btn-primary font-mono" type="button" onclick={saveEdit} disabled={editSaving}>
							{#if editSaving}<span class="spinner"></span>saving…{:else}Save changes{/if}
						</button>
						<button class="btn-ghost font-mono" type="button" onclick={closeEdit}>Cancel</button>
					{:else}
						<button class="btn-primary font-mono" type="button" onclick={saveCron} disabled={saving}>
							{#if saving}<span class="spinner"></span>saving…{:else}Add cron{/if}
						</button>
						<button class="btn-ghost font-mono" type="button" onclick={closeAdd}>Cancel</button>
					{/if}
				</div>
			</div>
		{/if}

		<div class="list-head">
			<span class="list-count font-mono">{crons.length} job{crons.length !== 1 ? 's' : ''}</span>
			{#if !addOpen && !editId}
				<button class="btn-add font-mono" type="button" onclick={openAdd}>
					<Icon icon="oc:spawn" width={11} height={11} />
					Add cron
				</button>
			{/if}
		</div>

		{#if crons.length === 0}
			<div class="empty-state">
				<div class="empty-icon">
					<Icon icon="tabler:clock" width={22} height={22} />
				</div>
				<p class="empty-title">No cron jobs yet</p>
				<p class="empty-sub">Define scheduled prompts and attach them to agents.</p>
			</div>
		{:else}
			<div class="cron-list">
				{#each crons as c (c.id)}
					<div class="cron-item" class:cron-deleting={deleteId === c.id}>
						<div class="cron-row">
							<Icon icon="tabler:clock" width={14} height={14} class="cron-icon" />
							<span class="cron-name font-mono">{c.name}</span>
							<span class="cron-schedule font-mono">{scheduleSummary(c)}</span>
							<span class="cron-date font-mono">{relDate(c.updatedAt)}</span>
							<button
								class="cron-edit font-mono"
								type="button"
								onclick={() => { if (editId === c.id) closeEdit(); else openEdit(c); deleteId = null; }}
							>edit</button>
							<button
								class="cron-del font-mono"
								type="button"
								onclick={() => { deleteId = deleteId === c.id ? null : c.id; deleteError = null; editId = null; addOpen = false; }}
							>delete</button>
						</div>

						{#if deleteId === c.id}
							<div class="danger-panel">
								<p class="delete-msg font-mono">
									Remove <strong>{c.name}</strong>? Attached agents will lose this job.
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

	.list-head {
		display: flex; align-items: center; justify-content: space-between;
		padding-bottom: 0.75rem; border-bottom: 1px solid var(--border);
	}
	.list-count {
		font-size: 0.62rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: color-mix(in oklch, var(--foreground) 40%, transparent);
	}
	.btn-add {
		display: flex; align-items: center; gap: 0.4rem;
		font-size: 0.68rem; letter-spacing: 0.04em;
		color: var(--primary); padding: 0.3rem 0.6rem; border-radius: 0.25rem;
		transition: background 150ms ease;
	}
	.btn-add:hover { background: color-mix(in oklch, var(--primary) 10%, transparent); }

	.form-card {
		background: var(--card); border: 1px solid var(--border); border-radius: 0.4rem;
		padding: 1.5rem; display: flex; flex-direction: column; gap: 1.25rem; position: relative;
	}
	.form-card::before {
		content: ''; position: absolute; top: -1px; left: 1.5rem; right: 1.5rem;
		height: 2px; background: var(--primary); opacity: 0.55; border-radius: 0 0 2px 2px;
	}
	.form-header { display: flex; align-items: center; gap: 0.6rem; }
	.form-type { font-size: 0.72rem; letter-spacing: 0.08em; color: var(--primary); opacity: 0.9; }

	.type-grid { display: flex; gap: 0.55rem; flex-wrap: wrap; }
	.type-btn {
		display: flex; align-items: center; gap: 0.75rem;
		padding: 0.65rem 1rem;
		border: 1px solid var(--border); border-radius: 0.35rem;
		background: var(--background); cursor: pointer;
		transition: border-color 150ms ease, background 150ms ease;
		min-width: 160px;
	}
	.type-btn:hover { border-color: var(--primary); background: color-mix(in oklch, var(--primary) 5%, var(--background)); }
	.type-btn--on { border-color: var(--primary); background: color-mix(in oklch, var(--primary) 10%, var(--background)); }
	.type-icon { font-size: 1rem; color: var(--primary); opacity: 0.8; flex-shrink: 0; width: 18px; text-align: center; }
	.type-info { display: flex; flex-direction: column; gap: 0.15rem; text-align: left; }
	.type-name { font-size: 0.72rem; letter-spacing: 0.04em; color: var(--foreground); }
	.type-desc { font-size: 0.6rem; color: var(--muted-foreground); letter-spacing: 0.02em; }

	.field { display: flex; flex-direction: column; gap: 0.4rem; }
	.field--row { flex-direction: row; gap: 1.2rem; flex-wrap: wrap; }
	.field-label {
		font-size: 0.62rem; letter-spacing: 0.12em; text-transform: uppercase;
		color: color-mix(in oklch, var(--foreground) 60%, transparent);
	}
	.field-opt { text-transform: none; letter-spacing: 0; opacity: 0.65; }
	.field-input, .field-textarea {
		padding: 0.42rem 0.65rem;
		background: var(--background);
		border: 1px solid color-mix(in oklch, var(--border) 80%, transparent);
		border-radius: 0.2rem;
		font-size: 0.75rem; color: var(--foreground); letter-spacing: 0.02em;
		transition: border-color 120ms ease;
	}
	.field-textarea { resize: vertical; }
	.field-input:focus, .field-textarea:focus {
		border-color: color-mix(in oklch, var(--primary) 50%, var(--border)); outline: none;
	}
	.field-hint { font-size: 0.62rem; color: var(--muted-foreground); letter-spacing: 0.01em; line-height: 1.5; }
	.field-hint code { font-family: var(--font-mono); background: var(--muted); padding: 0.04rem 0.25rem; border-radius: 0.15rem; }

	.toggle-inline { display: flex; align-items: center; gap: 0.4rem; cursor: pointer; }
	.toggle-inline input { accent-color: var(--primary); }
	.toggle-inline-label { font-size: 0.65rem; color: var(--muted-foreground); letter-spacing: 0.02em; }

	.form-error { color: var(--destructive); font-size: 0.66rem; letter-spacing: 0.02em; }

	.form-actions { display: flex; gap: 0.6rem; }
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
	.btn-danger:hover:not(:disabled) { background: color-mix(in oklch, var(--destructive) 18%, transparent); }
	.btn-danger:disabled { opacity: 0.6; cursor: not-allowed; }

	.spinner { width: 10px; height: 10px; border: 1.5px solid currentColor; border-right-color: transparent; border-radius: 50%; animation: spin 0.6s linear infinite; }
	.spinner--danger { border-color: var(--destructive); border-right-color: transparent; }
	@keyframes spin { to { transform: rotate(360deg); } }

	.cron-list { display: flex; flex-direction: column; }
	.cron-item {
		border-bottom: 1px solid color-mix(in oklch, var(--border) 70%, transparent);
		transition: background 150ms ease;
	}
	.cron-item:first-child { border-top: 1px solid color-mix(in oklch, var(--border) 70%, transparent); }
	.cron-item.cron-deleting { background: color-mix(in oklch, var(--card) 60%, transparent); }
	.cron-row { display: flex; align-items: center; gap: 0.85rem; padding: 0.85rem 0; }

	.cron-name { flex: 0 0 auto; font-size: 0.82rem; letter-spacing: 0.04em; color: var(--foreground); }
	.cron-schedule {
		flex: 1; font-size: 0.68rem;
		color: color-mix(in oklch, var(--muted-foreground) 80%, transparent);
		letter-spacing: 0.02em;
	}
	.cron-date { font-size: 0.65rem; letter-spacing: 0.02em; color: var(--muted-foreground); flex-shrink: 0; }
	.cron-edit, .cron-del {
		font-size: 0.65rem; letter-spacing: 0.06em;
		padding: 0.28rem 0.65rem; border-radius: 0.2rem;
		color: var(--muted-foreground); flex-shrink: 0;
		transition: color 150ms ease, background 150ms ease;
	}
	.cron-edit:hover { color: var(--primary); background: color-mix(in oklch, var(--primary) 8%, transparent); }
	.cron-del:hover { color: var(--destructive); background: color-mix(in oklch, var(--destructive) 8%, transparent); }

	.danger-panel { padding: 0.5rem 0 1rem 1.75rem; display: flex; flex-direction: column; gap: 0.9rem; }
	.delete-msg { font-size: 0.72rem; color: var(--foreground); letter-spacing: 0.02em; }

	.empty-state {
		padding: 4rem 2rem;
		display: flex; flex-direction: column; align-items: center; gap: 0.75rem;
		text-align: center; color: var(--muted-foreground);
	}
	.empty-icon {
		display: flex; align-items: center; justify-content: center;
		width: 52px; height: 52px; border-radius: 0.4rem;
		background: var(--muted); color: var(--muted-foreground);
	}
	.empty-title { font-size: 0.95rem; color: var(--foreground); font-weight: 500; }
	.empty-sub { font-size: 0.82rem; max-width: 30rem; }
</style>
