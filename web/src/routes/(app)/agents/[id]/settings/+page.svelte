<script lang="ts">
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import AgentAvatar from '$lib/components/agent-avatar.svelte';
	import { Icon } from '$lib/icons';
	import { resolve } from '$app/paths';

	let { data, form } = $props();

	let nameValue = $derived(data.agent.name);
	let avatarOverride = $state<string | null>(null);
	const avatarPreview = $derived(avatarOverride ?? data.agent.avatarUrl ?? null);
	let avatarUploading = $state(false);
	let avatarFileInput = $state<HTMLInputElement | null>(null);
	let isDragging = $state(false);

	async function uploadFile(file: File) {
		avatarOverride = URL.createObjectURL(file);
		avatarUploading = true;
		const body = new FormData();
		body.append('avatar', file);
		await fetch(`?/uploadAvatar`, { method: 'POST', body });
		await invalidateAll();
		avatarOverride = null;
		avatarUploading = false;
	}

	async function handleAvatarChange(e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		await uploadFile(file);
	}

	async function handleDrop(e: DragEvent) {
		isDragging = false;
		const file = e.dataTransfer?.files?.[0];
		if (!file || !file.type.startsWith('image/')) return;
		await uploadFile(file);
	}
	let confirmDelete = $state(false);
	let saving = $state(false);
	let deleting = $state(false);

	// Pending connection operations keyed by "<action>:<id>"
	let pending = $state<Record<string, boolean>>({});
	// Per-operation error messages (used for channel 409)
	let opErrors = $state<Record<string, string>>({});

	function connEnhance(opKey: string) {
		return () => {
			pending = { ...pending, [opKey]: true };
			opErrors = Object.fromEntries(Object.entries(opErrors).filter(([k]) => k !== opKey));
			return async ({ result, update }: { result: { type: string; data?: Record<string, string> }; update: () => Promise<void> }) => {
				pending = Object.fromEntries(Object.entries(pending).filter(([k]) => k !== opKey));
				if (result.type === 'failure') {
					opErrors = { ...opErrors, [opKey]: result.data?.error ?? 'Error' };
				} else {
					await update();
				}
			};
		};
	}

	type Channel     = { id: string; type: string; createdAt: Date; attached: boolean; takenBy: string | null };
	type Skill       = { id: string; name: string; attached: boolean };
	type Env         = { id: string; name: string; category: string | null; attached: boolean };
	type LlmProvider = { id: string; name: string; attached: boolean };
	type Mcp         = { id: string; name: string; type: string; attached: boolean };

	const activeLlm = $derived(
		(data.llmProviders as LlmProvider[]).find((p) => p.attached) ?? null
	);
	let switchingLlm = $state(false);

	const CHANNEL_META: Record<string, { label: string; icon: string }> = {
		telegram:  { label: 'Telegram',  icon: 'tabler:brand-telegram' },
		discord:   { label: 'Discord',   icon: 'tabler:brand-discord'  },
		whatsapp:  { label: 'WhatsApp',  icon: 'tabler:brand-whatsapp' }
	};

	function fmtDate(d: Date) {
		return new Date(d).toLocaleDateString('en', { month: 'short', day: 'numeric' });
	}
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
			<AgentAvatar name={data.agent.name} isAdmin={data.agent.isAdmin} avatarUrl={data.agent.avatarUrl} size={28} />
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

					<div class="field">
						<span class="field-label font-mono">Avatar</span>
						<div class="avatar-zone-wrap">
							<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
							<div
								class="avatar-dropzone"
								class:uploading={avatarUploading}
								class:dragging={isDragging}
								role="button"
								tabindex="0"
								aria-label="Upload avatar"
								onclick={() => avatarFileInput?.click()}
								onkeydown={(e) => e.key === 'Enter' && avatarFileInput?.click()}
								ondragover={(e) => { e.preventDefault(); isDragging = true; }}
								ondragleave={() => { isDragging = false; }}
								ondrop={(e) => { e.preventDefault(); handleDrop(e); }}
							>
								<div class="avatar-dropzone-preview">
									{#if avatarPreview}
										<img src={avatarPreview} alt="avatar" class="avatar-dropzone-img" />
									{:else}
										<AgentAvatar name={data.agent.name} isAdmin={data.agent.isAdmin} size={88} />
									{/if}
								</div>
								<div class="avatar-dropzone-overlay">
									{#if avatarUploading}
										<div class="upload-spinner-ring"></div>
									{:else}
										<Icon icon="tabler:camera" width={18} height={18} />
										<span class="upload-hint font-mono">{isDragging ? 'drop here' : 'change'}</span>
									{/if}
								</div>
								<svg class="avatar-dropzone-ring" viewBox="0 0 100 100" aria-hidden="true">
									<circle cx="50" cy="50" r="47" />
								</svg>
							</div>
						</div>
						<p class="field-hint avatar-hint">JPG, PNG, WebP or GIF — drop or click to change.</p>
						<input
							bind:this={avatarFileInput}
							type="file"
							accept="image/jpeg,image/png,image/webp,image/gif"
							class="avatar-file-input"
							onchange={handleAvatarChange}
						/>
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
				</header>

				<!-- MCPs -->
				<div class="conn-block">
					<div class="conn-block-head">
						<Icon icon="tabler:plug" width={13} height={13} />
						<span class="conn-block-title font-mono">mcps</span>
						<span class="conn-block-count font-mono">{(data.mcps as Mcp[]).filter(m => m.attached).length}</span>
					</div>
					{#each (data.mcps as Mcp[]).filter(m => m.attached) as mcp (mcp.id)}
						<div class="conn-row">
							<span class="conn-row-name">{mcp.name}</span>
							<span class="conn-row-badge font-mono">{mcp.type}</span>
							{#if mcp.name === 'officeclaw' && data.agent.isAdmin}
								<span class="conn-lock" title="System — cannot be detached from Admin">
									<Icon icon="tabler:lock" width={11} height={11} />
								</span>
							{:else}
								<form method="POST" action="?/detachMcp" use:enhance={connEnhance(`detach:mcp:${mcp.id}`)}>
									<input type="hidden" name="mcp_id" value={mcp.id} />
									<button class="conn-detach" type="submit" disabled={!!pending[`detach:mcp:${mcp.id}`]} title="Detach">
										{#if pending[`detach:mcp:${mcp.id}`]}
											<span class="spinner spinner--sm"></span>
										{:else}
											<Icon icon="tabler:x" width={11} height={11} />
										{/if}
									</button>
								</form>
							{/if}
						</div>
					{/each}
					{#each (data.mcps as Mcp[]).filter(m => !m.attached && (data.agent.isAdmin || m.name !== 'officeclaw')) as mcp (mcp.id)}
						<form method="POST" action="?/attachMcp" use:enhance={connEnhance(`attach:mcp:${mcp.id}`)}>
							<input type="hidden" name="mcp_id" value={mcp.id} />
							<button class="conn-available" type="submit" disabled={!!pending[`attach:mcp:${mcp.id}`]}>
								<span class="conn-available-name">{mcp.name}</span>
								<span class="conn-row-badge font-mono">{mcp.type}</span>
								{#if pending[`attach:mcp:${mcp.id}`]}
									<span class="spinner spinner--sm"></span>
								{:else}
									<Icon icon="tabler:plus" width={11} height={11} class="conn-available-icon" />
								{/if}
							</button>
						</form>
					{/each}
					{#if (data.mcps as Mcp[]).length === 0}
						<p class="conn-empty font-mono">No MCP servers in workspace</p>
					{/if}
				</div>

				<!-- LLM Provider -->
				<div class="conn-block">
					<div class="conn-block-head">
						<Icon icon="tabler:brain" width={13} height={13} />
						<span class="conn-block-title font-mono">llm provider</span>
						{#if activeLlm}
							<span class="conn-block-count font-mono">{activeLlm.name}</span>
						{/if}
					</div>
					{#if (data.llmProviders as LlmProvider[]).length === 0}
						<p class="conn-empty font-mono">No LLM providers — add one in Workspace → Environments</p>
					{:else}
						{#each data.llmProviders as LlmProvider[] as provider (provider.id)}
							<form method="POST" action="?/switchLlm" use:enhance={connEnhance(`llm:${provider.id}`)}>
								<input type="hidden" name="env_id" value={provider.id} />
								<input type="hidden" name="old_env_id" value={activeLlm?.id ?? ''} />
								<button
									class="conn-available conn-llm-row"
									class:conn-llm-active={provider.attached}
									type="submit"
									disabled={provider.attached || !!pending[`llm:${provider.id}`]}
								>
									<span class="conn-llm-indicator" class:conn-llm-indicator--on={provider.attached}></span>
									<span class="conn-available-name">{provider.name}</span>
									{#if provider.attached}
										<span class="conn-row-badge font-mono">active</span>
									{:else if pending[`llm:${provider.id}`]}
										<span class="spinner spinner--sm"></span>
									{:else}
										<span class="conn-row-badge conn-row-badge--dim font-mono">switch</span>
									{/if}
								</button>
							</form>
						{/each}
					{/if}
				</div>

				<!-- Skills -->
				<div class="conn-block">
					<div class="conn-block-head">
						<Icon icon="tabler:bulb" width={13} height={13} />
						<span class="conn-block-title font-mono">skills</span>
						<span class="conn-block-count font-mono">{(data.skills as Skill[]).filter(s => s.attached).length}</span>
					</div>
					{#each (data.skills as Skill[]).filter(s => s.attached) as skill (skill.id)}
						<div class="conn-row">
							<span class="conn-row-name">{skill.name}</span>
							<form method="POST" action="?/detachSkill" use:enhance={connEnhance(`detach:skill:${skill.id}`)}>
								<input type="hidden" name="skill_id" value={skill.id} />
								<button class="conn-detach" type="submit" disabled={!!pending[`detach:skill:${skill.id}`]} title="Detach">
									{#if pending[`detach:skill:${skill.id}`]}
										<span class="spinner spinner--sm"></span>
									{:else}
										<Icon icon="tabler:x" width={11} height={11} />
									{/if}
								</button>
							</form>
						</div>
					{/each}
					{#each (data.skills as Skill[]).filter(s => !s.attached) as skill (skill.id)}
						<form method="POST" action="?/attachSkill" use:enhance={connEnhance(`attach:skill:${skill.id}`)}>
							<input type="hidden" name="skill_id" value={skill.id} />
							<button class="conn-available" type="submit" disabled={!!pending[`attach:skill:${skill.id}`]}>
								<span class="conn-available-name">{skill.name}</span>
								{#if pending[`attach:skill:${skill.id}`]}
									<span class="spinner spinner--sm"></span>
								{:else}
									<Icon icon="tabler:plus" width={11} height={11} class="conn-available-icon" />
								{/if}
							</button>
						</form>
					{/each}
					{#if (data.skills as Skill[]).length === 0}
						<p class="conn-empty font-mono">No skills in workspace</p>
					{/if}
				</div>

				<!-- Env vars -->
				<div class="conn-block">
					<div class="conn-block-head">
						<Icon icon="tabler:key" width={13} height={13} />
						<span class="conn-block-title font-mono">env vars</span>
						<span class="conn-block-count font-mono">{(data.envs as Env[]).filter(e => e.attached).length}</span>
					</div>
					{#each (data.envs as Env[]).filter(e => e.attached) as env (env.id)}
						<div class="conn-row">
							<span class="conn-row-name">{env.name}</span>
							{#if env.name === 'officeclaw' && data.agent.isAdmin}
								<span class="conn-lock" title="System — cannot be detached from Admin">
									<Icon icon="tabler:lock" width={11} height={11} />
								</span>
							{:else}
								<form method="POST" action="?/detachEnv" use:enhance={connEnhance(`detach:env:${env.id}`)}>
									<input type="hidden" name="env_id" value={env.id} />
									<button class="conn-detach" type="submit" disabled={!!pending[`detach:env:${env.id}`]} title="Detach">
										{#if pending[`detach:env:${env.id}`]}
											<span class="spinner spinner--sm"></span>
										{:else}
											<Icon icon="tabler:x" width={11} height={11} />
										{/if}
									</button>
								</form>
							{/if}
						</div>
					{/each}
					{#each (data.envs as Env[]).filter(e => !e.attached && (data.agent.isAdmin || e.name !== 'officeclaw')) as env (env.id)}
						<form method="POST" action="?/attachEnv" use:enhance={connEnhance(`attach:env:${env.id}`)}>
							<input type="hidden" name="env_id" value={env.id} />
							<button class="conn-available" type="submit" disabled={!!pending[`attach:env:${env.id}`]}>
								<span class="conn-available-name">{env.name}</span>
								{#if pending[`attach:env:${env.id}`]}
									<span class="spinner spinner--sm"></span>
								{:else}
									<Icon icon="tabler:plus" width={11} height={11} class="conn-available-icon" />
								{/if}
							</button>
						</form>
					{/each}
					{#if (data.envs as Env[]).length === 0}
						<p class="conn-empty font-mono">No env var sets in workspace</p>
					{/if}
				</div>

				<!-- Channels -->
				<div class="conn-block">
					<div class="conn-block-head">
						<Icon icon="tabler:message" width={13} height={13} />
						<span class="conn-block-title font-mono">channels</span>
						<span class="conn-block-count font-mono">{(data.channels as Channel[]).filter(c => c.attached).length}</span>
					</div>
					{#each (data.channels as Channel[]).filter(c => c.attached) as ch (ch.id)}
						{@const meta = CHANNEL_META[ch.type] ?? { label: ch.type, icon: 'tabler:message' }}
						<div class="conn-row">
							<Icon icon={meta.icon} width={13} height={13} class="conn-channel-icon" />
							<span class="conn-row-name">{meta.label}</span>
							<span class="conn-row-muted font-mono">{fmtDate(ch.createdAt)}</span>
							<form method="POST" action="?/detachChannel" use:enhance={connEnhance(`detach:ch:${ch.id}`)}>
								<input type="hidden" name="channel_id" value={ch.id} />
								<button class="conn-detach" type="submit" disabled={!!pending[`detach:ch:${ch.id}`]} title="Detach">
									{#if pending[`detach:ch:${ch.id}`]}
										<span class="spinner spinner--sm"></span>
									{:else}
										<Icon icon="tabler:x" width={11} height={11} />
									{/if}
								</button>
							</form>
						</div>
					{/each}
					{#each (data.channels as Channel[]).filter(c => !c.attached && !c.takenBy) as ch (ch.id)}
						{@const meta = CHANNEL_META[ch.type] ?? { label: ch.type, icon: 'tabler:message' }}
						{@const opKey = `attach:ch:${ch.id}`}
						<form method="POST" action="?/attachChannel" use:enhance={connEnhance(opKey)}>
							<input type="hidden" name="channel_id" value={ch.id} />
							<button class="conn-available" type="submit" disabled={!!pending[opKey]}>
								<Icon icon={meta.icon} width={13} height={13} class="conn-channel-icon" />
								<span class="conn-available-name">{meta.label}</span>
								<span class="conn-row-muted font-mono">{fmtDate(ch.createdAt)}</span>
								{#if pending[opKey]}
									<span class="spinner spinner--sm"></span>
								{:else}
									<Icon icon="tabler:plus" width={11} height={11} class="conn-available-icon" />
								{/if}
							</button>
							{#if opErrors[opKey]}
								<p class="conn-error font-mono">{opErrors[opKey]}</p>
							{/if}
						</form>
					{/each}
					{#each (data.channels as Channel[]).filter(c => c.takenBy) as ch (ch.id)}
						{@const meta = CHANNEL_META[ch.type] ?? { label: ch.type, icon: 'tabler:message' }}
						<div class="conn-row conn-row--taken">
							<Icon icon={meta.icon} width={13} height={13} class="conn-channel-icon" />
							<span class="conn-row-name">{meta.label}</span>
							<span class="conn-row-muted font-mono">{fmtDate(ch.createdAt)}</span>
							<span class="conn-taken-label font-mono">→ {ch.takenBy}</span>
						</div>
					{/each}
					{#if (data.channels as Channel[]).length === 0}
						<p class="conn-empty font-mono">No channels in workspace</p>
					{/if}
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

	/* ── Connections ──────────────────────────────────────── */
	.conn-block {
		display: flex;
		flex-direction: column;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.35rem;
		overflow: hidden;
	}

	.conn-block-head {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.55rem 0.85rem;
		background: color-mix(in oklch, var(--muted) 40%, transparent);
		border-bottom: 1px solid var(--border);
		color: var(--muted-foreground);
	}

	.conn-block-title {
		flex: 1;
		font-size: 0.6rem;
		text-transform: uppercase;
		letter-spacing: 0.14em;
	}

	.conn-block-count {
		font-size: 0.65rem;
		color: var(--muted-foreground);
		opacity: 0.7;
	}

	/* Attached item row */
	.conn-row {
		display: flex;
		align-items: center;
		gap: 0.55rem;
		padding: 0.5rem 0.85rem;
		border-bottom: 1px solid var(--border);
	}

	.conn-row:last-child {
		border-bottom: none;
	}

	.conn-row--taken {
		opacity: 0.45;
	}

	.conn-row-name {
		flex: 1;
		font-size: 0.82rem;
		color: var(--foreground);
	}

	.conn-row-badge {
		font-size: 0.58rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--muted-foreground);
		background: var(--muted);
		padding: 0.1rem 0.35rem;
		border-radius: 2px;
	}

	.conn-row-muted {
		font-size: 0.62rem;
		color: var(--muted-foreground);
		opacity: 0.6;
	}

	.conn-taken-label {
		font-size: 0.62rem;
		color: var(--muted-foreground);
		opacity: 0.6;
		margin-left: auto;
	}

	/* System lock indicator */
	.conn-lock {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 20px;
		height: 20px;
		color: var(--muted-foreground);
		opacity: 0.35;
		flex-shrink: 0;
	}

	/* Detach button */
	.conn-detach {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 20px;
		height: 20px;
		border-radius: 0.2rem;
		color: var(--muted-foreground);
		transition:
			color 120ms ease,
			background 120ms ease;
		flex-shrink: 0;
	}

	.conn-detach:hover:not(:disabled) {
		color: var(--destructive);
		background: color-mix(in oklch, var(--destructive) 10%, transparent);
	}

	.conn-detach:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	/* Available item (attach button styled as a row) */
	.conn-available {
		display: flex;
		align-items: center;
		gap: 0.55rem;
		width: 100%;
		padding: 0.5rem 0.85rem;
		border-bottom: 1px solid var(--border);
		color: var(--muted-foreground);
		text-align: left;
		transition:
			background 120ms ease,
			color 120ms ease;
	}

	.conn-available:last-of-type {
		border-bottom: none;
	}

	.conn-available:hover:not(:disabled) {
		background: color-mix(in oklch, var(--primary) 6%, transparent);
		color: var(--foreground);
	}

	.conn-available:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.conn-available-name {
		flex: 1;
		font-size: 0.82rem;
	}

	:global(.conn-available-icon) {
		opacity: 0.5;
		flex-shrink: 0;
	}

	:global(.conn-channel-icon) {
		flex-shrink: 0;
		color: var(--muted-foreground);
	}

	/* LLM provider row */
	.conn-llm-row {
		cursor: pointer;
	}
	.conn-llm-active {
		background: color-mix(in oklch, var(--primary) 6%, transparent);
		color: var(--foreground);
		cursor: default;
	}
	.conn-llm-indicator {
		width: 7px;
		height: 7px;
		border-radius: 9999px;
		background: color-mix(in oklch, var(--muted-foreground) 40%, transparent);
		flex-shrink: 0;
		transition: background 150ms ease;
	}
	.conn-llm-indicator--on {
		background: color-mix(in oklch, var(--primary) 80%, transparent);
		box-shadow: 0 0 5px color-mix(in oklch, var(--primary) 40%, transparent);
	}
	.conn-row-badge--dim {
		opacity: 0.45;
	}

	.conn-empty {
		padding: 0.75rem 0.85rem;
		font-size: 0.65rem;
		color: var(--muted-foreground);
		opacity: 0.5;
		letter-spacing: 0.04em;
	}

	.conn-error {
		padding: 0.3rem 0.85rem;
		font-size: 0.62rem;
		color: var(--destructive);
		letter-spacing: 0.02em;
		border-top: 1px solid color-mix(in oklch, var(--destructive) 20%, transparent);
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

	.spinner--sm {
		width: 9px;
		height: 9px;
		border-width: 1.5px;
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

	/* ── Avatar dropzone ──────────────────────────────────── */
	.avatar-zone-wrap {
		display: flex;
		justify-content: flex-start;
		padding: 0.25rem 0;
	}

	.avatar-dropzone {
		position: relative;
		width: 96px;
		height: 96px;
		border-radius: 9999px;
		cursor: pointer;
		outline: none;
		-webkit-user-select: none;
		user-select: none;
	}

	/* inner image/avatar area — inset 4px to leave room for the SVG ring */
	.avatar-dropzone-preview {
		position: absolute;
		inset: 4px;
		border-radius: 9999px;
		overflow: hidden;
		background: var(--card);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.avatar-dropzone-img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	/* SVG ring */
	.avatar-dropzone-ring {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		pointer-events: none;
		overflow: visible;
	}

	.avatar-dropzone-ring circle {
		fill: none;
		stroke: var(--border);
		stroke-width: 1.5;
		/* circumference ≈ 295 for r=47 */
		stroke-dasharray: 6 5;
		transition:
			stroke 220ms ease,
			stroke-dasharray 300ms ease,
			stroke-width 220ms ease;
	}

	.avatar-dropzone:hover .avatar-dropzone-ring circle,
	.avatar-dropzone:focus-visible .avatar-dropzone-ring circle {
		stroke: color-mix(in oklch, var(--primary) 75%, var(--border));
		stroke-dasharray: 295 0;
		stroke-width: 1.5;
	}

	.avatar-dropzone.dragging .avatar-dropzone-ring circle {
		stroke: var(--primary);
		stroke-dasharray: 295 0;
		stroke-width: 2;
	}

	.avatar-dropzone.uploading .avatar-dropzone-ring circle {
		stroke: var(--primary);
		stroke-dasharray: 148 147;
		stroke-width: 1.5;
		animation: ring-orbit 1.1s linear infinite;
	}

	@keyframes ring-orbit {
		to { stroke-dashoffset: -295; }
	}

	/* hover / drag / uploading overlay */
	.avatar-dropzone-overlay {
		position: absolute;
		inset: 4px;
		border-radius: 9999px;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.28rem;
		color: transparent;
		background: oklch(0 0 0 / 0);
		transition:
			background 200ms ease,
			color 200ms ease;
		pointer-events: none;
	}

	.avatar-dropzone:hover .avatar-dropzone-overlay,
	.avatar-dropzone:focus-visible .avatar-dropzone-overlay,
	.avatar-dropzone.dragging .avatar-dropzone-overlay,
	.avatar-dropzone.uploading .avatar-dropzone-overlay {
		background: oklch(0 0 0 / 0.52);
		color: oklch(1 0 0 / 0.9);
	}

	.upload-hint {
		font-size: 0.5rem;
		text-transform: uppercase;
		letter-spacing: 0.14em;
		line-height: 1;
	}

	.upload-spinner-ring {
		width: 22px;
		height: 22px;
		border-radius: 9999px;
		border: 2px solid oklch(1 0 0 / 0.25);
		border-top-color: oklch(1 0 0 / 0.9);
		animation: spin 0.75s linear infinite;
	}

	.avatar-hint {
		margin-top: 0.15rem;
	}

	.avatar-file-input {
		display: none;
	}
</style>
