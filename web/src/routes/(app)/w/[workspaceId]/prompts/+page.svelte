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

	const TYPE_META: Record<TemplateType, { label: string; hint: string; description: string }> = {
		soul: {
			label: 'soul',
			hint: 'Identity, personality, persistent goals',
			description: "Defines who the agent is — its name, purpose, voice, and the goals it carries between sessions."
		},
		agents: {
			label: 'agents',
			hint: 'Sub-agents the agent can spawn',
			description: 'Catalogues the sub-agents this agent can spawn and how to delegate work to them.'
		},
		heartbeat: {
			label: 'heartbeat',
			hint: 'Scheduled / recurring tasks',
			description: 'Recurring tasks the agent runs on a schedule — checkins, reports, polling jobs.'
		},
		tools: {
			label: 'tools',
			hint: 'Tool configuration and guidance',
			description: 'How the agent should think about its tools — when to use which, edge cases, and traps.'
		}
	};

	const templates = $derived(data.templates as Template[]);

	// ── Selection / draft state ──────────────────────────────────
	let selectedId: string | null = $state(null);
	let drafting = $state(false);

	const selectedTemplate = $derived(
		selectedId ? (templates.find((t) => t.id === selectedId) ?? null) : null
	);

	// Edit buffers, keyed per template
	let editContent: Record<string, string> = $state({});
	let editName: Record<string, string> = $state({});
	let editSaving: Record<string, boolean> = $state({});
	let editError: Record<string, string | null> = $state({});

	function selectTemplate(t: Template) {
		drafting = false;
		selectedId = t.id;
		if (!(t.id in editContent)) {
			editContent = { ...editContent, [t.id]: t.content };
			editName = { ...editName, [t.id]: t.name };
		}
	}

	function isDirty(t: Template) {
		const c = editContent[t.id];
		const n = editName[t.id];
		return (c !== undefined && c !== t.content) || (n !== undefined && n.trim() !== t.name);
	}

	async function saveTemplate(t: Template) {
		if (editSaving[t.id]) return;
		editSaving = { ...editSaving, [t.id]: true };
		editError = { ...editError, [t.id]: null };
		try {
			const body: Record<string, string> = {};
			if (editContent[t.id] !== undefined && editContent[t.id] !== t.content)
				body.content = editContent[t.id];
			if (editName[t.id] !== undefined && editName[t.id].trim() !== t.name)
				body.name = editName[t.id].trim();

			const res = await fetch(`/api/templates/${t.id}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body)
			});
			if (!res.ok) {
				editError = { ...editError, [t.id]: await res.text() };
				return;
			}
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
			if (selectedId === t.id) selectedId = null;
			await invalidateAll();
		}
	}

	// ── Draft (create) state ─────────────────────────────────────
	let draftName = $state('');
	let draftType = $state<TemplateType>('soul');
	let draftContent = $state('');
	let draftError: string | null = $state(null);
	let draftSaving = $state(false);

	function openDraft(prefilledType: TemplateType = 'soul') {
		drafting = true;
		selectedId = null;
		draftName = '';
		draftType = prefilledType;
		draftContent = '';
		draftError = null;
	}

	function closeDraft() {
		drafting = false;
	}

	async function submitDraft() {
		if (!draftName.trim() || draftSaving) return;
		draftSaving = true;
		draftError = null;
		try {
			const res = await fetch('/api/templates', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					name: draftName.trim(),
					template_type: draftType,
					content: draftContent,
					workspace_id: data.workspace.id
				})
			});
			if (!res.ok) {
				draftError = await res.text();
				return;
			}
			const created = await res.json();
			drafting = false;
			await invalidateAll();
			selectedId = created.id ?? null;
		} catch (e) {
			draftError = e instanceof Error ? e.message : 'Failed to create';
		} finally {
			draftSaving = false;
		}
	}

	function focusOnMount(node: HTMLElement) {
		node.focus();
	}

	function fmtDate(d: Date | string | undefined): string {
		if (!d) return '';
		const date = typeof d === 'string' ? new Date(d) : d;
		return date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
	}
</script>

<div class="shell">
	<!-- ── Left rail: list ───────────────────────────────────── -->
	<aside class="rail">
		<header class="rail-head">
			<div class="rail-head-row">
				<div class="rail-titles">
					<div class="crumb font-mono">workspace</div>
					<h1 class="rail-title font-display">Prompts</h1>
				</div>
				<button
					class="rail-new"
					class:active={drafting}
					onclick={() => openDraft()}
					title="New template"
					aria-label="New template"
				>
					<Icon icon="tabler:plus" width={13} height={13} />
				</button>
			</div>
			<p class="rail-sub">Typed instruction templates. Attach one per type in agent settings.</p>
		</header>

		<div class="rail-scroll">
			{#each TYPES as type}
				{@const group = templates.filter((t) => t.templateType === type)}
				<section class="rail-group">
					<header class="rail-group-head">
						<span class="rail-group-label font-mono type-{type}">{type}</span>
						<span class="rail-group-count font-mono">{group.length}</span>
						<button
							class="rail-group-add"
							onclick={() => openDraft(type)}
							title={`New ${type} template`}
							aria-label={`New ${type} template`}
						>
							<Icon icon="tabler:plus" width={10} height={10} />
						</button>
					</header>

					{#if group.length === 0}
						<button class="rail-group-empty font-mono" onclick={() => openDraft(type)}>
							{TYPE_META[type].hint}
						</button>
					{:else}
						<ul class="rail-list">
							{#each group as tpl (tpl.id)}
								<li>
									<button
										class="rail-item type-{type}"
										class:active={selectedId === tpl.id}
										onclick={() => selectTemplate(tpl)}
									>
										<span class="rail-item-mark"></span>
										<span class="rail-item-name">{tpl.name}</span>
										{#if isDirty(tpl)}
											<span class="rail-item-dirty" aria-label="unsaved"></span>
										{/if}
									</button>
								</li>
							{/each}
						</ul>
					{/if}
				</section>
			{/each}
		</div>
	</aside>

	<!-- ── Right pane: editor ────────────────────────────────── -->
	<main class="pane">
		{#if drafting}
			<!-- ── Draft form ─────────────────────────────────── -->
			<div class="editor draft" data-type={draftType}>
				<header class="editor-head">
					<div class="editor-head-left">
						<div class="editor-eyebrow font-mono">new template</div>
						<input
							class="editor-name-input font-display"
							placeholder="untitled prompt"
							bind:value={draftName}
							maxlength={80}
							use:focusOnMount
						/>
					</div>
					<div class="editor-head-right">
						<div class="type-pills">
							{#each TYPES as t}
								<button
									type="button"
									class="type-pill type-pill-{t}"
									class:active={draftType === t}
									onclick={() => (draftType = t)}
								>
									{t}
								</button>
							{/each}
						</div>
					</div>
				</header>
				<p class="editor-hint font-mono">{TYPE_META[draftType].description}</p>

				<textarea
					class="editor-textarea"
					placeholder="Write the template content. Markdown supported."
					bind:value={draftContent}
				></textarea>

				{#if draftError}
					<p class="editor-error font-mono"><Icon icon="oc:error" width={11} height={11} />{draftError}</p>
				{/if}

				<footer class="editor-foot">
					<div class="editor-foot-left">
						<button class="btn-cancel font-mono" onclick={closeDraft}>cancel</button>
					</div>
					<div class="editor-foot-right">
						<button
							class="btn-primary"
							onclick={submitDraft}
							disabled={!draftName.trim() || draftSaving}
						>
							{#if draftSaving}<span class="spinner"></span>creating…{:else}<Icon icon="tabler:check" width={13} height={13} />Create template{/if}
						</button>
					</div>
				</footer>
			</div>
		{:else if selectedTemplate}
			{@const t = selectedTemplate}
			{@const ttype = t.templateType as TemplateType}
			<div class="editor" data-type={ttype}>
				<header class="editor-head">
					<div class="editor-head-left">
						<div class="editor-eyebrow font-mono">
							<span class="type-tag type-tag-{ttype}">{ttype}</span>
							<span class="sep">·</span>
							<span class="dim">edited {fmtDate(t.updatedAt)}</span>
						</div>
						<input
							class="editor-name-input font-display"
							value={editName[t.id] ?? t.name}
							oninput={(e) =>
								(editName = {
									...editName,
									[t.id]: (e.currentTarget as HTMLInputElement).value
								})}
							maxlength={80}
						/>
					</div>
				</header>
				<p class="editor-hint font-mono">{TYPE_META[ttype]?.description ?? ''}</p>

				<textarea
					class="editor-textarea"
					value={editContent[t.id] ?? t.content}
					oninput={(e) =>
						(editContent = {
							...editContent,
							[t.id]: (e.currentTarget as HTMLTextAreaElement).value
						})}
					placeholder="(empty)"
				></textarea>

				{#if editError[t.id]}
					<p class="editor-error font-mono"><Icon icon="oc:error" width={11} height={11} />{editError[t.id]}</p>
				{/if}

				<footer class="editor-foot">
					<div class="editor-foot-left">
						<button class="btn-delete font-mono" onclick={() => deleteTemplate(t)}>
							<Icon icon="tabler:trash" width={11} height={11} />
							delete
						</button>
					</div>
					<div class="editor-foot-right">
						<span class="dirty-hint font-mono" class:visible={isDirty(t)}>unsaved changes</span>
						<button
							class="btn-primary"
							onclick={() => saveTemplate(t)}
							disabled={!isDirty(t) || editSaving[t.id]}
						>
							{#if editSaving[t.id]}<span class="spinner"></span>saving…{:else}<Icon icon="tabler:check" width={13} height={13} />Save{/if}
						</button>
					</div>
				</footer>
			</div>
		{:else}
			<!-- ── Empty state ────────────────────────────────── -->
			<div class="empty">
				<div class="empty-eyebrow font-mono">no template selected</div>
				<h2 class="empty-title font-display">
					Pick a slot. <em>Shape</em> your agents.
				</h2>
				<p class="empty-sub">
					Templates plug into one of four slots on every agent. Pick a slot below to draft a new
					prompt, or select an existing one from the rail.
				</p>

				<div class="slot-grid">
					{#each TYPES as type}
						{@const count = templates.filter((t) => t.templateType === type).length}
						<button class="slot-card slot-{type}" onclick={() => openDraft(type)}>
							<div class="slot-card-head">
								<span class="slot-card-label font-mono">{type}</span>
								<span class="slot-card-count font-mono">{count}</span>
							</div>
							<p class="slot-card-desc">{TYPE_META[type].description}</p>
							<div class="slot-card-cta font-mono">
								<Icon icon="tabler:plus" width={11} height={11} />
								new {type}
							</div>
						</button>
					{/each}
				</div>
			</div>
		{/if}
	</main>
</div>

<style>
	/* ── Shell: fill viewport, two columns ───────────────────── */
	.shell {
		flex: 1;
		display: grid;
		grid-template-columns: 304px 1fr;
		min-height: 0;
		height: 100%;
		background: var(--background);
	}

	/* ── Rail ────────────────────────────────────────────────── */
	.rail {
		display: flex;
		flex-direction: column;
		min-height: 0;
		border-right: 1px solid var(--border);
		background: color-mix(in oklch, var(--card) 50%, var(--background));
	}

	.rail-head {
		flex-shrink: 0;
		padding: 1.4rem 1.1rem 1rem;
		border-bottom: 1px solid var(--border);
	}

	.rail-head-row {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		gap: 0.5rem;
	}

	.rail-titles {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.crumb {
		font-size: 0.58rem;
		letter-spacing: 0.18em;
		text-transform: uppercase;
		color: color-mix(in oklch, var(--foreground) 35%, transparent);
	}

	.rail-title {
		font-size: 1.5rem;
		line-height: 1;
		font-style: italic;
		letter-spacing: -0.015em;
	}

	.rail-sub {
		margin-top: 0.55rem;
		font-size: 0.72rem;
		line-height: 1.5;
		color: color-mix(in oklch, var(--foreground) 45%, transparent);
	}

	.rail-new {
		width: 26px;
		height: 26px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 0.3rem;
		color: var(--primary);
		background: color-mix(in oklch, var(--primary) 10%, transparent);
		border: 1px solid color-mix(in oklch, var(--primary) 24%, transparent);
		transition: background 150ms ease, transform 150ms ease;
	}
	.rail-new:hover {
		background: color-mix(in oklch, var(--primary) 18%, transparent);
		transform: rotate(90deg);
	}
	.rail-new.active {
		background: var(--primary);
		color: var(--primary-foreground);
		border-color: var(--primary);
	}

	.rail-scroll {
		flex: 1;
		overflow-y: auto;
		padding: 0.6rem 0;
	}

	.rail-group {
		padding: 0.4rem 0 0.7rem;
	}

	.rail-group-head {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.3rem 1.1rem 0.45rem;
	}

	.rail-group-label {
		font-size: 0.6rem;
		letter-spacing: 0.18em;
		text-transform: uppercase;
		font-weight: 600;
	}

	.rail-group-count {
		margin-left: auto;
		font-size: 0.6rem;
		color: color-mix(in oklch, var(--foreground) 35%, transparent);
		letter-spacing: 0.06em;
	}

	.rail-group-add {
		width: 18px;
		height: 18px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 3px;
		opacity: 0;
		color: color-mix(in oklch, var(--foreground) 40%, transparent);
		transition: opacity 120ms ease, color 120ms ease, background 120ms ease;
	}
	.rail-group:hover .rail-group-add {
		opacity: 1;
	}
	.rail-group-add:hover {
		color: var(--primary);
		background: color-mix(in oklch, var(--primary) 14%, transparent);
	}

	.rail-group-empty {
		display: block;
		width: calc(100% - 1.1rem);
		margin: 0 0.55rem;
		padding: 0.5rem 0.7rem;
		text-align: left;
		font-size: 0.65rem;
		line-height: 1.45;
		color: color-mix(in oklch, var(--foreground) 38%, transparent);
		border: 1px dashed color-mix(in oklch, var(--border) 80%, transparent);
		border-radius: 0.35rem;
		transition: border-color 150ms ease, color 150ms ease, background 150ms ease;
	}
	.rail-group-empty:hover {
		color: var(--primary);
		border-color: color-mix(in oklch, var(--primary) 32%, transparent);
		background: color-mix(in oklch, var(--primary) 5%, transparent);
	}

	.rail-list {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.rail-item {
		position: relative;
		width: calc(100% - 0.5rem);
		margin: 0.05rem 0.25rem;
		padding: 0.45rem 0.6rem 0.45rem 0.95rem;
		display: flex;
		align-items: center;
		gap: 0.45rem;
		text-align: left;
		border-radius: 0.3rem;
		font-size: 0.78rem;
		color: var(--foreground);
		background: transparent;
		transition: background 150ms ease, color 150ms ease;
	}
	.rail-item:hover {
		background: color-mix(in oklch, var(--muted) 50%, transparent);
	}
	.rail-item.active {
		background: color-mix(in oklch, var(--primary) 8%, var(--muted));
		color: var(--foreground);
	}

	.rail-item-mark {
		position: absolute;
		left: 0.3rem;
		top: 50%;
		transform: translateY(-50%);
		width: 4px;
		height: 14px;
		border-radius: 2px;
		background: transparent;
		transition: background 200ms ease;
	}
	.rail-item.active .rail-item-mark {
		background: var(--type-color);
	}

	.rail-item-name {
		flex: 1;
		min-width: 0;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.rail-item-dirty {
		flex-shrink: 0;
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--primary);
		box-shadow: 0 0 6px color-mix(in oklch, var(--primary) 50%, transparent);
	}

	/* ── Type accent colors ──────────────────────────────────── */
	.type-soul,
	.type-pill-soul,
	.type-tag-soul,
	.slot-soul {
		--type-color: var(--primary);
	}
	.type-agents,
	.type-pill-agents,
	.type-tag-agents,
	.slot-agents {
		--type-color: oklch(0.72 0.14 250);
	}
	.type-heartbeat,
	.type-pill-heartbeat,
	.type-tag-heartbeat,
	.slot-heartbeat {
		--type-color: oklch(0.72 0.14 148);
	}
	.type-tools,
	.type-pill-tools,
	.type-tag-tools,
	.slot-tools {
		--type-color: oklch(0.72 0.04 75);
	}

	.rail-group-label,
	.rail-item-name {
		color: inherit;
	}
	.rail-group-label.type-soul,
	.rail-group-label.type-agents,
	.rail-group-label.type-heartbeat,
	.rail-group-label.type-tools {
		color: var(--type-color);
	}

	/* ── Pane ────────────────────────────────────────────────── */
	.pane {
		position: relative;
		display: flex;
		flex-direction: column;
		min-height: 0;
		min-width: 0;
		overflow: hidden;
	}

	/* ── Editor ──────────────────────────────────────────────── */
	.editor {
		flex: 1;
		display: flex;
		flex-direction: column;
		min-height: 0;
		padding: 1.5rem 2.25rem 1.25rem;
		gap: 0.85rem;

		/* Subtle accent strip on the left edge of the editor */
		background:
			linear-gradient(to right, color-mix(in oklch, var(--type-color, var(--primary)) 5%, transparent) 0, transparent 12rem),
			var(--background);
	}

	.editor[data-type='soul'] {
		--type-color: var(--primary);
	}
	.editor[data-type='agents'] {
		--type-color: oklch(0.72 0.14 250);
	}
	.editor[data-type='heartbeat'] {
		--type-color: oklch(0.72 0.14 148);
	}
	.editor[data-type='tools'] {
		--type-color: oklch(0.72 0.04 75);
	}

	.editor-head {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 1.5rem;
		padding-bottom: 0.4rem;
	}

	.editor-head-left {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}

	.editor-eyebrow {
		font-size: 0.62rem;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: color-mix(in oklch, var(--foreground) 40%, transparent);
		display: flex;
		align-items: center;
		gap: 0.45rem;
	}

	.editor-eyebrow .sep {
		opacity: 0.4;
	}
	.editor-eyebrow .dim {
		color: color-mix(in oklch, var(--foreground) 35%, transparent);
		text-transform: none;
		letter-spacing: 0.02em;
	}

	.type-tag {
		display: inline-flex;
		align-items: center;
		padding: 0.1rem 0.45rem;
		border-radius: 0.2rem;
		font-size: 0.6rem;
		letter-spacing: 0.12em;
		font-weight: 600;
		background: color-mix(in oklch, var(--type-color) 14%, transparent);
		color: var(--type-color);
	}

	.editor-name-input {
		width: 100%;
		background: transparent;
		border: none;
		outline: none;
		font-size: 2rem;
		font-style: italic;
		font-variation-settings:
			'opsz' 36,
			'wght' 680;
		line-height: 1.05;
		letter-spacing: -0.015em;
		color: var(--foreground);
		padding: 0;
	}
	.editor-name-input::placeholder {
		color: color-mix(in oklch, var(--foreground) 28%, transparent);
		font-style: italic;
	}
	.editor-name-input:focus {
		outline: none;
	}

	.editor-head-right {
		display: flex;
		align-items: flex-start;
		gap: 0.5rem;
		flex-shrink: 0;
		padding-top: 1.05rem;
	}

	.type-pills {
		display: flex;
		gap: 0.25rem;
		padding: 0.25rem;
		background: color-mix(in oklch, var(--muted) 50%, transparent);
		border: 1px solid var(--border);
		border-radius: 0.4rem;
	}

	.type-pill {
		padding: 0.32rem 0.65rem;
		font-size: 0.65rem;
		letter-spacing: 0.06em;
		font-family: var(--font-mono);
		text-transform: lowercase;
		border-radius: 0.25rem;
		color: color-mix(in oklch, var(--foreground) 45%, transparent);
		background: transparent;
		transition: background 150ms ease, color 150ms ease;
	}
	.type-pill:hover {
		color: var(--type-color);
	}
	.type-pill.active {
		background: color-mix(in oklch, var(--type-color) 18%, transparent);
		color: var(--type-color);
	}

	.editor-hint {
		font-size: 0.7rem;
		line-height: 1.5;
		color: color-mix(in oklch, var(--foreground) 40%, transparent);
		max-width: 60ch;
	}

	/* ── Textarea: fills available height ────────────────────── */
	.editor-textarea {
		flex: 1;
		min-height: 0;
		width: 100%;
		resize: none;
		background: color-mix(in oklch, var(--card) 60%, transparent);
		border: 1px solid var(--border);
		border-radius: 0.5rem;
		padding: 1.1rem 1.3rem;
		font-family: var(--font-mono);
		font-size: 0.82rem;
		line-height: 1.65;
		color: var(--foreground);
		transition: border-color 150ms ease, box-shadow 150ms ease;
	}

	.editor-textarea:focus {
		outline: none;
		border-color: color-mix(in oklch, var(--type-color, var(--primary)) 50%, var(--border));
		box-shadow: 0 0 0 3px color-mix(in oklch, var(--type-color, var(--primary)) 8%, transparent);
	}

	.editor-textarea::placeholder {
		color: color-mix(in oklch, var(--foreground) 28%, transparent);
	}

	.editor-error {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.7rem;
		color: var(--destructive);
		padding: 0.5rem 0.7rem;
		background: color-mix(in oklch, var(--destructive) 8%, transparent);
		border: 1px solid color-mix(in oklch, var(--destructive) 28%, transparent);
		border-radius: 0.3rem;
	}

	/* ── Editor footer ───────────────────────────────────────── */
	.editor-foot {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.85rem;
		padding-top: 0.25rem;
	}

	.editor-foot-right {
		display: flex;
		align-items: center;
		gap: 0.85rem;
	}

	.btn-primary {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.5rem 1rem;
		background: var(--primary);
		color: var(--primary-foreground);
		border-radius: 0.35rem;
		font-size: 0.78rem;
		font-weight: 500;
		letter-spacing: 0.01em;
		box-shadow: 0 0 14px color-mix(in oklch, var(--primary) 22%, transparent);
		transition: filter 150ms ease, transform 150ms ease, opacity 150ms ease;
	}
	.btn-primary:hover:not(:disabled) {
		filter: brightness(1.07);
		transform: translateY(-1px);
	}
	.btn-primary:disabled {
		opacity: 0.4;
		cursor: not-allowed;
		box-shadow: none;
	}

	.btn-cancel {
		font-size: 0.7rem;
		letter-spacing: 0.04em;
		color: color-mix(in oklch, var(--foreground) 45%, transparent);
		padding: 0.5rem 0.4rem;
		transition: color 150ms ease;
	}
	.btn-cancel:hover {
		color: var(--foreground);
	}

	.btn-delete {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		font-size: 0.7rem;
		letter-spacing: 0.04em;
		color: color-mix(in oklch, var(--destructive) 70%, transparent);
		padding: 0.5rem 0.5rem;
		border-radius: 0.3rem;
		transition: color 150ms ease, background 150ms ease;
	}
	.btn-delete:hover {
		color: var(--destructive);
		background: color-mix(in oklch, var(--destructive) 8%, transparent);
	}

	.dirty-hint {
		font-size: 0.62rem;
		letter-spacing: 0.06em;
		color: color-mix(in oklch, var(--primary) 80%, transparent);
		opacity: 0;
		transition: opacity 150ms ease;
	}
	.dirty-hint.visible {
		opacity: 1;
	}

	/* ── Spinner ─────────────────────────────────────────────── */
	.spinner {
		display: inline-block;
		width: 11px;
		height: 11px;
		border-radius: 9999px;
		border: 1.5px solid currentColor;
		border-right-color: transparent;
		animation: spin 0.75s linear infinite;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* ── Empty state (no selection) ──────────────────────────── */
	.empty {
		flex: 1;
		display: flex;
		flex-direction: column;
		justify-content: center;
		padding: 3rem 3.5rem;
		max-width: 60rem;
		margin: 0 auto;
		width: 100%;
	}

	.empty-eyebrow {
		font-size: 0.62rem;
		letter-spacing: 0.18em;
		text-transform: uppercase;
		color: color-mix(in oklch, var(--foreground) 35%, transparent);
		margin-bottom: 1rem;
	}

	.empty-title {
		font-size: 2.6rem;
		line-height: 1.05;
		font-style: italic;
		letter-spacing: -0.02em;
		margin-bottom: 1rem;
	}
	.empty-title em {
		color: var(--primary);
		font-style: italic;
	}

	.empty-sub {
		font-size: 0.95rem;
		line-height: 1.6;
		color: var(--muted-foreground);
		max-width: 36rem;
		margin-bottom: 2.5rem;
	}

	.slot-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 0.85rem;
	}

	.slot-card {
		--type-color: var(--primary);
		position: relative;
		display: flex;
		flex-direction: column;
		gap: 0.55rem;
		padding: 1.1rem 1.2rem 1rem;
		text-align: left;
		border: 1px solid var(--border);
		border-radius: 0.5rem;
		background: color-mix(in oklch, var(--card) 60%, transparent);
		overflow: hidden;
		transition: border-color 150ms ease, transform 150ms ease, background 150ms ease;
	}
	.slot-card::before {
		content: '';
		position: absolute;
		left: 0;
		top: 0;
		bottom: 0;
		width: 3px;
		background: var(--type-color);
		opacity: 0.55;
		transition: opacity 200ms ease, width 200ms ease;
	}
	.slot-card:hover {
		border-color: color-mix(in oklch, var(--type-color) 35%, var(--border));
		transform: translateY(-2px);
	}
	.slot-card:hover::before {
		opacity: 1;
		width: 4px;
	}

	.slot-card-head {
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}

	.slot-card-label {
		font-size: 0.68rem;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		font-weight: 600;
		color: var(--type-color);
	}

	.slot-card-count {
		margin-left: auto;
		font-size: 0.6rem;
		padding: 0.1rem 0.4rem;
		border-radius: 999px;
		background: color-mix(in oklch, var(--type-color) 12%, transparent);
		color: var(--type-color);
	}

	.slot-card-desc {
		font-size: 0.78rem;
		line-height: 1.55;
		color: color-mix(in oklch, var(--foreground) 70%, transparent);
	}

	.slot-card-cta {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		font-size: 0.62rem;
		letter-spacing: 0.06em;
		color: var(--type-color);
		opacity: 0.75;
		transition: opacity 150ms ease;
	}
	.slot-card:hover .slot-card-cta {
		opacity: 1;
	}

	/* ── Responsive: collapse rail on narrow viewports ───────── */
	@media (max-width: 880px) {
		.shell {
			grid-template-columns: 1fr;
			grid-template-rows: auto 1fr;
		}
		.rail {
			max-height: 220px;
			border-right: none;
			border-bottom: 1px solid var(--border);
		}
		.editor {
			padding: 1.25rem 1.25rem 1rem;
		}
		.editor-name-input {
			font-size: 1.5rem;
		}
		.empty {
			padding: 1.75rem 1.5rem;
		}
		.slot-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
