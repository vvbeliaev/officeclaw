<script lang="ts">
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import { Icon } from '$lib/icons';

	let { data, form } = $props();

	let content = $state(data.userTemplate?.content ?? '');
	let saving = $state(false);
	let dirty = $derived(content !== (data.userTemplate?.content ?? ''));
</script>

<div class="shell">
	<!-- Header -->
	<header class="page-head">
		<div class="crumb font-mono">profile</div>
		<h1 class="page-title font-display">Your Profile</h1>
		<p class="page-sub">Personal context attached to agents so they know who they're working for.</p>
	</header>

	<div class="body">
		<!-- Identity (read-only) -->
		<section class="section">
			<header class="section-head">
				<span class="section-title font-mono">identity</span>
			</header>
			<div class="form-block">
				<div class="field-row">
					<div class="field">
						<span class="field-label font-mono">Name</span>
						<div class="field-static">{data.user?.name ?? '—'}</div>
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
