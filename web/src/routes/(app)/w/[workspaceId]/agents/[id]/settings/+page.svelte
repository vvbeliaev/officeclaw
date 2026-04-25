<script lang="ts">
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import AgentAvatar from '$lib/components/agent-avatar.svelte';
	import { Icon } from '$lib/icons';

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
	type Skill       = {
		id: string;
		name: string;
		attached: boolean;
		requiredEnvs: string[];
		missingEnvs: string[];
		requiredBins: string[];
	};
	type Env         = { id: string; name: string; category: string | null; attached: boolean };
	type LlmProvider = { id: string; name: string; attached: boolean };
	type Mcp         = { id: string; name: string; type: string; attached: boolean };
	type Template    = { id: string; name: string; templateType: string; attached: boolean };
	type Cron        = {
		id: string;
		name: string;
		scheduleKind: 'at' | 'every' | 'cron';
		scheduleEveryMs: number | null;
		scheduleExpr: string | null;
		scheduleTz: string | null;
		attached: boolean;
		enabled: boolean;
		lastStatus: 'ok' | 'error' | 'skipped' | null;
		lastRunAtMs: number | null;
		nextRunAtMs: number | null;
	};

	const activeLlm = $derived(
		(data.llmProviders as LlmProvider[]).find((p) => p.attached) ?? null
	);

	const CHANNEL_META: Record<string, { label: string; icon: string }> = {
		telegram:  { label: 'Telegram',  icon: 'tabler:brand-telegram' },
		discord:   { label: 'Discord',   icon: 'tabler:brand-discord'  },
		whatsapp:  { label: 'WhatsApp',  icon: 'tabler:brand-whatsapp' }
	};

	function fmtDate(d: Date) {
		return new Date(d).toLocaleDateString('en', { month: 'short', day: 'numeric' });
	}

	function cronSummary(c: {
		scheduleKind: 'at' | 'every' | 'cron';
		scheduleEveryMs: number | null;
		scheduleExpr: string | null;
	}): string {
		if (c.scheduleKind === 'cron') return c.scheduleExpr ?? 'cron';
		if (c.scheduleKind === 'every' && c.scheduleEveryMs) {
			const s = Math.round(c.scheduleEveryMs / 1000);
			if (s < 60) return `${s}s`;
			const m = Math.round(s / 60);
			if (m < 60) return `${m}m`;
			const h = Math.round(m / 60);
			if (h < 24) return `${h}h`;
			return `${Math.round(h / 24)}d`;
		}
		return 'one-shot';
	}
</script>

<div class="settings-shell">
	<!-- ── Header ──────────────────────────────────────────────── -->
	<header class="settings-header">
		<div class="header-left">
			<a href={`/w/${data.workspace.id}/agents/${data.agent.id}`} class="back-btn" aria-label="Back to chat">
				<Icon icon="tabler:arrow-left" width={13} height={13} />
				<span>back</span>
			</a>
			<div class="header-divider"></div>
			<span class="header-crumb font-mono">settings</span>
		</div>
		<div class="header-agent">
			<AgentAvatar name={data.agent.name} isAdmin={data.agent.isAdmin} avatarUrl={data.agent.avatarUrl} size={18} />
			<span class="header-agent-name font-display">{data.agent.name}</span>
		</div>
	</header>

	<!-- ── Two-panel body ──────────────────────────────────────── -->
	<div class="settings-body">

		<!-- ── LEFT: Identity panel ──────────────────────────── -->
		<aside class="identity-panel">

			<!-- Avatar dropzone -->
			<div class="id-avatar-wrap">
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
					<div class="avatar-preview">
						{#if avatarPreview}
							<img src={avatarPreview} alt="avatar" class="avatar-img" />
						{:else}
							<AgentAvatar name={data.agent.name} isAdmin={data.agent.isAdmin} size={80} />
						{/if}
					</div>
					<div class="avatar-overlay">
						{#if avatarUploading}
							<span class="upload-spinner"></span>
						{:else}
							<Icon icon="tabler:camera" width={15} height={15} />
							<span class="font-mono">{isDragging ? 'drop' : 'edit'}</span>
						{/if}
					</div>
				</div>
				<input
					bind:this={avatarFileInput}
					type="file"
					accept="image/jpeg,image/png,image/webp,image/gif"
					class="avatar-file-input"
					onchange={handleAvatarChange}
				/>
				{#if data.agent.isAdmin}
					<span class="admin-badge font-mono">admin</span>
				{/if}
			</div>

			<!-- Name form -->
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
				class="id-name-form"
			>
				<div class="id-name-row" class:focused={false}>
					<input
						id="agent-name"
						name="name"
						type="text"
						class="id-name-input font-display"
						bind:value={nameValue}
						maxlength={64}
						required
						placeholder="Agent name"
					/>
					<button class="btn-save font-mono" type="submit" disabled={saving}>
						{#if saving}<span class="spinner"></span>{:else}save{/if}
					</button>
				</div>
				{#if form?.error}
					<p class="id-feedback id-feedback--err font-mono">{form.error}</p>
				{/if}
				{#if form?.success}
					<p class="id-feedback id-feedback--ok font-mono">saved</p>
				{/if}
			</form>

			<!-- Runtime info -->
			<div class="id-block">
				<p class="id-block-label font-mono">runtime</p>
				<div class="runtime-row">
					<span class="runtime-key font-mono">image</span>
					<span class="runtime-val font-mono">{data.agent.image}</span>
				</div>
			</div>

			<!-- Behaviour — nanobot-level knobs on the agent itself -->
			<div class="id-block">
				<p class="id-block-label font-mono">behaviour</p>
				<form
					method="POST"
					action="?/toggleSkillEvolution"
					use:enhance={connEnhance('skill-evolution')}
					class="toggle-row"
				>
					<input
						type="hidden"
						name="enabled"
						value={data.agent.skillEvolution ? 'false' : 'true'}
					/>
					<div class="toggle-copy">
						<span class="toggle-title font-mono">skill evolution</span>
						<span class="toggle-sub">
							Auto-crystallise reusable skills from qualifying runs.
						</span>
					</div>
					<button
						class="toggle-switch"
						class:toggle-switch--on={data.agent.skillEvolution}
						type="submit"
						aria-pressed={data.agent.skillEvolution}
						aria-label="Toggle skill evolution"
						disabled={!!pending['skill-evolution']}
					>
						<span class="toggle-knob"></span>
					</button>
				</form>

				<form
					method="POST"
					action="?/toggleHeartbeat"
					use:enhance={connEnhance('heartbeat-toggle')}
					class="toggle-row"
				>
					<input
						type="hidden"
						name="enabled"
						value={data.agent.heartbeatEnabled ? 'false' : 'true'}
					/>
					<div class="toggle-copy">
						<span class="toggle-title font-mono">heartbeat</span>
						<span class="toggle-sub">
							Periodic wake-up. Checks <span class="inline-code">HEARTBEAT.md</span> and runs pending tasks.
						</span>
					</div>
					<button
						class="toggle-switch"
						class:toggle-switch--on={data.agent.heartbeatEnabled}
						type="submit"
						aria-pressed={data.agent.heartbeatEnabled}
						aria-label="Toggle heartbeat"
						disabled={!!pending['heartbeat-toggle']}
					>
						<span class="toggle-knob"></span>
					</button>
				</form>

				{#if data.agent.heartbeatEnabled}
					<form
						method="POST"
						action="?/saveHeartbeatInterval"
						use:enhance={connEnhance('heartbeat-interval')}
						class="hb-interval-row"
					>
						<label class="hb-label font-mono" for="hb-interval">interval</label>
						<input
							id="hb-interval"
							class="hb-input font-mono"
							type="number"
							name="interval_s"
							min="60"
							max="86400"
							step="30"
							value={data.agent.heartbeatIntervalS}
						/>
						<span class="hb-unit font-mono">sec</span>
						<button
							class="btn-field-save font-mono"
							type="submit"
							disabled={!!pending['heartbeat-interval']}
						>save</button>
					</form>
					{#if form?.hbError}
						<p class="id-feedback id-feedback--err font-mono">{form.hbError}</p>
					{:else if form?.hbSuccess}
						<p class="id-feedback id-feedback--ok font-mono">saved</p>
					{/if}
				{/if}
			</div>

			<!-- Danger zone -->
			{#if !data.agent.isAdmin}
				<div class="id-block id-block--danger">
					<p class="id-block-label id-block-label--danger font-mono">danger zone</p>
					{#if !confirmDelete}
						<button class="btn-danger font-mono" type="button" onclick={() => (confirmDelete = true)}>
							<Icon icon="tabler:trash" width={11} height={11} />
							Delete agent
						</button>
					{:else}
						<p class="danger-confirm font-mono">
							Delete <strong>{data.agent.name}</strong>? Cannot be undone.
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
							<button class="btn-danger font-mono" type="submit" disabled={deleting}>
								{#if deleting}
									<span class="spinner spinner--danger"></span>
								{:else}
									<Icon icon="tabler:trash" width={11} height={11} />
								{/if}
								Confirm
							</button>
							<button class="btn-ghost font-mono" type="button" onclick={() => (confirmDelete = false)}>
								Cancel
							</button>
						</form>
					{/if}
				</div>
			{/if}
		</aside>

		<!-- ── RIGHT: Capabilities panel ────────────────────── -->
		<div class="cap-panel">
			<p class="cap-panel-eyebrow font-mono">capabilities</p>

			<!-- LLM Provider ─ single-select row -->
			<div class="cap-section">
				<div class="cap-head">
					<Icon icon="tabler:brain" width={12} height={12} class="cap-head-icon" />
					<span class="cap-label font-mono">llm provider</span>
					{#if activeLlm}
						<span class="cap-meta cap-meta--active font-mono">{activeLlm.name}</span>
					{:else}
						<span class="cap-meta font-mono">none</span>
					{/if}
				</div>
				{#if (data.llmProviders as LlmProvider[]).length === 0}
					<p class="cap-empty font-mono">No LLM providers — add one in Environments</p>
				{:else}
					<div class="llm-row">
						{#each data.llmProviders as LlmProvider[] as provider (provider.id)}
							<form method="POST" action="?/switchLlm" use:enhance={connEnhance(`llm:${provider.id}`)} style="display:contents">
								<input type="hidden" name="env_id" value={provider.id} />
								<input type="hidden" name="old_env_id" value={activeLlm?.id ?? ''} />
								<button
									class="llm-pill font-mono"
									class:llm-pill--active={provider.attached}
									type="submit"
									disabled={provider.attached || !!pending[`llm:${provider.id}`]}
								>
									<span class="llm-dot" class:llm-dot--on={provider.attached}></span>
									{provider.name}
									{#if pending[`llm:${provider.id}`]}
										<span class="spinner spinner--sm"></span>
									{/if}
								</button>
							</form>
						{/each}
					</div>
				{/if}
			</div>

			<!-- MCP Servers -->
			<div class="cap-section">
				<div class="cap-head">
					<Icon icon="tabler:plug" width={12} height={12} class="cap-head-icon" />
					<span class="cap-label font-mono">mcp servers</span>
					<span class="cap-meta font-mono">{(data.mcps as Mcp[]).filter(m => m.attached).length} / {(data.mcps as Mcp[]).length}</span>
				</div>
				{#if (data.mcps as Mcp[]).length === 0}
					<p class="cap-empty font-mono">No MCP servers in workspace</p>
				{:else}
					<div class="chip-grid">
						{#each (data.mcps as Mcp[]).filter(m => m.attached) as mcp (mcp.id)}
							<div class="chip chip--on">
								<span class="chip-name">{mcp.name}</span>
								<span class="chip-tag font-mono">{mcp.type}</span>
								{#if mcp.name === 'officeclaw' && data.agent.isAdmin}
									<span class="chip-lock"><Icon icon="tabler:lock" width={9} height={9} /></span>
								{:else}
									<form method="POST" action="?/detachMcp" use:enhance={connEnhance(`detach:mcp:${mcp.id}`)} style="display:contents">
										<input type="hidden" name="mcp_id" value={mcp.id} />
										<button class="chip-x" type="submit" disabled={!!pending[`detach:mcp:${mcp.id}`]} title="Detach">
											{#if pending[`detach:mcp:${mcp.id}`]}<span class="spinner spinner--xs"></span>{:else}<Icon icon="tabler:x" width={9} height={9} />{/if}
										</button>
									</form>
								{/if}
							</div>
						{/each}
						{#each (data.mcps as Mcp[]).filter(m => !m.attached && (data.agent.isAdmin || m.name !== 'officeclaw')) as mcp (mcp.id)}
							<form method="POST" action="?/attachMcp" use:enhance={connEnhance(`attach:mcp:${mcp.id}`)} style="display:contents">
								<input type="hidden" name="mcp_id" value={mcp.id} />
								<button class="chip chip--off" type="submit" disabled={!!pending[`attach:mcp:${mcp.id}`]}>
									<span class="chip-name">{mcp.name}</span>
									<span class="chip-tag font-mono">{mcp.type}</span>
									{#if pending[`attach:mcp:${mcp.id}`]}<span class="spinner spinner--xs"></span>{:else}<Icon icon="tabler:plus" width={9} height={9} class="chip-plus" />{/if}
								</button>
							</form>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Skills -->
			<div class="cap-section">
				<div class="cap-head">
					<Icon icon="tabler:bulb" width={12} height={12} class="cap-head-icon" />
					<span class="cap-label font-mono">skills</span>
					<span class="cap-meta font-mono">{(data.skills as Skill[]).filter(s => s.attached).length} / {(data.skills as Skill[]).length}</span>
				</div>
				{#if (data.skills as Skill[]).length === 0}
					<p class="cap-empty font-mono">No skills in workspace</p>
				{:else}
					<div class="chip-grid">
						{#each (data.skills as Skill[]).filter(s => s.attached) as skill (skill.id)}
							{@const needsCount = skill.missingEnvs.length}
							<div class="skill-block">
								<div class="chip chip--on" class:chip--warn={needsCount > 0}>
									<span class="chip-name">{skill.name}</span>
									{#if needsCount > 0}
										<span class="chip-warn-badge font-mono" title="Missing requirements">
											<Icon icon="tabler:alert-triangle" width={9} height={9} />
											{needsCount} need{needsCount === 1 ? '' : 's'}
										</span>
									{/if}
									<form method="POST" action="?/detachSkill" use:enhance={connEnhance(`detach:skill:${skill.id}`)} style="display:contents">
										<input type="hidden" name="skill_id" value={skill.id} />
										<button class="chip-x" type="submit" disabled={!!pending[`detach:skill:${skill.id}`]} title="Detach">
											{#if pending[`detach:skill:${skill.id}`]}<span class="spinner spinner--xs"></span>{:else}<Icon icon="tabler:x" width={9} height={9} />{/if}
										</button>
									</form>
								</div>
								{#if needsCount > 0}
									<ul class="needs-list font-mono">
										{#each skill.missingEnvs as key (key)}
											<li class="needs-row">
												<Icon icon="tabler:key" width={9} height={9} class="needs-icon" />
												<span class="needs-key">{key}</span>
												<a
													class="needs-cta"
													href={`/w/${data.workspace.id}/workspace/environments?addKey=${encodeURIComponent(key)}`}
												>
													<Icon icon="tabler:plus" width={9} height={9} /> add
												</a>
											</li>
										{/each}
									</ul>
								{/if}
								{#if skill.requiredBins.length > 0}
									<p class="needs-note font-mono">
										<Icon icon="tabler:terminal-2" width={9} height={9} />
										needs bin: {skill.requiredBins.join(', ')}
									</p>
								{/if}
							</div>
						{/each}
						{#each (data.skills as Skill[]).filter(s => !s.attached) as skill (skill.id)}
							<form method="POST" action="?/attachSkill" use:enhance={connEnhance(`attach:skill:${skill.id}`)} style="display:contents">
								<input type="hidden" name="skill_id" value={skill.id} />
								<button class="chip chip--off" type="submit" disabled={!!pending[`attach:skill:${skill.id}`]}>
									<span class="chip-name">{skill.name}</span>
									{#if pending[`attach:skill:${skill.id}`]}<span class="spinner spinner--xs"></span>{:else}<Icon icon="tabler:plus" width={9} height={9} class="chip-plus" />{/if}
								</button>
							</form>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Env Vars -->
			<div class="cap-section">
				<div class="cap-head">
					<Icon icon="tabler:key" width={12} height={12} class="cap-head-icon" />
					<span class="cap-label font-mono">env vars</span>
					<span class="cap-meta font-mono">{(data.envs as Env[]).filter(e => e.attached).length} / {(data.envs as Env[]).length}</span>
				</div>
				{#if (data.envs as Env[]).length === 0}
					<p class="cap-empty font-mono">No env var sets in workspace</p>
				{:else}
					<div class="chip-grid">
						{#each (data.envs as Env[]).filter(e => e.attached) as env (env.id)}
							<div class="chip chip--on">
								<span class="chip-name">{env.name}</span>
								<form method="POST" action="?/detachEnv" use:enhance={connEnhance(`detach:env:${env.id}`)} style="display:contents">
									<input type="hidden" name="env_id" value={env.id} />
									<button class="chip-x" type="submit" disabled={!!pending[`detach:env:${env.id}`]} title="Detach">
										{#if pending[`detach:env:${env.id}`]}<span class="spinner spinner--xs"></span>{:else}<Icon icon="tabler:x" width={9} height={9} />{/if}
									</button>
								</form>
							</div>
						{/each}
						{#each (data.envs as Env[]).filter(e => !e.attached) as env (env.id)}
							<form method="POST" action="?/attachEnv" use:enhance={connEnhance(`attach:env:${env.id}`)} style="display:contents">
								<input type="hidden" name="env_id" value={env.id} />
								<button class="chip chip--off" type="submit" disabled={!!pending[`attach:env:${env.id}`]}>
									<span class="chip-name">{env.name}</span>
									{#if pending[`attach:env:${env.id}`]}<span class="spinner spinner--xs"></span>{:else}<Icon icon="tabler:plus" width={9} height={9} class="chip-plus" />{/if}
								</button>
							</form>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Channels -->
			<div class="cap-section">
				<div class="cap-head">
					<Icon icon="tabler:message" width={12} height={12} class="cap-head-icon" />
					<span class="cap-label font-mono">channels</span>
					<span class="cap-meta font-mono">{(data.channels as Channel[]).filter(c => c.attached).length} / {(data.channels as Channel[]).length}</span>
				</div>
				{#if (data.channels as Channel[]).length === 0}
					<p class="cap-empty font-mono">No channels in workspace</p>
				{:else}
					<div class="chip-grid">
						{#each (data.channels as Channel[]).filter(c => c.attached) as ch (ch.id)}
							{@const meta = CHANNEL_META[ch.type] ?? { label: ch.type, icon: 'tabler:message' }}
							<div class="chip chip--on">
								<Icon icon={meta.icon} width={11} height={11} />
								<span class="chip-name">{meta.label}</span>
								<span class="chip-date font-mono">{fmtDate(ch.createdAt)}</span>
								<form method="POST" action="?/detachChannel" use:enhance={connEnhance(`detach:ch:${ch.id}`)} style="display:contents">
									<input type="hidden" name="channel_id" value={ch.id} />
									<button class="chip-x" type="submit" disabled={!!pending[`detach:ch:${ch.id}`]} title="Detach">
										{#if pending[`detach:ch:${ch.id}`]}<span class="spinner spinner--xs"></span>{:else}<Icon icon="tabler:x" width={9} height={9} />{/if}
									</button>
								</form>
							</div>
						{/each}
						{#each (data.channels as Channel[]).filter(c => !c.attached && !c.takenBy) as ch (ch.id)}
							{@const meta = CHANNEL_META[ch.type] ?? { label: ch.type, icon: 'tabler:message' }}
							{@const opKey = `attach:ch:${ch.id}`}
							<div class="chip-with-err">
								<form method="POST" action="?/attachChannel" use:enhance={connEnhance(opKey)} style="display:contents">
									<input type="hidden" name="channel_id" value={ch.id} />
									<button class="chip chip--off" type="submit" disabled={!!pending[opKey]}>
										<Icon icon={meta.icon} width={11} height={11} />
										<span class="chip-name">{meta.label}</span>
										<span class="chip-date font-mono">{fmtDate(ch.createdAt)}</span>
										{#if pending[opKey]}<span class="spinner spinner--xs"></span>{:else}<Icon icon="tabler:plus" width={9} height={9} class="chip-plus" />{/if}
									</button>
								</form>
								{#if opErrors[opKey]}
									<p class="chip-err font-mono">{opErrors[opKey]}</p>
								{/if}
							</div>
						{/each}
						{#each (data.channels as Channel[]).filter(c => c.takenBy) as ch (ch.id)}
							{@const meta = CHANNEL_META[ch.type] ?? { label: ch.type, icon: 'tabler:message' }}
							<div class="chip chip--taken">
								<Icon icon={meta.icon} width={11} height={11} />
								<span class="chip-name">{meta.label}</span>
								<span class="chip-taken-by font-mono">→ {ch.takenBy}</span>
							</div>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Cron jobs -->
			<div class="cap-section">
				<div class="cap-head">
					<Icon icon="tabler:clock" width={12} height={12} class="cap-head-icon" />
					<span class="cap-label font-mono">cron</span>
					<span class="cap-meta font-mono">{(data.crons as Cron[]).filter(c => c.attached).length} / {(data.crons as Cron[]).length}</span>
				</div>
				{#if (data.crons as Cron[]).length === 0}
					<p class="cap-empty font-mono">No cron jobs in workspace — <a href={`/w/${data.workspace.id}/workspace/cron`} class="cap-link">create one</a></p>
				{:else}
					<div class="chip-grid">
						{#each (data.crons as Cron[]).filter(c => c.attached) as job (job.id)}
							<div class="chip chip--on">
								<span class="chip-name">{job.name}</span>
								<span class="chip-tag font-mono">{cronSummary(job)}</span>
								<form method="POST" action="?/toggleAgentCron" use:enhance={connEnhance(`toggle:cron:${job.id}`)} style="display:contents">
									<input type="hidden" name="cron_id" value={job.id} />
									<input type="hidden" name="enabled" value={job.enabled ? 'false' : 'true'} />
									<button
										class="chip-x"
										type="submit"
										title={job.enabled ? 'Pause' : 'Resume'}
										disabled={!!pending[`toggle:cron:${job.id}`]}
									>
										{#if pending[`toggle:cron:${job.id}`]}
											<span class="spinner spinner--xs"></span>
										{:else}
											<Icon icon={job.enabled ? 'tabler:player-pause' : 'tabler:player-play'} width={9} height={9} />
										{/if}
									</button>
								</form>
								<form method="POST" action="?/detachCron" use:enhance={connEnhance(`detach:cron:${job.id}`)} style="display:contents">
									<input type="hidden" name="cron_id" value={job.id} />
									<button class="chip-x" type="submit" disabled={!!pending[`detach:cron:${job.id}`]} title="Detach">
										{#if pending[`detach:cron:${job.id}`]}<span class="spinner spinner--xs"></span>{:else}<Icon icon="tabler:x" width={9} height={9} />{/if}
									</button>
								</form>
							</div>
						{/each}
						{#each (data.crons as Cron[]).filter(c => !c.attached) as job (job.id)}
							<form method="POST" action="?/attachCron" use:enhance={connEnhance(`attach:cron:${job.id}`)} style="display:contents">
								<input type="hidden" name="cron_id" value={job.id} />
								<button class="chip chip--off" type="submit" disabled={!!pending[`attach:cron:${job.id}`]}>
									<span class="chip-name">{job.name}</span>
									<span class="chip-tag font-mono">{cronSummary(job)}</span>
									{#if pending[`attach:cron:${job.id}`]}<span class="spinner spinner--xs"></span>{:else}<Icon icon="tabler:plus" width={9} height={9} class="chip-plus" />{/if}
								</button>
							</form>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Prompts / Templates -->
			<div class="cap-section">
				<div class="cap-head">
					<Icon icon="tabler:file-text" width={12} height={12} class="cap-head-icon" />
					<span class="cap-label font-mono">prompts</span>
					<span class="cap-meta font-mono">{(data.templates as Template[]).filter(t => t.attached).length} / {(data.templates as Template[]).length}</span>
				</div>
				{#if (data.templates as Template[]).length === 0}
					<p class="cap-empty font-mono">No templates in library — <a href={`/w/${data.workspace.id}/prompts`} class="cap-link">create one</a></p>
				{:else}
					<div class="chip-grid">
						{#each (data.templates as Template[]).filter(t => t.attached) as tpl (tpl.id)}
							<div class="chip chip--on">
								<span class="chip-name">{tpl.name}</span>
								<span class="chip-tag font-mono">{tpl.templateType}</span>
								<form method="POST" action="?/detachTemplate" use:enhance={connEnhance(`detach:tpl:${tpl.id}`)} style="display:contents">
									<input type="hidden" name="template_id" value={tpl.id} />
									<button class="chip-x" type="submit" disabled={!!pending[`detach:tpl:${tpl.id}`]} title="Detach">
										{#if pending[`detach:tpl:${tpl.id}`]}<span class="spinner spinner--xs"></span>{:else}<Icon icon="tabler:x" width={9} height={9} />{/if}
									</button>
								</form>
							</div>
						{/each}
						{#each (data.templates as Template[]).filter(t => !t.attached) as tpl (tpl.id)}
							<form method="POST" action="?/attachTemplate" use:enhance={connEnhance(`attach:tpl:${tpl.id}`)} style="display:contents">
								<input type="hidden" name="template_id" value={tpl.id} />
								<button class="chip chip--off" type="submit" disabled={!!pending[`attach:tpl:${tpl.id}`]}>
									<span class="chip-name">{tpl.name}</span>
									<span class="chip-tag font-mono">{tpl.templateType}</span>
									{#if pending[`attach:tpl:${tpl.id}`]}<span class="spinner spinner--xs"></span>{:else}<Icon icon="tabler:plus" width={9} height={9} class="chip-plus" />{/if}
								</button>
							</form>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>

<style>
	/* ── Shell ────────────────────────────────────────────────── */
	.settings-shell {
		display: flex;
		flex-direction: column;
		height: 100vh;
		max-height: 100vh;
		background: var(--background);
	}

	/* ── Header ───────────────────────────────────────────────── */
	.settings-header {
		height: 56px;
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 1.25rem;
		border-bottom: 1px solid var(--border);
		background: var(--background);
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 0.65rem;
	}

	.back-btn {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		font-size: 0.68rem;
		font-family: var(--font-mono);
		color: var(--muted-foreground);
		text-decoration: none;
		padding: 0.28rem 0.55rem;
		border-radius: 0.2rem;
		transition: color 150ms ease, background 150ms ease;
	}

	.back-btn:hover {
		color: var(--foreground);
		background: var(--muted);
	}

	.header-divider {
		width: 1px;
		height: 14px;
		background: var(--border);
	}

	.header-crumb {
		font-size: 0.55rem;
		text-transform: uppercase;
		letter-spacing: 0.18em;
		color: var(--muted-foreground);
		opacity: 0.45;
	}

	.header-agent {
		display: flex;
		align-items: center;
		gap: 0.45rem;
	}

	.header-agent-name {
		font-size: 0.92rem;
		font-style: italic;
		color: var(--foreground);
		opacity: 0.65;
	}

	/* ── Body: two-column ─────────────────────────────────────── */
	.settings-body {
		flex: 1;
		overflow: hidden;
		display: grid;
		grid-template-columns: 272px 1fr;
	}

	/* ── Identity panel (left) ────────────────────────────────── */
	.identity-panel {
		border-right: 1px solid var(--border);
		overflow-y: auto;
		padding: 2rem 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	/* Avatar */
	.id-avatar-wrap {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.6rem;
	}

	.avatar-dropzone {
		position: relative;
		width: 88px;
		height: 88px;
		border-radius: 9999px;
		cursor: pointer;
		outline: 2px solid transparent;
		outline-offset: 3px;
		transition: outline-color 150ms ease;
		-webkit-user-select: none;
		user-select: none;
	}

	.avatar-dropzone:hover,
	.avatar-dropzone.dragging {
		outline-color: color-mix(in oklch, var(--primary) 45%, transparent);
	}

	.avatar-dropzone:focus-visible {
		outline-color: var(--primary);
	}

	.avatar-preview {
		position: absolute;
		inset: 0;
		border-radius: 9999px;
		overflow: hidden;
		background: var(--card);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.avatar-img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.avatar-overlay {
		position: absolute;
		inset: 0;
		border-radius: 9999px;
		background: color-mix(in oklch, black 55%, transparent);
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.2rem;
		opacity: 0;
		transition: opacity 150ms ease;
		color: white;
		font-size: 0.58rem;
		letter-spacing: 0.06em;
		pointer-events: none;
	}

	.avatar-dropzone:hover .avatar-overlay,
	.avatar-dropzone.uploading .avatar-overlay,
	.avatar-dropzone.dragging .avatar-overlay {
		opacity: 1;
	}

	.avatar-file-input {
		display: none;
	}

	.admin-badge {
		font-size: 0.52rem;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--primary);
		background: color-mix(in oklch, var(--primary) 10%, transparent);
		border: 1px solid color-mix(in oklch, var(--primary) 28%, transparent);
		padding: 0.12rem 0.45rem;
		border-radius: 2px;
	}

	/* Name form */
	.id-name-form {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}

	.id-name-row {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.3rem;
		padding: 0.2rem 0.2rem 0.2rem 0.7rem;
		transition: border-color 150ms ease, box-shadow 150ms ease;
	}

	.id-name-row:focus-within {
		border-color: color-mix(in oklch, var(--primary) 50%, var(--border));
		box-shadow: 0 0 0 3px color-mix(in oklch, var(--primary) 10%, transparent);
	}

	.id-name-input {
		flex: 1;
		background: transparent;
		border: none;
		outline: none;
		font-size: 0.95rem;
		font-style: italic;
		color: var(--foreground);
		min-width: 0;
	}

	.id-name-input::placeholder {
		color: var(--muted-foreground);
		opacity: 0.4;
	}

	.btn-save {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		padding: 0.32rem 0.7rem;
		background: var(--primary);
		color: var(--primary-foreground);
		font-size: 0.65rem;
		letter-spacing: 0.04em;
		border-radius: 0.2rem;
		flex-shrink: 0;
		transition: filter 150ms ease;
	}

	.btn-save:hover:not(:disabled) { filter: brightness(1.08); }
	.btn-save:disabled { opacity: 0.6; cursor: not-allowed; }

	.btn-field-save {
		padding: 0.3rem 0.6rem;
		background: color-mix(in oklch, var(--muted-foreground) 18%, transparent);
		color: var(--foreground);
		font-size: 0.6rem;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		border: 1px solid var(--border);
		border-radius: 0.2rem;
		transition: background 150ms ease;
	}
	.btn-field-save:hover:not(:disabled) {
		background: color-mix(in oklch, var(--primary) 25%, transparent);
	}
	.btn-field-save:disabled { opacity: 0.55; cursor: not-allowed; }

	.id-feedback {
		font-size: 0.62rem;
		letter-spacing: 0.02em;
	}

	.id-feedback--err { color: var(--destructive); }
	.id-feedback--ok  { color: color-mix(in oklch, oklch(0.65 0.18 145) 85%, var(--foreground)); }

	/* Identity sub-blocks */
	.id-block {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		padding-top: 1.5rem;
		border-top: 1px solid var(--border);
	}

	.id-block-label {
		font-size: 0.52rem;
		text-transform: uppercase;
		letter-spacing: 0.18em;
		color: var(--muted-foreground);
		opacity: 0.5;
	}

	.id-block-label--danger {
		color: color-mix(in oklch, var(--destructive) 65%, var(--muted-foreground));
		opacity: 1;
	}

	.runtime-row {
		display: flex;
		align-items: baseline;
		gap: 0.55rem;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.25rem;
		padding: 0.5rem 0.65rem;
	}

	.runtime-key {
		font-size: 0.58rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--muted-foreground);
		opacity: 0.6;
		flex-shrink: 0;
	}

	.runtime-val {
		font-size: 0.7rem;
		color: var(--foreground);
		opacity: 0.6;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		min-width: 0;
	}

	/* ── Toggle row (behaviour block) ─────────────────────────── */
	.toggle-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.3rem;
		padding: 0.6rem 0.7rem;
	}

	.toggle-copy {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
		min-width: 0;
	}

	.toggle-title {
		font-size: 0.65rem;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--foreground);
		opacity: 0.85;
	}

	.toggle-sub {
		font-size: 0.66rem;
		line-height: 1.4;
		color: var(--muted-foreground);
		opacity: 0.7;
	}

	.toggle-switch {
		position: relative;
		width: 30px;
		height: 17px;
		border-radius: 9999px;
		background: color-mix(in oklch, var(--muted-foreground) 20%, transparent);
		border: 1px solid var(--border);
		flex-shrink: 0;
		cursor: pointer;
		transition: background 150ms ease, border-color 150ms ease;
	}

	.toggle-switch--on {
		background: color-mix(in oklch, var(--primary) 55%, transparent);
		border-color: color-mix(in oklch, var(--primary) 60%, var(--border));
	}

	.toggle-switch:disabled { opacity: 0.6; cursor: not-allowed; }

	.toggle-knob {
		position: absolute;
		top: 1px;
		left: 1px;
		width: 13px;
		height: 13px;
		border-radius: 9999px;
		background: var(--background);
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.18);
		transition: transform 150ms ease;
	}

	.toggle-switch--on .toggle-knob { transform: translateX(13px); }

	/* Heartbeat interval input row */
	.hb-interval-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.35rem 0.1rem 0;
	}
	.hb-label {
		font-size: 0.6rem;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--muted-foreground);
		opacity: 0.75;
	}
	.hb-input {
		width: 6.5rem;
		padding: 0.3rem 0.5rem;
		font-size: 0.7rem;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.2rem;
		color: var(--foreground);
	}
	.hb-input:focus {
		outline: none;
		border-color: color-mix(in oklch, var(--primary) 45%, var(--border));
	}
	.hb-unit {
		font-size: 0.62rem;
		color: var(--muted-foreground);
		opacity: 0.7;
	}

	.inline-code {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		padding: 0.05rem 0.25rem;
		background: color-mix(in oklch, var(--muted-foreground) 14%, transparent);
		border-radius: 0.18rem;
	}

	/* Danger */
	.id-block--danger {
		margin-top: auto;
	}

	.btn-danger {
		display: inline-flex;
		align-items: center;
		gap: 0.38rem;
		padding: 0.38rem 0.7rem;
		background: color-mix(in oklch, var(--destructive) 8%, transparent);
		color: var(--destructive);
		border: 1px solid color-mix(in oklch, var(--destructive) 25%, transparent);
		font-size: 0.65rem;
		letter-spacing: 0.03em;
		border-radius: 0.25rem;
		transition: background 150ms ease;
	}

	.btn-danger:hover:not(:disabled) {
		background: color-mix(in oklch, var(--destructive) 14%, transparent);
	}

	.btn-danger:disabled { opacity: 0.6; cursor: not-allowed; }

	.danger-confirm {
		font-size: 0.7rem;
		color: var(--muted-foreground);
		line-height: 1.5;
	}

	.danger-confirm strong { color: var(--destructive); }

	.confirm-form {
		display: flex;
		align-items: center;
		gap: 0.45rem;
	}

	.btn-ghost {
		padding: 0.38rem 0.65rem;
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--muted-foreground);
		border-radius: 0.25rem;
		transition: color 150ms ease, background 150ms ease;
	}

	.btn-ghost:hover {
		color: var(--foreground);
		background: var(--muted);
	}

	/* ── Capabilities panel (right) ───────────────────────────── */
	.cap-panel {
		overflow-y: auto;
		padding: 1.75rem 2rem 3rem;
		display: flex;
		flex-direction: column;
	}

	.cap-panel-eyebrow {
		font-size: 0.52rem;
		text-transform: uppercase;
		letter-spacing: 0.2em;
		color: var(--muted-foreground);
		opacity: 0.4;
		margin-bottom: 1.25rem;
	}

	/* Section */
	.cap-section {
		display: flex;
		flex-direction: column;
		gap: 0.7rem;
		padding: 1.25rem 0;
		border-bottom: 1px solid var(--border);
	}

	.cap-section:last-of-type {
		border-bottom: none;
	}

	.cap-head {
		display: flex;
		align-items: center;
		gap: 0.45rem;
		color: var(--muted-foreground);
	}

	:global(.cap-head-icon) {
		flex-shrink: 0;
		opacity: 0.7;
	}

	.cap-label {
		flex: 1;
		font-size: 0.58rem;
		text-transform: uppercase;
		letter-spacing: 0.15em;
	}

	.cap-meta {
		font-size: 0.6rem;
		color: var(--muted-foreground);
		opacity: 0.45;
	}

	.cap-meta--active {
		color: var(--primary);
		opacity: 0.75;
	}

	.cap-empty {
		font-size: 0.68rem;
		color: var(--muted-foreground);
		opacity: 0.4;
		letter-spacing: 0.02em;
	}

	.cap-link {
		color: var(--primary);
		text-decoration: none;
	}

	.cap-link:hover {
		text-decoration: underline;
		text-underline-offset: 2px;
	}

	/* ── LLM pill selector ────────────────────────────────────── */
	.llm-row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
	}

	.llm-pill {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.32rem 0.75rem;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 9999px;
		font-size: 0.7rem;
		color: var(--muted-foreground);
		transition: border-color 150ms ease, color 150ms ease, background 150ms ease;
		cursor: pointer;
	}

	.llm-pill:hover:not(:disabled):not(.llm-pill--active) {
		border-color: color-mix(in oklch, var(--primary) 40%, var(--border));
		color: var(--foreground);
	}

	.llm-pill--active {
		border-color: color-mix(in oklch, var(--primary) 55%, transparent);
		background: color-mix(in oklch, var(--primary) 9%, var(--card));
		color: var(--foreground);
		cursor: default;
	}

	.llm-pill:disabled:not(.llm-pill--active) { opacity: 0.5; cursor: not-allowed; }

	.llm-dot {
		width: 6px;
		height: 6px;
		border-radius: 9999px;
		background: color-mix(in oklch, var(--muted-foreground) 40%, transparent);
		flex-shrink: 0;
		transition: background 150ms ease, box-shadow 150ms ease;
	}

	.llm-dot--on {
		background: var(--primary);
		box-shadow: 0 0 5px color-mix(in oklch, var(--primary) 50%, transparent);
	}

	/* ── Chip grid ────────────────────────────────────────────── */
	.chip-grid {
		display: flex;
		flex-wrap: wrap;
		gap: 0.38rem;
		align-items: flex-start;
	}

	/* Base chip — div for attached, button for available */
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 0.32rem;
		padding: 0.28rem 0.38rem 0.28rem 0.6rem;
		border-radius: 0.22rem;
		font-size: 0.75rem;
		border: 1px solid transparent;
		line-height: 1;
	}

	/* Active / attached */
	.chip--on {
		background: color-mix(in oklch, var(--primary) 9%, var(--card));
		border-color: color-mix(in oklch, var(--primary) 22%, transparent);
		color: var(--foreground);
	}

	/* Available / attachable */
	.chip--off {
		background: var(--card);
		border-color: var(--border);
		color: var(--muted-foreground);
		cursor: pointer;
		transition: background 120ms ease, border-color 120ms ease, color 120ms ease;
	}

	.chip--off:hover:not(:disabled) {
		background: color-mix(in oklch, var(--primary) 5%, var(--card));
		border-color: color-mix(in oklch, var(--primary) 28%, var(--border));
		color: var(--foreground);
	}

	.chip--off:disabled { opacity: 0.45; cursor: not-allowed; }

	/* Taken by another agent */
	.chip--taken {
		background: var(--card);
		border-color: var(--border);
		color: var(--muted-foreground);
		opacity: 0.35;
	}

	.chip-name {
		font-size: 0.75rem;
		line-height: 1;
	}

	.chip-tag {
		font-size: 0.53rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--muted-foreground);
		opacity: 0.65;
		background: color-mix(in oklch, var(--muted) 55%, transparent);
		padding: 0.08rem 0.28rem;
		border-radius: 2px;
	}

	.chip-date {
		font-size: 0.58rem;
		color: var(--muted-foreground);
		opacity: 0.5;
	}

	.chip-taken-by {
		font-size: 0.6rem;
		color: var(--muted-foreground);
		opacity: 0.5;
	}

	.chip-lock {
		display: flex;
		align-items: center;
		color: var(--muted-foreground);
		opacity: 0.3;
		padding-left: 0.1rem;
	}

	/* Detach button inside attached chip */
	.chip-x {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 15px;
		height: 15px;
		border-radius: 0.15rem;
		color: var(--muted-foreground);
		opacity: 0.4;
		flex-shrink: 0;
		transition: color 100ms ease, background 100ms ease, opacity 100ms ease;
	}

	.chip-x:hover:not(:disabled) {
		color: var(--destructive);
		background: color-mix(in oklch, var(--destructive) 12%, transparent);
		opacity: 1;
	}

	.chip-x:disabled { opacity: 0.25; cursor: not-allowed; }

	:global(.chip-plus) {
		opacity: 0.35;
		flex-shrink: 0;
	}

	.chip-with-err {
		display: flex;
		flex-direction: column;
		gap: 0.18rem;
	}

	.chip-err {
		font-size: 0.58rem;
		color: var(--destructive);
		letter-spacing: 0.02em;
		padding-left: 0.6rem;
	}

	/* ── Skill diagnostics: missing envs / bins ─────────────── */
	.skill-block {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		max-width: 100%;
	}

	.chip--warn {
		border-color: color-mix(in oklch, oklch(0.78 0.16 75) 45%, transparent);
		background: color-mix(in oklch, oklch(0.78 0.16 75) 8%, var(--card));
	}

	.chip-warn-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.18rem;
		font-size: 0.55rem;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: oklch(0.62 0.16 75);
		background: color-mix(in oklch, oklch(0.78 0.16 75) 14%, transparent);
		padding: 0.06rem 0.3rem;
		border-radius: 2px;
	}

	.needs-list {
		list-style: none;
		display: flex;
		flex-direction: column;
		gap: 0.18rem;
		padding: 0.18rem 0 0 0.55rem;
		margin: 0;
	}

	.needs-row {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		font-size: 0.6rem;
		color: var(--muted-foreground);
	}

	:global(.needs-icon) {
		opacity: 0.55;
	}

	.needs-key {
		color: var(--foreground);
		opacity: 0.75;
		letter-spacing: 0.02em;
	}

	.needs-cta {
		display: inline-flex;
		align-items: center;
		gap: 0.15rem;
		padding: 0.05rem 0.32rem;
		border-radius: 2px;
		color: var(--primary);
		text-decoration: none;
		background: color-mix(in oklch, var(--primary) 8%, transparent);
		border: 1px solid color-mix(in oklch, var(--primary) 22%, transparent);
		transition: background 120ms ease;
	}

	.needs-cta:hover {
		background: color-mix(in oklch, var(--primary) 16%, transparent);
	}

	.needs-note {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		font-size: 0.58rem;
		color: var(--muted-foreground);
		opacity: 0.55;
		padding-left: 0.55rem;
		margin: 0;
	}

	/* ── Spinners ─────────────────────────────────────────────── */
	.spinner {
		display: inline-block;
		width: 10px;
		height: 10px;
		border-radius: 9999px;
		border: 1.5px solid currentColor;
		border-right-color: transparent;
		animation: spin 0.8s linear infinite;
	}

	.spinner--sm {
		width: 8px;
		height: 8px;
	}

	.spinner--xs {
		width: 7px;
		height: 7px;
		border-width: 1px;
	}

	.spinner--danger {
		border-color: var(--destructive);
		border-right-color: transparent;
	}

	.upload-spinner {
		width: 18px;
		height: 18px;
		border-radius: 9999px;
		border: 2px solid white;
		border-right-color: transparent;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}
</style>
