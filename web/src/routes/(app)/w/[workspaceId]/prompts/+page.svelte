<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { Icon } from '$lib/icons';

	let { data } = $props();

	type Template = {
		id: string;
		name: string;
		templateType: string;
		content: string;
		createdAt: Date;
		updatedAt: Date;
	};

	const TYPES = ['soul', 'agents', 'heartbeat', 'tools'] as const;
	type TemplateType = (typeof TYPES)[number];

	const TYPE_META: Record<TemplateType, { label: string; hint: string }> = {
		soul:      { label: 'soul',      hint: 'Identity, personality, persistent goals' },
		agents:    { label: 'agents',    hint: 'Sub-agents the agent can spawn' },
		heartbeat: { label: 'heartbeat', hint: 'Scheduled / recurring tasks' },
		tools:     { label: 'tools',     hint: 'Tool configuration and guidance' }
	};

	// ── Create form ──────────────────────────────────────────────
	let creating = $state(false);
	let newName = $state('');
	let newType = $state<TemplateType>('soul');
	let newContent = $state('');
	let createError: string | null = $state(null);
	let createSaving = $state(false);

	function openCreate() {
		creating = true;
		newName = '';
		newType = 'soul';
		newContent = '';
		createError = null;
	}

	function cancelCreate() {
		creating = false;
	}

	async function submitCreate() {
		if (!newName.trim() || createSaving) return;
		createSaving = true;
		createError = null;
		try {
			const res = await fetch('/api/templates', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ name: newName.trim(), template_type: newType, content: newContent, workspace_id: data.workspace.id })
			});
			if (!res.ok) { createError = await res.text(); return; }
			creating = false;
			await invalidateAll();
		} catch (e) {
			createError = e instanceof Error ? e.message : 'Failed to create';
		} finally {
			createSaving = false;
		}
	}

	// ── Edit state ───────────────────────────────────────────────
	let expandedId: string | null = $state(null);
	let editContent: Record<string, string> = $state({});
	let editSaving: Record<string, boolean> = $state({});
	let editError: Record<string, string | null> = $state({});

	function toggleExpand(t: Template) {
		if (expandedId === t.id) {
			expandedId = null;
		} else {
			expandedId = t.id;
			if (!(t.id in editContent)) {
				editContent = { ...editContent, [t.id]: t.content };
			}
		}
	}

	function isDirty(t: Template) {
		return editContent[t.id] !== undefined && editContent[t.id] !== t.content;
	}

	async function saveTemplate(t: Template) {
		if (editSaving[t.id]) return;
		editSaving = { ...editSaving, [t.id]: true };
		editError = { ...editError, [t.id]: null };
		try {
			const res = await fetch(`/api/templates/${t.id}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ content: editContent[t.id] })
			});
			if (!res.ok) { editError = { ...editError, [t.id]: await res.text() }; return; }
			await invalidateAll();
		} catch (e) {
			editError = { ...editError, [t.id]: e instanceof Error ? e.message : 'Failed' };
		} finally {
			editSaving = { ...editSaving, [t.id]: false };
		}
	}

	async function deleteTemplate(t: Template) {
		if (!confirm(`Delete "${t.name}"?`)) return;
		const res = await fetch(`/api/templates/${t.id}`, { method: 'DELETE' });
		if (res.ok || res.status === 204) {
			if (expandedId === t.id) expandedId = null;
			await invalidateAll();
		}
	}

	const templates = $derived(data.templates as Template[]);
</script>

<div class="shell">
	<header class="page-head">
		<div class="crumb font-mono">workspace / prompts</div>
		<div class="head-row">
			<div>
				<h1 class="page-title font-display">Prompts</h1>
				<p class="page-sub">Typed instruction templates for your agents. Attach one per type in agent settings.</p>
			</div>
			<button class="btn-new" onclick={openCreate}>
				<Icon icon="tabler:plus" width={13} height={13} />
				New template
			</button>
		</div>
	</header>

	<div class="body">
		<!-- Create form -->
		{#if creating}
			<div class="create-card">
				<div class="create-row">
					<input
						class="create-name font-mono"
						placeholder="template name…"
						bind:value={newName}
						maxlength={80}
						autofocus
					/>
					<select class="create-type font-mono" bind:value={newType}>
						{#each TYPES as t}
							<option value={t}>{t}</option>
						{/each}
					</select>
					<button class="btn-cancel font-mono" onclick={cancelCreate}>cancel</button>
				</div>
				<p class="create-hint font-mono">{TYPE_META[newType].hint}</p>
				<textarea
					class="create-textarea"
					placeholder="Write the template content…"
					bind:value={newContent}
					rows={6}
				></textarea>
				{#if createError}
					<p class="create-error font-mono">{createError}</p>
				{/if}
				<div class="create-foot">
					<button class="btn-save" onclick={submitCreate} disabled={!newName.trim() || createSaving}>
						{#if createSaving}<span class="spinner"></span>saving…{:else}Create{/if}
					</button>
				</div>
			</div>
		{/if}

		<!-- Type groups -->
		{#each TYPES as type}
			{@const group = templates.filter((t) => t.templateType === type)}
			{#if group.length > 0}
				<div class="type-group">
					<div class="type-group-head">
						<span class="type-badge type-badge--{type} font-mono">{type}</span>
						<span class="type-group-hint font-mono">{TYPE_META[type].hint}</span>
					</div>

					{#each group as tpl (tpl.id)}
						<div class="tpl-card" class:expanded={expandedId === tpl.id}>
							<button class="tpl-header" onclick={() => toggleExpand(tpl)}>
								<span class="tpl-name">{tpl.name}</span>
								<span class="tpl-preview font-mono">
									{tpl.content ? tpl.content.slice(0, 60).replace(/\n/g, ' ') + (tpl.content.length > 60 ? '…' : '') : '(empty)'}
								</span>
								<Icon
									icon={expandedId === tpl.id ? 'tabler:chevron-up' : 'tabler:chevron-down'}
									width={13} height={13}
									class="tpl-chevron"
								/>
							</button>

							{#if expandedId === tpl.id}
								<div class="tpl-body">
									<textarea
										class="tpl-textarea"
										value={editContent[tpl.id] ?? tpl.content}
										oninput={(e) => {
											editContent = { ...editContent, [tpl.id]: (e.currentTarget as HTMLTextAreaElement).value };
										}}
										rows={10}
									></textarea>
									{#if editError[tpl.id]}
										<p class="tpl-error font-mono">{editError[tpl.id]}</p>
									{/if}
									<div class="tpl-foot">
										<button
											class="btn-save"
											onclick={() => saveTemplate(tpl)}
											disabled={!isDirty(tpl) || editSaving[tpl.id]}
										>
											{#if editSaving[tpl.id]}<span class="spinner"></span>saving…{:else}Save{/if}
										</button>
										<button class="btn-delete font-mono" onclick={() => deleteTemplate(tpl)}>
											<Icon icon="tabler:trash" width={12} height={12} />
											delete
										</button>
									</div>
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		{/each}

		{#if templates.length === 0 && !creating}
			<div class="empty">
				<p class="empty-title font-display">No templates yet</p>
				<p class="empty-sub">Create a template to share base instructions across agents.</p>
				<button class="btn-new" onclick={openCreate}>
					<Icon icon="tabler:plus" width={13} height={13} />
					New template
				</button>
			</div>
		{/if}
	</div>
</div>

<style>
	.shell { flex: 1; display: flex; flex-direction: column; overflow-y: auto; }

	.page-head {
		padding: 1.75rem 3rem 1.5rem;
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

	.head-row {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		gap: 1rem;
	}

	.page-title {
		font-size: 2.5rem;
		line-height: 1;
		font-style: italic;
		letter-spacing: -0.015em;
	}

	.page-sub {
		margin-top: 0.65rem;
		color: var(--muted-foreground);
		font-size: 0.88rem;
	}

	.body {
		flex: 1;
		padding: 1.75rem 3rem;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
		max-width: 60rem;
	}

	/* ── Create card ─────────────────────────────────────────── */
	.create-card {
		border: 1px solid color-mix(in oklch, var(--primary) 30%, var(--border));
		border-radius: 0.5rem;
		padding: 1rem 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		background: color-mix(in oklch, var(--primary) 4%, var(--background));
		animation: slide-in 120ms ease;
	}

	@keyframes slide-in {
		from { opacity: 0; transform: translateY(-6px); }
		to   { opacity: 1; transform: translateY(0); }
	}

	.create-row {
		display: flex;
		gap: 0.5rem;
		align-items: center;
	}

	.create-name {
		flex: 1;
		background: transparent;
		border: none;
		outline: none;
		font-size: 0.85rem;
		color: var(--foreground);
	}

	.create-name::placeholder { color: color-mix(in oklch, var(--foreground) 30%, transparent); }

	.create-type {
		background: color-mix(in oklch, var(--muted) 50%, transparent);
		border: 1px solid var(--border);
		border-radius: 0.3rem;
		padding: 0.3rem 0.5rem;
		font-size: 0.72rem;
		color: var(--foreground);
		cursor: pointer;
	}

	.create-hint {
		font-size: 0.65rem;
		letter-spacing: 0.04em;
		color: color-mix(in oklch, var(--foreground) 35%, transparent);
	}

	.create-textarea, .tpl-textarea {
		width: 100%;
		background: color-mix(in oklch, var(--muted) 20%, transparent);
		border: 1px solid var(--border);
		border-radius: 0.35rem;
		padding: 0.75rem 0.9rem;
		font-size: 0.82rem;
		font-family: var(--font-mono);
		color: var(--foreground);
		resize: vertical;
		line-height: 1.6;
		transition: border-color 150ms ease;
	}

	.create-textarea:focus, .tpl-textarea:focus {
		outline: none;
		border-color: var(--primary);
	}

	.create-textarea::placeholder { color: color-mix(in oklch, var(--foreground) 28%, transparent); }

	.create-error, .tpl-error {
		font-size: 0.68rem;
		color: var(--destructive);
		letter-spacing: 0.02em;
	}

	.create-foot, .tpl-foot {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	/* ── Type group ──────────────────────────────────────────── */
	.type-group {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.type-group-head {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		padding-bottom: 0.5rem;
		border-bottom: 1px solid var(--border);
	}

	.type-group-hint {
		font-size: 0.62rem;
		letter-spacing: 0.04em;
		color: color-mix(in oklch, var(--foreground) 30%, transparent);
	}

	.type-badge {
		display: inline-block;
		padding: 0.15rem 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.6rem;
		letter-spacing: 0.08em;
		font-weight: 600;
		text-transform: uppercase;
	}

	.type-badge--soul {
		background: color-mix(in oklch, var(--primary) 16%, transparent);
		color: var(--primary);
	}

	.type-badge--agents {
		background: color-mix(in oklch, oklch(0.65 0.15 250) 16%, transparent);
		color: oklch(0.72 0.14 250);
	}

	.type-badge--heartbeat {
		background: color-mix(in oklch, oklch(0.65 0.15 148) 16%, transparent);
		color: oklch(0.72 0.14 148);
	}

	.type-badge--tools {
		background: color-mix(in oklch, var(--muted-foreground) 16%, transparent);
		color: var(--muted-foreground);
	}

	/* ── Template card ───────────────────────────────────────── */
	.tpl-card {
		border: 1px solid var(--border);
		border-radius: 0.4rem;
		overflow: hidden;
		transition: border-color 150ms ease;
	}

	.tpl-card.expanded {
		border-color: color-mix(in oklch, var(--primary) 35%, var(--border));
	}

	.tpl-header {
		width: 100%;
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.7rem 1rem;
		text-align: left;
		transition: background 150ms ease;
	}

	.tpl-header:hover { background: color-mix(in oklch, var(--muted) 30%, transparent); }

	.tpl-name {
		font-size: 0.85rem;
		font-weight: 500;
		color: var(--foreground);
		min-width: 10rem;
		flex-shrink: 0;
	}

	.tpl-preview {
		flex: 1;
		font-size: 0.7rem;
		color: color-mix(in oklch, var(--foreground) 38%, transparent);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		letter-spacing: 0.01em;
	}

	:global(.tpl-chevron) {
		color: color-mix(in oklch, var(--foreground) 35%, transparent);
		flex-shrink: 0;
	}

	.tpl-body {
		border-top: 1px solid var(--border);
		padding: 1rem;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		background: color-mix(in oklch, var(--muted) 10%, transparent);
		animation: slide-in 100ms ease;
	}

	/* ── Buttons ─────────────────────────────────────────────── */
	.btn-new {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.45rem 0.9rem;
		background: var(--primary);
		color: var(--primary-foreground);
		border-radius: 0.35rem;
		font-size: 0.78rem;
		font-weight: 500;
		flex-shrink: 0;
		transition: opacity 150ms ease;
	}

	.btn-new:hover { opacity: 0.88; }

	.btn-save {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.4rem 0.9rem;
		background: var(--primary);
		color: var(--primary-foreground);
		border-radius: 0.3rem;
		font-size: 0.75rem;
		font-weight: 500;
		transition: opacity 150ms ease;
	}

	.btn-save:disabled { opacity: 0.35; cursor: not-allowed; }

	.btn-cancel {
		font-size: 0.68rem;
		letter-spacing: 0.04em;
		color: color-mix(in oklch, var(--foreground) 40%, transparent);
		transition: color 150ms ease;
	}

	.btn-cancel:hover { color: var(--foreground); }

	.btn-delete {
		display: flex;
		align-items: center;
		gap: 0.3rem;
		font-size: 0.68rem;
		letter-spacing: 0.04em;
		color: color-mix(in oklch, var(--destructive) 70%, transparent);
		transition: color 150ms ease;
	}

	.btn-delete:hover { color: var(--destructive); }

	/* ── Empty state ─────────────────────────────────────────── */
	.empty {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.85rem;
		text-align: center;
		padding: 4rem;
	}

	.empty-title { font-size: 1.75rem; line-height: 1.1; font-style: italic; }
	.empty-sub { font-size: 0.88rem; color: var(--muted-foreground); max-width: 28rem; }

	/* ── Spinner ─────────────────────────────────────────────── */
	.spinner {
		display: inline-block;
		width: 10px;
		height: 10px;
		border-radius: 9999px;
		border: 1.5px solid currentColor;
		border-right-color: transparent;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin { to { transform: rotate(360deg); } }
</style>
