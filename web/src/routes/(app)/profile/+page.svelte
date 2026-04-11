<script lang="ts">
	import { enhance } from '$app/forms';
	import { goto, invalidateAll } from '$app/navigation';
	import { authClient } from '$lib/auth-client';
	import { Icon } from '$lib/icons';

	let { data, form } = $props();

	// USER template
	let content = $state(data.userTemplate?.content ?? '');
	let saving = $state(false);
	let dirty = $derived(content !== (data.userTemplate?.content ?? ''));

	// Name editing
	let nameEdit = $state(data.user?.name ?? '');
	let nameSaving = $state(false);
	let nameDirty = $derived(nameEdit.trim() !== (data.user?.name ?? '').trim());
	let nameError = $state<string | null>(null);

	async function saveName() {
		if (!nameDirty || nameSaving) return;
		nameSaving = true;
		nameError = null;
		try {
			const { error } = await authClient.updateUser({ name: nameEdit.trim() });
			if (error) {
				nameError = error.message ?? 'Failed to update name';
			} else {
				await invalidateAll();
			}
		} catch (e) {
			nameError = e instanceof Error ? e.message : 'Failed to update name';
		} finally {
			nameSaving = false;
		}
	}

	function onNameKey(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			saveName();
		} else if (e.key === 'Escape') {
			nameEdit = data.user?.name ?? '';
			nameError = null;
		}
	}

	async function signOut() {
		await authClient.signOut();
		goto('/auth');
	}
</script>

<div class="shell">
	<!-- Header -->
	<header class="page-head">
		<div class="page-head-left">
			<div class="crumb font-mono">profile</div>
			<h1 class="page-title font-display">Your Profile</h1>
			<p class="page-sub">Personal context attached to agents so they know who they're working for.</p>
		</div>
		<button class="btn-signout" onclick={signOut}>
			<Icon icon="tabler:logout" width={14} height={14} />
			Sign out
		</button>
	</header>

	<div class="body">
		<!-- Identity -->
		<section class="section">
			<header class="section-head">
				<span class="section-title font-mono">identity</span>
			</header>
			<div class="form-block">
				<div class="field-row">
					<div class="field">
						<label class="field-label font-mono" for="name-input">Name</label>
						<div class="field-editable">
							<input
								id="name-input"
								class="field-input"
								type="text"
								bind:value={nameEdit}
								onkeydown={onNameKey}
								placeholder="Your name"
								disabled={nameSaving}
							/>
							{#if nameDirty}
								<button
									class="btn-field-save font-mono"
									type="button"
									onclick={saveName}
									disabled={nameSaving}
								>
									{nameSaving ? '…' : 'save'}
								</button>
							{/if}
						</div>
						{#if nameError}
							<p class="field-error font-mono">{nameError}</p>
						{/if}
					</div>
					<div class="field">
						<span class="field-label font-mono">Email</span>
						<div class="field-static">{data.user?.email ?? '—'}</div>
					</div>
				</div>
			</div>
		</section>

		<!-- About me — user template -->
		<section class="section">
			<header class="section-head">
				<span class="section-title font-mono">about me</span>
				<span class="section-hint font-mono">USER.md template · prepended to agents that attach it</span>
			</header>

			<form
				method="POST"
				action="?/saveUserTemplate"
				use:enhance={() => {
					saving = true;
					return async ({ update }) => {
						await update({ reset: false });
						await invalidateAll();
						saving = false;
					};
				}}
				class="form-block"
			>
				{#if data.userTemplate}
					<input type="hidden" name="id" value={data.userTemplate.id} />
				{/if}
				<input type="hidden" name="name" value="About me" />

				<div class="field">
					<label class="field-label font-mono" for="about-content">Content</label>
					<p class="field-hint">
						Write who you are, your goals, preferences, working style. Agents with this template attached will read it as <code>USER.md</code>.
					</p>
					<textarea
						id="about-content"
						name="content"
						class="about-textarea"
						placeholder="I'm building an AI-agent platform. My priorities are…"
						bind:value={content}
						rows={14}
					></textarea>
				</div>

				{#if form?.error}
					<p class="form-error font-mono">{form.error}</p>
				{/if}
				{#if form?.success}
					<p class="form-ok font-mono">Saved.</p>
				{/if}

				<div class="form-foot">
					<button class="btn-save" type="submit" disabled={saving || !dirty}>
						{#if saving}
							<span class="spinner"></span>saving…
						{:else}
							Save
						{/if}
					</button>
					{#if data.userTemplate}
						<span class="save-meta font-mono">
							last saved {new Date(data.userTemplate.updatedAt).toLocaleDateString('en', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
						</span>
					{/if}
				</div>
			</form>
		</section>
	</div>
</div>

<style>
	.shell {
		flex: 1;
		display: flex;
		flex-direction: column;
		overflow-y: auto;
	}

	.page-head {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 1rem;
		padding: 1.75rem 3rem 1.5rem;
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
	}

	.page-head-left {
		flex: 1;
		min-width: 0;
	}

	.crumb {
		font-size: 0.62rem;
		letter-spacing: 0.16em;
		text-transform: uppercase;
		color: color-mix(in oklch, var(--foreground) 35%, transparent);
		margin-bottom: 0.75rem;
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
		max-width: 40rem;
	}

	.btn-signout {
		display: flex;
		align-items: center;
		gap: 0.45rem;
		padding: 0.45rem 0.85rem;
		font-size: 0.78rem;
		border: 1px solid var(--border);
		border-radius: 0.35rem;
		color: var(--muted-foreground);
		background: transparent;
		flex-shrink: 0;
		margin-top: 0.25rem;
		transition:
			color 150ms ease,
			border-color 150ms ease,
			background 150ms ease;
	}

	.btn-signout:hover {
		color: var(--destructive);
		border-color: color-mix(in oklch, var(--destructive) 40%, transparent);
		background: color-mix(in oklch, var(--destructive) 6%, transparent);
	}

	.body {
		flex: 1;
		padding: 2rem 3rem;
		display: flex;
		flex-direction: column;
		gap: 2rem;
		max-width: 56rem;
	}

	.section {
		display: flex;
		flex-direction: column;
		gap: 0;
	}

	.section-head {
		display: flex;
		align-items: baseline;
		gap: 0.75rem;
		padding-bottom: 0.75rem;
		border-bottom: 1px solid var(--border);
		margin-bottom: 1rem;
	}

	.section-title {
		font-size: 0.62rem;
		letter-spacing: 0.16em;
		text-transform: uppercase;
		color: color-mix(in oklch, var(--foreground) 45%, transparent);
	}

	.section-hint {
		font-size: 0.62rem;
		letter-spacing: 0.04em;
		color: color-mix(in oklch, var(--foreground) 28%, transparent);
	}

	.form-block {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	.field-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
	}

	.field {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}

	.field-label {
		font-size: 0.65rem;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: color-mix(in oklch, var(--foreground) 50%, transparent);
	}

	.field-static {
		font-size: 0.875rem;
		color: var(--foreground);
		padding: 0.55rem 0.75rem;
		background: color-mix(in oklch, var(--muted) 40%, transparent);
		border: 1px solid var(--border);
		border-radius: 0.375rem;
	}

	.field-editable {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		background: color-mix(in oklch, var(--muted) 25%, transparent);
		border: 1px solid var(--border);
		border-radius: 0.375rem;
		transition: border-color 150ms ease;
	}

	.field-editable:focus-within {
		border-color: var(--primary);
	}

	.field-input {
		flex: 1;
		background: transparent;
		border: none;
		outline: none;
		padding: 0.55rem 0.75rem;
		font-size: 0.875rem;
		color: var(--foreground);
		font-family: var(--font-sans);
	}

	.field-input::placeholder {
		color: color-mix(in oklch, var(--foreground) 28%, transparent);
	}

	.field-input:disabled {
		opacity: 0.5;
	}

	.btn-field-save {
		padding: 0.25rem 0.6rem;
		margin-right: 0.35rem;
		font-size: 0.62rem;
		letter-spacing: 0.06em;
		color: var(--primary);
		border-radius: 0.2rem;
		background: color-mix(in oklch, var(--primary) 12%, transparent);
		transition: background 150ms ease;
		flex-shrink: 0;
	}

	.btn-field-save:hover:not(:disabled) {
		background: color-mix(in oklch, var(--primary) 20%, transparent);
	}

	.btn-field-save:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.field-error {
		font-size: 0.68rem;
		color: var(--destructive);
		letter-spacing: 0.02em;
	}

	.field-hint {
		font-size: 0.78rem;
		color: var(--muted-foreground);
		line-height: 1.5;
	}

	.field-hint code {
		font-family: var(--font-mono);
		font-size: 0.75em;
		background: color-mix(in oklch, var(--muted) 60%, transparent);
		padding: 0.1em 0.35em;
		border-radius: 0.2rem;
	}

	.about-textarea {
		width: 100%;
		min-height: 260px;
		background: color-mix(in oklch, var(--muted) 25%, transparent);
		border: 1px solid var(--border);
		border-radius: 0.375rem;
		padding: 0.85rem 1rem;
		font-size: 0.875rem;
		font-family: var(--font-mono);
		color: var(--foreground);
		resize: vertical;
		line-height: 1.6;
		transition: border-color 150ms ease;
	}

	.about-textarea:focus {
		outline: none;
		border-color: var(--primary);
	}

	.about-textarea::placeholder {
		color: color-mix(in oklch, var(--foreground) 28%, transparent);
	}

	.form-error {
		font-size: 0.72rem;
		color: var(--destructive);
		letter-spacing: 0.02em;
	}

	.form-ok {
		font-size: 0.72rem;
		color: var(--primary);
		letter-spacing: 0.02em;
	}

	.form-foot {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.btn-save {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.5rem 1.1rem;
		background: var(--primary);
		color: var(--primary-foreground);
		border-radius: 0.35rem;
		font-size: 0.8rem;
		font-weight: 500;
		transition: opacity 150ms ease;
	}

	.btn-save:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.save-meta {
		font-size: 0.62rem;
		letter-spacing: 0.04em;
		color: color-mix(in oklch, var(--foreground) 30%, transparent);
	}

	.spinner {
		display: inline-block;
		width: 10px;
		height: 10px;
		border-radius: 9999px;
		border: 1.5px solid currentColor;
		border-right-color: transparent;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}
</style>
