<script lang="ts">
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import AgentAvatar from '$lib/components/agent-avatar.svelte';
	import { Icon } from '$lib/icons';
	import { resolve } from '$app/paths';

	let { data, form } = $props();

	let nameValue = $derived(data.agent.name);
	let confirmDelete = $state(false);
	let saving = $state(false);
	let deleting = $state(false);
</script>

<div class="settings-shell">
	<!-- ── Header ──────────────────────────────────────────────── -->
	<header class="settings-header">
		<div class="header-left">
			<a href={resolve(`/agents/${data.agent.id}`)} class="back-btn" aria-label="Back to chat">
				<Icon icon="tabler:arrow-left" width={14} height={14} />
				<span>Back</span>
			</a>
			<div class="header-divider"></div>
			<AgentAvatar name={data.agent.name} isAdmin={data.agent.isAdmin} size={28} />
			<h1 class="agent-name font-display">{data.agent.name}</h1>
		</div>
		<span class="settings-label font-mono">settings</span>
	</header>

	<!-- ── Body ────────────────────────────────────────────────── -->
	<div class="settings-body">
		<div class="settings-content">
			<!-- ── Identity ──────────────────────────────────── -->
			<section class="section">
				<header class="section-head">
					<span class="section-title font-mono">identity</span>
				</header>

				<form
					method="POST"
					action="?/update"
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
					<div class="field">
						<label class="field-label font-mono" for="agent-name">Name</label>
						<input
							id="agent-name"
							name="name"
							type="text"
							class="field-input"
							bind:value={nameValue}
							maxlength={64}
							required
						/>
						<p class="field-hint">How this agent appears in your fleet.</p>
					</div>

					{#if form?.error}
						<p class="form-error font-mono">{form.error}</p>
					{/if}
					{#if form?.success}
						<p class="form-ok font-mono">Saved.</p>
					{/if}

					<div class="form-foot">
						<button class="btn-primary" type="submit" disabled={saving}>
							{#if saving}
								<span class="spinner"></span>saving…
							{:else}
								Save changes
							{/if}
						</button>
					</div>
				</form>
			</section>

			<!-- ── Runtime ───────────────────────────────────── -->
			<section class="section">
				<header class="section-head">
					<span class="section-title font-mono">runtime</span>
				</header>
				<div class="form-block">
					<div class="field">
						<label class="field-label font-mono" for="agent-image">Container image</label>
						<input
							id="agent-image"
							type="text"
							class="field-input field-input--readonly"
							value={data.agent.image}
							readonly
						/>
						<p class="field-hint">Docker image used when starting the sandbox. Editable soon.</p>
					</div>
				</div>
			</section>

			<!-- ── Connections ───────────────────────────────── -->
			<section class="section">
				<header class="section-head">
					<span class="section-title font-mono">connections</span>
					<span class="section-badge font-mono">soon</span>
				</header>
				<div class="connections-grid">
					<div class="conn-card">
						<Icon icon="tabler:plug" width={16} height={16} />
						<span class="conn-label font-mono">MCPs</span>
						<span class="conn-count font-mono">—</span>
					</div>
					<div class="conn-card">
						<Icon icon="tabler:bulb" width={16} height={16} />
						<span class="conn-label font-mono">Skills</span>
						<span class="conn-count font-mono">—</span>
					</div>
					<div class="conn-card">
						<Icon icon="tabler:key" width={16} height={16} />
						<span class="conn-label font-mono">Env vars</span>
						<span class="conn-count font-mono">—</span>
					</div>
					<div class="conn-card">
						<Icon icon="tabler:message" width={16} height={16} />
						<span class="conn-label font-mono">Channels</span>
						<span class="conn-count font-mono">—</span>
					</div>
				</div>
			</section>

			<!-- ── Danger zone ───────────────────────────────── -->
			{#if !data.agent.isAdmin}
				<section class="section section--danger">
					<header class="section-head">
						<span class="section-title font-mono">danger zone</span>
					</header>

					{#if !confirmDelete}
						<div class="form-block">
							<p class="danger-desc">
								Permanently delete <strong>{data.agent.name}</strong> and all associated memories. This
								cannot be undone.
							</p>
							<button class="btn-danger" type="button" onclick={() => (confirmDelete = true)}>
								<Icon icon="tabler:trash" width={13} height={13} />
								Delete agent
							</button>
						</div>
					{:else}
						<div class="form-block">
							<p class="danger-confirm font-mono">
								Type <strong>{data.agent.name}</strong> to confirm deletion.
							</p>
							<form
								method="POST"
								action="?/delete"
								use:enhance={() => {
									deleting = true;
									return async ({ update }) => {
										await update();
										deleting = false;
									};
								}}
								class="confirm-form"
							>
								<button class="btn-danger" type="submit" disabled={deleting}>
									{#if deleting}
										<span class="spinner spinner--danger"></span>deleting…
									{:else}
										<Icon icon="tabler:trash" width={13} height={13} />
										Yes, delete {data.agent.name}
									{/if}
								</button>
								<button class="btn-ghost" type="button" onclick={() => (confirmDelete = false)}>
									Cancel
								</button>
							</form>
						</div>
					{/if}
				</section>
			{/if}
		</div>
	</div>
</div>

<style>
	.settings-shell {
		display: flex;
		flex-direction: column;
		height: 100vh;
		max-height: 100vh;
		background: var(--background);
	}

	/* ── Header ────────────────────────────────────────────── */
	.settings-header {
		height: 56px;
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 1.5rem;
		border-bottom: 1px solid var(--border);
		background: var(--background);
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 0.85rem;
	}

	.back-btn {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.72rem;
		font-family: var(--font-mono);
		color: var(--muted-foreground);
		text-decoration: none;
		padding: 0.35rem 0.6rem;
		border-radius: 0.25rem;
		transition:
			color 150ms ease,
			background 150ms ease;
	}

	.back-btn:hover {
		color: var(--foreground);
		background: var(--muted);
	}

	.header-divider {
		width: 1px;
		height: 18px;
		background: var(--border);
	}

	.agent-name {
		font-size: 1.05rem;
		font-style: italic;
		line-height: 1;
		letter-spacing: -0.005em;
	}

	.settings-label {
		font-size: 0.6rem;
		text-transform: uppercase;
		letter-spacing: 0.16em;
		color: var(--muted-foreground);
		opacity: 0.6;
	}

	/* ── Body ─────────────────────────────────────────────── */
	.settings-body {
		flex: 1;
		overflow-y: auto;
		padding: 2.5rem 1.5rem 4rem;
	}

	.settings-content {
		max-width: 36rem;
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 2.5rem;
	}

	/* ── Section ──────────────────────────────────────────── */
	.section {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.section-head {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding-bottom: 0.65rem;
		border-bottom: 1px solid var(--border);
	}

	.section-title {
		font-size: 0.6rem;
		text-transform: uppercase;
		letter-spacing: 0.18em;
		color: var(--muted-foreground);
	}

	.section-badge {
		font-size: 0.52rem;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--muted-foreground);
		background: color-mix(in oklch, var(--muted) 60%, transparent);
		padding: 0.1rem 0.38rem;
		border-radius: 2px;
		opacity: 0.6;
	}

	.section--danger .section-title {
		color: color-mix(in oklch, var(--destructive) 80%, var(--muted-foreground));
	}

	/* ── Form ─────────────────────────────────────────────── */
	.form-block {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.field {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}

	.field-label {
		font-size: 0.65rem;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--muted-foreground);
	}

	.field-input {
		width: 100%;
		padding: 0.6rem 0.85rem;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.3rem;
		color: var(--foreground);
		font-family: var(--font-sans);
		font-size: 0.92rem;
		transition:
			border-color 150ms ease,
			box-shadow 150ms ease;
		outline: none;
	}

	.field-input:focus {
		border-color: color-mix(in oklch, var(--primary) 55%, var(--border));
		box-shadow: 0 0 0 3px color-mix(in oklch, var(--primary) 14%, transparent);
	}

	.field-input--readonly {
		opacity: 0.55;
		cursor: default;
		font-family: var(--font-mono);
		font-size: 0.8rem;
	}

	.field-hint {
		font-size: 0.7rem;
		color: var(--muted-foreground);
		line-height: 1.5;
		opacity: 0.8;
	}

	.form-error {
		font-size: 0.7rem;
		color: var(--destructive);
		letter-spacing: 0.02em;
	}

	.form-ok {
		font-size: 0.7rem;
		color: color-mix(in oklch, var(--status-running) 85%, var(--foreground));
		letter-spacing: 0.02em;
	}

	.form-foot {
		display: flex;
	}

	/* ── Buttons ──────────────────────────────────────────── */
	.btn-primary {
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
		padding: 0.55rem 1.1rem;
		background: var(--primary);
		color: var(--primary-foreground);
		font-family: var(--font-mono);
		font-size: 0.72rem;
		letter-spacing: 0.03em;
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

	.btn-danger {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.5rem 1rem;
		background: color-mix(in oklch, var(--destructive) 10%, transparent);
		color: var(--destructive);
		border: 1px solid color-mix(in oklch, var(--destructive) 35%, transparent);
		font-family: var(--font-mono);
		font-size: 0.72rem;
		letter-spacing: 0.03em;
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

	.btn-ghost {
		padding: 0.5rem 0.85rem;
		font-family: var(--font-mono);
		font-size: 0.72rem;
		color: var(--muted-foreground);
		border-radius: 0.25rem;
		transition:
			color 150ms ease,
			background 150ms ease;
	}

	.btn-ghost:hover {
		color: var(--foreground);
		background: var(--muted);
	}

	/* ── Connections grid ─────────────────────────────────── */
	.connections-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 0.6rem;
	}

	.conn-card {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		padding: 0.75rem 1rem;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.3rem;
		color: var(--muted-foreground);
		opacity: 0.5;
	}

	.conn-label {
		flex: 1;
		font-size: 0.68rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
	}

	.conn-count {
		font-size: 0.68rem;
		letter-spacing: 0.02em;
	}

	/* ── Danger desc ──────────────────────────────────────── */
	.danger-desc {
		font-size: 0.85rem;
		line-height: 1.55;
		color: var(--muted-foreground);
	}

	.danger-confirm {
		font-size: 0.75rem;
		color: var(--muted-foreground);
		line-height: 1.5;
	}

	.danger-confirm strong {
		color: var(--destructive);
	}

	.confirm-form {
		display: flex;
		align-items: center;
		gap: 0.6rem;
	}

	/* ── Spinner ──────────────────────────────────────────── */
	.spinner {
		display: inline-block;
		width: 11px;
		height: 11px;
		border-radius: 9999px;
		border: 1.5px solid currentColor;
		border-right-color: transparent;
		animation: spin 0.8s linear infinite;
	}

	.spinner--danger {
		border-color: var(--destructive);
		border-right-color: transparent;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
