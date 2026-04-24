<script lang="ts">
	import { enhance } from '$app/forms';
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/stores';
	import { Icon } from '$lib/icons';

	let { data, form } = $props();

	type SkillRow = {
		id: string;
		name: string;
		description: string;
		always: boolean;
		emoji: string | null;
		homepage: string | null;
		createdAt: Date;
		fileCount: number;
		agentCount: number;
	};

	const skills = $derived(data.skills as SkillRow[]);
	const workspaceId = $derived($page.params.workspaceId);

	// ── Create modal ──────────────────────────────────────────
	let createOpen = $state(false);
	let createName = $state('');
	let createDescription = $state('');
	let creating = $state(false);

	function openCreate() {
		createOpen = true;
		createName = '';
		createDescription = '';
	}
	function closeCreate() {
		createOpen = false;
	}

	// ── Import form ───────────────────────────────────────────
	let importOpen = $state(false);
	let importUrl = $state('');
	let importing = $state(false);

	function openImport() {
		importOpen = true;
		importUrl = '';
	}
	function closeImport() {
		importOpen = false;
	}

	// ── Delete confirm ────────────────────────────────────────
	let deleteId = $state<string | null>(null);
	let deleting = $state(false);

	function formatDate(date: Date): string {
		const diffMs = Date.now() - new Date(date).getTime();
		const days = Math.floor(diffMs / 86400000);
		if (days === 0) return 'today';
		if (days === 1) return 'yesterday';
		if (days < 30) return `${days}d ago`;
		if (days < 365) return `${Math.floor(days / 30)}mo ago`;
		return `${Math.floor(days / 365)}y ago`;
	}
</script>

<div class="shell">
	<header class="head">
		<div class="crumb font-mono">workspace / skills</div>
		<h1 class="title font-display">Skills</h1>
		<p class="tag">reusable capabilities you teach once and wire into any agent.</p>
	</header>

	<div class="body">
		<!-- ── Create + Import bar ────────────────────────────── -->
		<section class="section">
			<div class="section-head">
				<div class="section-title-row">
					<div class="section-icon">
						<Icon icon="oc:tool" width={14} height={14} />
					</div>
					<div>
						<h2 class="section-title font-mono">Your skills</h2>
						<p class="section-sub">
							each skill is a folder with <code class="code-mono">SKILL.md</code> and optional scripts,
							references, or assets — attached to agents from their settings.
						</p>
					</div>
				</div>
				<div class="head-actions">
					<button class="btn-ghost-link font-mono" type="button" onclick={openImport}>
						<Icon icon="tabler:cloud-download" width={12} height={12} />
						Import from ClawHub
					</button>
					<button class="btn-add font-mono" type="button" onclick={openCreate}>
						<Icon icon="oc:spawn" width={11} height={11} />
						New skill
					</button>
				</div>
			</div>

			<!-- ── Create form ────────────────────────────────── -->
			{#if createOpen}
				<form
					class="form-card"
					method="POST"
					action="?/create"
					use:enhance={() => {
						creating = true;
						return async ({ result, update }) => {
							creating = false;
							if (result.type === 'success') {
								createOpen = false;
								const id = (result.data as { createdId?: string } | undefined)?.createdId;
								if (id) {
									await goto(`/w/${workspaceId}/workspace/skills/${id}`);
									return;
								}
							}
							await update();
						};
					}}
				>
					<div class="field">
						<label class="lbl font-mono" for="new-name">NAME</label>
						<input
							id="new-name"
							class="inp font-mono"
							name="name"
							bind:value={createName}
							placeholder="my-skill"
							spellcheck="false"
							autocomplete="off"
							required
						/>
					</div>
					<div class="field">
						<label class="lbl font-mono" for="new-desc">DESCRIPTION</label>
						<input
							id="new-desc"
							class="inp font-mono"
							name="description"
							bind:value={createDescription}
							placeholder="What does this skill do?"
							autocomplete="off"
						/>
					</div>
					{#if form && 'error' in form && form.error}
						<p class="form-error font-mono">{form.error}</p>
					{/if}
					<div class="form-actions">
						<button class="btn-primary font-mono" type="submit" disabled={creating}>
							{#if creating}<span class="spinner"></span>creating…{:else}Create skill{/if}
						</button>
						<button class="btn-ghost font-mono" type="button" onclick={closeCreate}>Cancel</button>
					</div>
				</form>
			{/if}

			<!-- ── Import form ────────────────────────────────── -->
			{#if importOpen}
				<form
					class="form-card form-card--import"
					method="POST"
					action="?/importClawhub"
					use:enhance={() => {
						importing = true;
						return async ({ result, update }) => {
							importing = false;
							if (result.type === 'success') {
								importOpen = false;
								const id = (result.data as { importedId?: string } | undefined)?.importedId;
								if (id) {
									await goto(`/w/${workspaceId}/workspace/skills/${id}`);
									return;
								}
							}
							await update();
						};
					}}
				>
					<div class="field">
						<label class="lbl font-mono" for="clawhub-url">CLAWHUB URL</label>
						<input
							id="clawhub-url"
							class="inp font-mono"
							name="url"
							bind:value={importUrl}
							placeholder="https://clawhub.ai/steipete/trello"
							spellcheck="false"
							autocomplete="off"
							required
						/>
					</div>
					{#if form && 'importError' in form && form.importError}
						<p class="form-error font-mono">{form.importError}</p>
					{/if}
					<div class="form-actions">
						<button class="btn-primary font-mono" type="submit" disabled={importing}>
							{#if importing}<span class="spinner"></span>importing…{:else}Import{/if}
						</button>
						<button class="btn-ghost font-mono" type="button" onclick={closeImport}>Cancel</button>
					</div>
				</form>
			{/if}

			<!-- ── Grid ───────────────────────────────────────── -->
			{#if skills.length === 0 && !createOpen && !importOpen}
				<div class="empty">
					<Icon icon="oc:tool" width={28} height={28} />
					<p class="empty-title font-display"><em>no skills yet</em></p>
					<p class="empty-sub font-mono">
						create one from scratch, or import <em>steipete/trello</em> from ClawHub.
					</p>
				</div>
			{:else if skills.length > 0}
				<div class="grid">
					{#each skills as skill (skill.id)}
						<div class="card">
							<a
								class="card-body"
								href={`/w/${workspaceId}/workspace/skills/${skill.id}`}
								aria-label={`Open skill ${skill.name}`}
							>
								<div class="card-head">
									<div class="card-icon">
										{#if skill.emoji}
											<span class="card-emoji">{skill.emoji}</span>
										{:else}
											<Icon icon="oc:tool" width={14} height={14} />
										{/if}
									</div>
									<span class="card-name font-mono">{skill.name}</span>
									{#if skill.always}
										<span class="card-always font-mono" title="Always loaded into system prompt">always</span>
									{/if}
								</div>
								{#if skill.description}
									<p class="card-desc">{skill.description}</p>
								{:else}
									<p class="card-desc card-desc--muted font-mono">no description</p>
								{/if}
								<div class="card-meta font-mono">
									<span class="meta-item">
										<Icon icon="tabler:file" width={10} height={10} />
										{skill.fileCount} {skill.fileCount === 1 ? 'file' : 'files'}
									</span>
									<span class="meta-sep"></span>
									<span class="meta-item">
										<Icon icon="tabler:robot" width={10} height={10} />
										{skill.agentCount} {skill.agentCount === 1 ? 'agent' : 'agents'}
									</span>
									<span class="meta-sep"></span>
									<span class="meta-date">{formatDate(skill.createdAt)}</span>
								</div>
							</a>
							<form
								method="POST"
								action="?/delete"
								use:enhance={() => {
									deleting = true;
									return async ({ update }) => {
										deleting = false;
										deleteId = null;
										await update();
										await invalidateAll();
									};
								}}
							>
								<input type="hidden" name="skill_id" value={skill.id} />
								<button
									class="card-delete"
									type="button"
									onclick={() => (deleteId = deleteId === skill.id ? null : skill.id)}
									aria-label="Delete skill"
								>
									<Icon icon="tabler:trash" width={11} height={11} />
								</button>
								{#if deleteId === skill.id}
									<div class="confirm">
										<span class="confirm-text font-mono">
											delete <em>{skill.name}</em>?
											{#if skill.agentCount > 0}<br />
												<span class="confirm-warn"
													>will detach from {skill.agentCount}
													{skill.agentCount === 1 ? 'agent' : 'agents'}</span
												>
											{/if}
										</span>
										<div class="confirm-actions">
											<button class="confirm-yes font-mono" type="submit" disabled={deleting}>
												delete
											</button>
											<button
												class="confirm-no font-mono"
												type="button"
												onclick={() => (deleteId = null)}
											>
												cancel
											</button>
										</div>
									</div>
								{/if}
							</form>
						</div>
					{/each}
				</div>
			{/if}
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
	.head {
		padding: 1.75rem 3rem 2rem;
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

	.body {
		padding: 2rem 3rem 3rem;
		display: flex;
		flex-direction: column;
		gap: 2rem;
	}

	.section {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}
	.section-head {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 1.5rem;
	}
	.section-title-row {
		display: flex;
		gap: 0.75rem;
		align-items: flex-start;
	}
	.section-icon {
		width: 28px;
		height: 28px;
		border-radius: 0.4rem;
		background: color-mix(in oklch, var(--primary) 10%, var(--card));
		color: var(--primary);
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}
	.section-title {
		font-size: 0.72rem;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		margin-bottom: 0.15rem;
	}
	.section-sub {
		font-size: 0.75rem;
		color: var(--muted-foreground);
		max-width: 42ch;
	}
	.code-mono {
		font-family: inherit;
		background: var(--muted);
		padding: 0.05rem 0.3rem;
		border-radius: 0.2rem;
		font-size: 0.72rem;
	}

	.head-actions {
		display: flex;
		gap: 0.6rem;
		flex-shrink: 0;
	}
	.btn-add {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.45rem 0.8rem;
		font-size: 0.68rem;
		letter-spacing: 0.04em;
		border-radius: 0.3rem;
		border: 1px solid color-mix(in oklch, var(--primary) 40%, var(--border));
		color: var(--primary);
		background: color-mix(in oklch, var(--primary) 5%, transparent);
		transition: background 120ms ease, border-color 120ms ease;
	}
	.btn-add:hover {
		background: color-mix(in oklch, var(--primary) 15%, transparent);
		border-color: color-mix(in oklch, var(--primary) 60%, var(--border));
	}
	.btn-ghost-link {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.45rem 0.8rem;
		font-size: 0.68rem;
		letter-spacing: 0.04em;
		border-radius: 0.3rem;
		color: var(--muted-foreground);
		transition: color 120ms ease, background 120ms ease;
	}
	.btn-ghost-link:hover {
		color: var(--foreground);
		background: var(--muted);
	}

	.form-card {
		display: flex;
		flex-direction: column;
		gap: 0.85rem;
		padding: 1rem 1.15rem;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.45rem;
	}
	.form-card--import {
		border-left: 2px solid var(--primary);
	}
	.field {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}
	.lbl {
		font-size: 0.58rem;
		letter-spacing: 0.1em;
		color: var(--muted-foreground);
	}
	.inp {
		padding: 0.5rem 0.65rem;
		font-size: 0.8rem;
		background: var(--background);
		border: 1px solid var(--border);
		border-radius: 0.3rem;
		color: var(--foreground);
		transition: border-color 120ms ease;
	}
	.inp:focus {
		outline: none;
		border-color: var(--primary);
	}
	.form-error {
		font-size: 0.7rem;
		color: var(--destructive);
	}
	.form-actions {
		display: flex;
		gap: 0.5rem;
	}
	.btn-primary {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.5rem 0.9rem;
		font-size: 0.7rem;
		letter-spacing: 0.04em;
		border-radius: 0.3rem;
		background: var(--primary);
		color: var(--primary-foreground);
		border: 1px solid var(--primary);
	}
	.btn-primary:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}
	.btn-ghost {
		padding: 0.5rem 0.9rem;
		font-size: 0.7rem;
		letter-spacing: 0.04em;
		border-radius: 0.3rem;
		color: var(--muted-foreground);
		border: 1px solid transparent;
	}
	.btn-ghost:hover {
		background: var(--muted);
		color: var(--foreground);
	}
	.spinner {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		border: 1.5px solid currentColor;
		border-right-color: transparent;
		animation: spin 0.7s linear infinite;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.empty {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.75rem;
		padding: 3rem 2rem;
		color: var(--muted-foreground);
	}
	.empty-title {
		font-size: 1.5rem;
	}
	.empty-title em {
		color: var(--primary);
	}
	.empty-sub {
		font-size: 0.75rem;
		opacity: 0.7;
	}
	.empty-sub em {
		color: var(--foreground);
		font-style: italic;
	}

	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
		gap: 0.9rem;
	}

	.card {
		position: relative;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.5rem;
		transition: border-color 120ms ease, transform 120ms ease;
	}
	.card:hover {
		border-color: color-mix(in oklch, var(--primary) 30%, var(--border));
	}
	.card-body {
		display: flex;
		flex-direction: column;
		gap: 0.55rem;
		padding: 1rem 1.1rem;
		color: var(--foreground);
		text-decoration: none;
	}
	.card-head {
		display: flex;
		align-items: center;
		gap: 0.55rem;
	}
	.card-icon {
		width: 24px;
		height: 24px;
		border-radius: 0.3rem;
		background: color-mix(in oklch, var(--primary) 12%, transparent);
		color: var(--primary);
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}
	.card-name {
		font-size: 0.82rem;
		letter-spacing: 0.01em;
		color: var(--foreground);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		flex: 1;
	}
	.card-emoji {
		font-size: 0.95rem;
		line-height: 1;
	}
	.card-always {
		font-size: 0.55rem;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		padding: 0.15rem 0.4rem;
		border-radius: 0.2rem;
		background: color-mix(in oklch, var(--primary) 15%, transparent);
		color: var(--primary);
	}
	.card-desc {
		font-size: 0.75rem;
		color: var(--muted-foreground);
		line-height: 1.45;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
		min-height: 2.15rem;
	}
	.card-desc--muted {
		opacity: 0.5;
		font-style: italic;
	}
	.card-meta {
		display: flex;
		align-items: center;
		gap: 0.55rem;
		font-size: 0.62rem;
		color: var(--muted-foreground);
		letter-spacing: 0.04em;
	}
	.meta-item {
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}
	.meta-sep {
		width: 2px;
		height: 2px;
		border-radius: 50%;
		background: currentColor;
		opacity: 0.4;
	}
	.meta-date {
		opacity: 0.6;
	}

	.card-delete {
		position: absolute;
		top: 0.55rem;
		right: 0.55rem;
		width: 22px;
		height: 22px;
		border-radius: 0.25rem;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--muted-foreground);
		opacity: 0;
		transition: opacity 120ms ease, color 120ms ease, background 120ms ease;
	}
	.card:hover .card-delete {
		opacity: 0.65;
	}
	.card-delete:hover {
		opacity: 1;
		color: var(--destructive);
		background: color-mix(in oklch, var(--destructive) 12%, transparent);
	}

	.confirm {
		position: absolute;
		inset: 0;
		background: color-mix(in oklch, var(--card) 96%, var(--destructive));
		border: 1px solid var(--destructive);
		border-radius: 0.5rem;
		padding: 0.85rem 1rem;
		display: flex;
		flex-direction: column;
		justify-content: center;
		gap: 0.7rem;
	}
	.confirm-text {
		font-size: 0.72rem;
		line-height: 1.4;
	}
	.confirm-text em {
		color: var(--foreground);
		font-style: italic;
	}
	.confirm-warn {
		color: var(--destructive);
		font-size: 0.62rem;
	}
	.confirm-actions {
		display: flex;
		gap: 0.4rem;
	}
	.confirm-yes {
		padding: 0.3rem 0.7rem;
		font-size: 0.65rem;
		letter-spacing: 0.04em;
		border-radius: 0.25rem;
		background: var(--destructive);
		color: white;
	}
	.confirm-yes:disabled {
		opacity: 0.6;
	}
	.confirm-no {
		padding: 0.3rem 0.7rem;
		font-size: 0.65rem;
		letter-spacing: 0.04em;
		border-radius: 0.25rem;
		color: var(--muted-foreground);
	}
	.confirm-no:hover {
		color: var(--foreground);
	}
</style>
