<script lang="ts">
	import { enhance } from '$app/forms';
	import { Icon } from '$lib/icons';

	let { data, form } = $props();

	const workspace = $derived(data.workspace);

	let name = $state(workspace.name);
	let slug = $state(workspace.slug);
	let saving = $state(false);
	let deleting = $state(false);
	let confirmDelete = $state('');
	let showDeleteZone = $state(false);

	const slugPreview = $derived(`/w/${slug || '…'}/`);
	const slugValid = $derived(
		slug.length >= 3 && slug.length <= 64 && /^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$/.test(slug)
	);
	const nameChanged = $derived(name !== workspace.name);
	const slugChanged = $derived(slug !== workspace.slug);
	const hasChanges = $derived(nameChanged || slugChanged);
	const canSave = $derived(hasChanges && name.trim().length > 0 && slugValid && !saving);
	const canDelete = $derived(confirmDelete === workspace.slug);

	function onSlugInput(e: Event) {
		const raw = (e.target as HTMLInputElement).value;
		slug = raw.toLowerCase().replace(/[^a-z0-9-]/g, '').replace(/--+/g, '-');
	}
</script>

<div class="page">
	<header class="page-header">
		<h1 class="page-title">Workspace Settings</h1>
		<p class="page-sub font-mono">{workspace.slug}</p>
	</header>

	<!-- General section -->
	<section class="card">
		<div class="card-header">
			<span class="card-label">General</span>
		</div>

		<form
			method="POST"
			action="?/update"
			use:enhance={() => {
				saving = true;
				return async ({ update }) => {
					await update();
					saving = false;
				};
			}}
		>
			<div class="field">
				<label class="field-label font-mono" for="ws-name">Name</label>
				<input
					id="ws-name"
					name="name"
					type="text"
					class="field-input"
					bind:value={name}
					maxlength={64}
					placeholder="My Workspace"
					autocomplete="off"
				/>
				<p class="field-hint">Displayed in navigation and the workspace switcher.</p>
			</div>

			<div class="field">
				<label class="field-label font-mono" for="ws-slug">Slug</label>
				<div class="slug-wrap">
					<span class="slug-prefix font-mono">/w/</span>
					<input
						id="ws-slug"
						name="slug"
						type="text"
						class="field-input slug-input font-mono"
						class:invalid={slug.length > 0 && !slugValid}
						value={slug}
						oninput={onSlugInput}
						maxlength={64}
						placeholder="my-workspace"
						autocomplete="off"
						spellcheck="false"
					/>
				</div>
				<p class="field-hint">
					Used in all URLs. Lowercase letters, digits, and hyphens only.
					{#if slug.length > 0 && !slugValid}
						<span class="hint-error"> — invalid slug</span>
					{:else if slugChanged}
						<span class="hint-warn"> — all existing links will break</span>
					{/if}
				</p>
			</div>

			{#if form?.error}
				<p class="form-error font-mono">{form.error}</p>
			{/if}
			{#if form?.success}
				<p class="form-success font-mono">Saved.</p>
			{/if}

			<div class="card-footer">
				<button
					type="submit"
					class="btn-primary font-mono"
					disabled={!canSave}
				>
					{#if saving}
						<span class="spinner"></span>saving…
					{:else}
						Save changes
					{/if}
				</button>
				{#if hasChanges}
					<button
						type="button"
						class="btn-ghost font-mono"
						onclick={() => { name = workspace.name; slug = workspace.slug; }}
					>
						Discard
					</button>
				{/if}
			</div>
		</form>
	</section>

	<!-- Token section -->
	<section class="card">
		<div class="card-header">
			<span class="card-label">MCP Token</span>
		</div>
		<div class="field">
			<p class="field-hint">Bearer token for MCP clients connecting to this workspace.</p>
			<div class="token-row">
				<code class="token-value font-mono">{"•".repeat(32)}</code>
				<span class="token-badge font-mono">read-only</span>
			</div>
		</div>
	</section>

	<!-- Danger zone -->
	<section class="card danger-card">
		<div class="card-header">
			<span class="card-label danger-label">Danger Zone</span>
		</div>

		<div class="danger-row">
			<div class="danger-info">
				<p class="danger-title">Delete this workspace</p>
				<p class="field-hint">
					Permanently removes this workspace, all agents, envs, channels, and MCP configs.
					This action is irreversible.
				</p>
			</div>
			<button
				type="button"
				class="btn-danger font-mono"
				onclick={() => { showDeleteZone = !showDeleteZone; confirmDelete = ''; }}
			>
				{showDeleteZone ? 'Cancel' : 'Delete workspace'}
			</button>
		</div>

		{#if showDeleteZone}
			<form
				method="POST"
				action="?/delete"
				class="confirm-form"
				use:enhance={() => {
					deleting = true;
					return async ({ update }) => {
						await update();
						deleting = false;
					};
				}}
			>
				<label class="field-label font-mono" for="confirm-slug">
					Type <strong class="confirm-slug font-mono">{workspace.slug}</strong> to confirm
				</label>
				<div class="confirm-row">
					<input
						id="confirm-slug"
						type="text"
						class="field-input font-mono"
						bind:value={confirmDelete}
						placeholder={workspace.slug}
						autocomplete="off"
						spellcheck="false"
					/>
					<button
						type="submit"
						class="btn-danger font-mono"
						disabled={!canDelete || deleting}
					>
						{#if deleting}
							<span class="spinner"></span>deleting…
						{:else}
							Confirm delete
						{/if}
					</button>
				</div>
			</form>
		{/if}
	</section>
</div>

<style>
	.page {
		max-width: 640px;
		margin: 0 auto;
		padding: 2.5rem 2rem 4rem;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	/* ── Header ─────────────────────────────────────────────── */
	.page-header {
		margin-bottom: 0.5rem;
	}

	.page-title {
		font-family: 'Fraunces Variable', serif;
		font-size: 1.75rem;
		font-weight: 600;
		line-height: 1.1;
		color: var(--foreground);
		letter-spacing: -0.02em;
	}

	.page-sub {
		margin-top: 0.3rem;
		font-size: 0.75rem;
		color: var(--muted-foreground);
		letter-spacing: 0.02em;
	}

	/* ── Card ────────────────────────────────────────────────── */
	.card {
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.5rem;
		overflow: hidden;
	}

	.card-header {
		padding: 0.75rem 1.25rem;
		border-bottom: 1px solid var(--border);
	}

	.card-label {
		font-size: 0.62rem;
		font-family: var(--font-mono, 'DM Mono', monospace);
		text-transform: uppercase;
		letter-spacing: 0.16em;
		color: var(--muted-foreground);
	}

	/* ── Fields ──────────────────────────────────────────────── */
	.field {
		padding: 1rem 1.25rem 0;
	}

	.field:last-of-type {
		padding-bottom: 0;
	}

	.field-label {
		display: block;
		font-size: 0.72rem;
		color: var(--foreground);
		margin-bottom: 0.4rem;
		letter-spacing: 0.01em;
	}

	.field-input {
		width: 100%;
		padding: 0.5rem 0.7rem;
		background: var(--background);
		border: 1px solid var(--border);
		border-radius: 0.35rem;
		font-size: 0.875rem;
		color: var(--foreground);
		outline: none;
		transition: border-color 150ms ease, box-shadow 150ms ease;
	}

	.field-input:focus {
		border-color: var(--primary);
		box-shadow: 0 0 0 2px var(--ring);
	}

	.field-input.invalid {
		border-color: var(--destructive);
		box-shadow: 0 0 0 2px color-mix(in oklch, var(--destructive) 25%, transparent);
	}

	.field-hint {
		margin-top: 0.4rem;
		font-size: 0.72rem;
		color: var(--muted-foreground);
		line-height: 1.5;
		padding-bottom: 1rem;
	}

	/* ── Slug field ──────────────────────────────────────────── */
	.slug-wrap {
		display: flex;
		align-items: center;
		background: var(--background);
		border: 1px solid var(--border);
		border-radius: 0.35rem;
		overflow: hidden;
		transition: border-color 150ms ease, box-shadow 150ms ease;
		focus-within: border-color var(--primary);
	}

	.slug-wrap:focus-within {
		border-color: var(--primary);
		box-shadow: 0 0 0 2px var(--ring);
	}

	.slug-wrap:has(.invalid) {
		border-color: var(--destructive);
		box-shadow: 0 0 0 2px color-mix(in oklch, var(--destructive) 25%, transparent);
	}

	.slug-prefix {
		padding: 0.5rem 0 0.5rem 0.7rem;
		font-size: 0.8rem;
		color: var(--muted-foreground);
		white-space: nowrap;
		flex-shrink: 0;
	}

	.slug-input {
		border: none;
		border-radius: 0;
		padding-left: 0.1rem;
		background: transparent;
		box-shadow: none !important;
	}

	.slug-input:focus {
		border-color: transparent;
		box-shadow: none !important;
	}

	.hint-error {
		color: var(--destructive);
	}

	.hint-warn {
		color: oklch(0.75 0.14 72);
	}

	/* ── Card footer ─────────────────────────────────────────── */
	.card-footer {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 1rem 1.25rem;
		border-top: 1px solid var(--border);
		margin-top: 0.25rem;
	}

	/* ── Token ───────────────────────────────────────────────── */
	.token-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.5rem 0.7rem;
		background: var(--background);
		border: 1px solid var(--border);
		border-radius: 0.35rem;
		margin-bottom: 1rem;
	}

	.token-value {
		flex: 1;
		font-size: 0.78rem;
		color: var(--muted-foreground);
		letter-spacing: 0.12em;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.token-badge {
		font-size: 0.58rem;
		text-transform: uppercase;
		letter-spacing: 0.14em;
		color: var(--muted-foreground);
		background: var(--muted);
		padding: 0.15rem 0.45rem;
		border-radius: 0.2rem;
		white-space: nowrap;
	}

	/* ── Danger zone ─────────────────────────────────────────── */
	.danger-card {
		border-color: color-mix(in oklch, var(--destructive) 25%, var(--border));
	}

	.danger-label {
		color: var(--destructive);
	}

	.danger-row {
		display: flex;
		align-items: flex-start;
		gap: 1rem;
		padding: 1rem 1.25rem;
	}

	.danger-info {
		flex: 1;
	}

	.danger-title {
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--foreground);
		margin-bottom: 0.25rem;
	}

	.confirm-form {
		padding: 0 1.25rem 1.25rem;
		border-top: 1px solid color-mix(in oklch, var(--destructive) 15%, var(--border));
		padding-top: 1rem;
	}

	.confirm-slug {
		font-family: 'DM Mono', monospace;
		color: var(--foreground);
		font-weight: 500;
	}

	.confirm-row {
		display: flex;
		gap: 0.75rem;
		margin-top: 0.5rem;
	}

	.confirm-row .field-input {
		flex: 1;
	}

	/* ── Buttons ─────────────────────────────────────────────── */
	.btn-primary {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.45rem 1rem;
		font-size: 0.75rem;
		letter-spacing: 0.04em;
		background: var(--primary);
		color: var(--primary-foreground);
		border-radius: 0.3rem;
		transition: opacity 150ms ease;
	}

	.btn-primary:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.btn-ghost {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.45rem 0.75rem;
		font-size: 0.75rem;
		letter-spacing: 0.04em;
		color: var(--muted-foreground);
		border-radius: 0.3rem;
		transition: color 150ms ease, background 150ms ease;
	}

	.btn-ghost:hover {
		color: var(--foreground);
		background: var(--accent);
	}

	.btn-danger {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.45rem 1rem;
		font-size: 0.75rem;
		letter-spacing: 0.04em;
		color: var(--destructive);
		border: 1px solid color-mix(in oklch, var(--destructive) 40%, transparent);
		border-radius: 0.3rem;
		white-space: nowrap;
		transition: background 150ms ease, color 150ms ease;
	}

	.btn-danger:hover:not(:disabled) {
		background: color-mix(in oklch, var(--destructive) 12%, transparent);
	}

	.btn-danger:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	/* ── Form feedback ───────────────────────────────────────── */
	.form-error {
		font-size: 0.72rem;
		color: var(--destructive);
		padding: 0 1.25rem;
		margin-bottom: 0.25rem;
	}

	.form-success {
		font-size: 0.72rem;
		color: var(--status-running);
		padding: 0 1.25rem;
		margin-bottom: 0.25rem;
	}

	/* ── Spinner ─────────────────────────────────────────────── */
	.spinner {
		display: inline-block;
		width: 10px;
		height: 10px;
		border-radius: 9999px;
		border: 1.5px solid currentColor;
		border-right-color: transparent;
		animation: spin 0.7s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}
</style>
