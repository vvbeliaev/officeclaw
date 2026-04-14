<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { Icon } from '$lib/icons';

	let { data } = $props();

	const channels = $derived(data.channels as { id: string; name: string; type: string; createdAt: Date }[]);

	type ChannelType = 'telegram' | 'discord' | 'whatsapp';
	const CHANNEL_META: Record<ChannelType, { label: string; icon: string; color: string }> = {
		telegram:  { label: 'Telegram',  icon: 'tabler:brand-telegram', color: 'oklch(0.56 0.16 240)' },
		discord:   { label: 'Discord',   icon: 'tabler:brand-discord',  color: 'oklch(0.60 0.16 280)' },
		whatsapp:  { label: 'WhatsApp',  icon: 'tabler:brand-whatsapp', color: 'oklch(0.62 0.18 148)' }
	};

	// ── Wizard state ─────────────────────────────────────────
	let addOpen = $state(false);
	let addStep: 'pick' | ChannelType = $state('pick');
	let chSaving = $state(false);
	let chError: string | null = $state(null);
	let chName = $state('');

	// Telegram
	let tgToken = $state('');
	let tgAllowMode: 'all' | 'specific' = $state('all');
	let tgAllowIds = $state('');
	let tgStreaming = $state(true);

	// Discord
	let dcToken = $state('');
	let dcAllowMode: 'all' | 'specific' = $state('all');
	let dcAllowIds = $state('');

	// WhatsApp
	let waUrl = $state('ws://localhost:3001');
	let waToken = $state('');
	let waAllowMode: 'all' | 'specific' = $state('all');
	let waAllowIds = $state('');

	function openAdd() {
		addOpen = true;
		addStep = 'pick';
		chError = null;
		chName = '';
		tgToken = ''; tgAllowMode = 'all'; tgAllowIds = ''; tgStreaming = true;
		dcToken = ''; dcAllowMode = 'all'; dcAllowIds = '';
		waUrl = 'ws://localhost:3001'; waToken = ''; waAllowMode = 'all'; waAllowIds = '';
	}
	function closeAdd() { addOpen = false; }
	function pickType(type: ChannelType) { addStep = type; chError = null; }

	function parseIds(raw: string): string[] {
		return raw.split(/[\s,]+/).map(s => s.trim()).filter(Boolean);
	}

	function allowFrom(mode: 'all' | 'specific', raw: string): string[] {
		return mode === 'all' ? ['*'] : parseIds(raw);
	}

	async function saveChannel() {
		chError = null;
		if (!chName.trim()) { chError = 'Channel name is required'; return; }
		let type: ChannelType;
		let config: Record<string, unknown>;

		if (addStep === 'telegram') {
			if (!tgToken.trim()) { chError = 'Bot token is required'; return; }
			const af = allowFrom(tgAllowMode, tgAllowIds);
			if (tgAllowMode === 'specific' && af.length === 0) { chError = 'Enter at least one user ID'; return; }
			type = 'telegram';
			config = { token: tgToken.trim(), allow_from: af, streaming: tgStreaming };

		} else if (addStep === 'discord') {
			if (!dcToken.trim()) { chError = 'Bot token is required'; return; }
			const af = allowFrom(dcAllowMode, dcAllowIds);
			if (dcAllowMode === 'specific' && af.length === 0) { chError = 'Enter at least one user ID'; return; }
			type = 'discord';
			config = { token: dcToken.trim(), allow_from: af };

		} else if (addStep === 'whatsapp') {
			if (!waUrl.trim()) { chError = 'Bridge URL is required'; return; }
			if (!waToken.trim()) { chError = 'Bridge token is required'; return; }
			const af = allowFrom(waAllowMode, waAllowIds);
			if (waAllowMode === 'specific' && af.length === 0) { chError = 'Enter at least one phone number'; return; }
			type = 'whatsapp';
			config = { bridge_url: waUrl.trim(), bridge_token: waToken.trim(), allow_from: af };

		} else {
			return;
		}

		chSaving = true;
		try {
			const res = await fetch('/api/channels', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ name: chName.trim(), type, config, workspace_id: data.workspace.id })
			});
			if (!res.ok) { chError = await res.text(); return; }
			addOpen = false;
			await invalidateAll();
		} catch (e) {
			chError = e instanceof Error ? e.message : 'Failed to create channel';
		} finally {
			chSaving = false;
		}
	}

	// ── Delete ───────────────────────────────────────────────
	let deleteId: string | null = $state(null);
	let deleting = $state(false);
	let deleteError: string | null = $state(null);

	async function confirmDelete() {
		if (!deleteId) return;
		deleting = true;
		deleteError = null;
		try {
			const res = await fetch(`/api/channels/${deleteId}`, { method: 'DELETE' });
			if (!res.ok && res.status !== 204) { deleteError = await res.text(); return; }
			deleteId = null;
			await invalidateAll();
		} catch (e) {
			deleteError = e instanceof Error ? e.message : 'Failed to delete';
		} finally {
			deleting = false;
		}
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
		<div class="crumb font-mono">workspace / channels</div>
		<h1 class="title font-display">Channels</h1>
		<p class="tag">where your agents listen and reply — Telegram, Discord, email.</p>
	</header>

	<div class="body">

		<!-- ── Add wizard ──────────────────────────────────────── -->
		{#if addOpen}
			<div class="form-card">

				{#if addStep === 'pick'}
					<p class="pick-label font-mono">choose platform</p>
					<div class="type-grid">
						{#each Object.entries(CHANNEL_META) as [type, meta]}
							<button class="type-btn" style="--c: {meta.color}" type="button" onclick={() => pickType(type as ChannelType)}>
								<span class="type-icon">
									<Icon icon={meta.icon} width={22} height={22} />
								</span>
								<span class="type-name font-mono">{meta.label}</span>
								<span class="type-arr">→</span>
							</button>
						{/each}
					</div>
					<div class="form-actions">
						<button class="btn-ghost font-mono" type="button" onclick={closeAdd}>Cancel</button>
					</div>

				{:else if addStep === 'telegram'}
					{@const meta = CHANNEL_META.telegram}
					<div class="form-header" style="--c: {meta.color}">
						<span class="form-plat-icon"><Icon icon={meta.icon} width={16} height={16} /></span>
						<span class="form-title font-mono">Connect Telegram</span>
					</div>

					<div class="field">
						<label class="field-label font-mono" for="ch-name-tg">Channel Name</label>
						<input id="ch-name-tg" class="field-input font-mono" type="text" bind:value={chName} placeholder="e.g. Support Bot" spellcheck="false" />
					</div>

					<div class="field">
						<label class="field-label font-mono" for="tg-token">Bot Token</label>
						<input id="tg-token" class="field-input font-mono" type="password" bind:value={tgToken} placeholder="123456789:ABC..." spellcheck="false" autocomplete="new-password" />
						<p class="field-hint font-mono">Get from <span class="code">@BotFather</span> → /newbot</p>
					</div>

					<div class="field">
						<span class="field-label font-mono">Who can message this bot?</span>
						<div class="radio-group">
							<label class="radio font-mono"><input type="radio" bind:group={tgAllowMode} value="all" /><span>Everyone <span class="sub">(open bot)</span></span></label>
							<label class="radio font-mono"><input type="radio" bind:group={tgAllowMode} value="specific" /><span>Specific user IDs</span></label>
						</div>
						{#if tgAllowMode === 'specific'}
							<textarea class="field-textarea font-mono" bind:value={tgAllowIds} placeholder="12345678, 87654321" rows={2} spellcheck="false"></textarea>
							<p class="field-hint font-mono">Comma-separated Telegram numeric IDs. Use <span class="code">@userinfobot</span> to find yours.</p>
						{/if}
					</div>

					<label class="toggle font-mono">
						<input type="checkbox" bind:checked={tgStreaming} />
						<span>Stream responses</span>
						<span class="sub">(show partial output as it generates)</span>
					</label>

				{:else if addStep === 'discord'}
					{@const meta = CHANNEL_META.discord}
					<div class="form-header" style="--c: {meta.color}">
						<span class="form-plat-icon"><Icon icon={meta.icon} width={16} height={16} /></span>
						<span class="form-title font-mono">Connect Discord</span>
					</div>

					<div class="field">
						<label class="field-label font-mono" for="ch-name-dc">Channel Name</label>
						<input id="ch-name-dc" class="field-input font-mono" type="text" bind:value={chName} placeholder="e.g. Dev Server" spellcheck="false" />
					</div>

					<div class="field">
						<label class="field-label font-mono" for="dc-token">Bot Token</label>
						<input id="dc-token" class="field-input font-mono" type="password" bind:value={dcToken} placeholder="MTxxxxxxx.Gyyyyy.zzzzzzz" spellcheck="false" autocomplete="new-password" />
						<p class="field-hint font-mono">Discord Developer Portal → Your App → Bot → Reset Token</p>
					</div>

					<div class="field">
						<span class="field-label font-mono">Who can message this bot?</span>
						<div class="radio-group">
							<label class="radio font-mono"><input type="radio" bind:group={dcAllowMode} value="all" /><span>Everyone <span class="sub">(open bot)</span></span></label>
							<label class="radio font-mono"><input type="radio" bind:group={dcAllowMode} value="specific" /><span>Specific user IDs</span></label>
						</div>
						{#if dcAllowMode === 'specific'}
							<textarea class="field-textarea font-mono" bind:value={dcAllowIds} placeholder="123456789012345678" rows={2} spellcheck="false"></textarea>
							<p class="field-hint font-mono">Discord user IDs (18-digit numbers). Enable Developer Mode → right-click user → Copy ID.</p>
						{/if}
					</div>

				{:else if addStep === 'whatsapp'}
					{@const meta = CHANNEL_META.whatsapp}
					<div class="form-header" style="--c: {meta.color}">
						<span class="form-plat-icon"><Icon icon={meta.icon} width={16} height={16} /></span>
						<span class="form-title font-mono">Connect WhatsApp</span>
					</div>

					<div class="field">
						<label class="field-label font-mono" for="ch-name-wa">Channel Name</label>
						<input id="ch-name-wa" class="field-input font-mono" type="text" bind:value={chName} placeholder="e.g. Customer Support" spellcheck="false" />
					</div>

					<div class="field">
						<label class="field-label font-mono" for="wa-url">Bridge URL</label>
						<input id="wa-url" class="field-input font-mono" type="text" bind:value={waUrl} placeholder="ws://localhost:3001" spellcheck="false" />
						<p class="field-hint font-mono">WebSocket address of your <span class="code">nanobot-whatsapp-bridge</span> instance.</p>
					</div>

					<div class="field">
						<label class="field-label font-mono" for="wa-token">Bridge Token</label>
						<input id="wa-token" class="field-input font-mono" type="password" bind:value={waToken} placeholder="••••••••" spellcheck="false" autocomplete="new-password" />
						<p class="field-hint font-mono">Auth token configured in the bridge — set via <span class="code">BRIDGE_TOKEN</span> env var.</p>
					</div>

					<div class="field">
						<span class="field-label font-mono">Who can message this bot?</span>
						<div class="radio-group">
							<label class="radio font-mono"><input type="radio" bind:group={waAllowMode} value="all" /><span>Everyone</span></label>
							<label class="radio font-mono"><input type="radio" bind:group={waAllowMode} value="specific" /><span>Specific numbers</span></label>
						</div>
						{#if waAllowMode === 'specific'}
							<textarea class="field-textarea font-mono" bind:value={waAllowIds} placeholder="+1234567890, +0987654321" rows={2} spellcheck="false"></textarea>
							<p class="field-hint font-mono">International format with country code.</p>
						{/if}
					</div>
				{/if}

				{#if addStep !== 'pick'}
					{#if chError}<p class="form-error font-mono">{chError}</p>{/if}
					<div class="form-actions">
						<button class="btn-primary font-mono" type="button" onclick={saveChannel} disabled={chSaving}>
							{#if chSaving}<span class="spinner"></span>connecting…{:else}Connect{/if}
						</button>
						<button class="btn-ghost font-mono" type="button" onclick={closeAdd}>Cancel</button>
					</div>
				{/if}

			</div>
		{/if}

		<!-- ── List header ─────────────────────────────────────── -->
		<div class="list-head">
			<span class="list-count font-mono">{channels.length} channel{channels.length !== 1 ? 's' : ''}</span>
			{#if !addOpen}
				<button class="btn-add font-mono" type="button" onclick={openAdd}>
					<Icon icon="oc:spawn" width={11} height={11} />
					Add channel
				</button>
			{/if}
		</div>

		<!-- ── Empty state ─────────────────────────────────────── -->
		{#if channels.length === 0}
			<div class="empty-state">
				<div class="empty-icons">
					{#each Object.values(CHANNEL_META) as meta}
						<div class="empty-icon-item" style="--c: {meta.color}">
							<Icon icon={meta.icon} width={19} height={19} />
						</div>
					{/each}
				</div>
				<p class="empty-title">No channels yet</p>
				<p class="empty-sub">Connect a Telegram, Discord, or WhatsApp bot and attach it to any agent.</p>
			</div>

		{:else}
			<div class="ch-list">
				{#each channels as ch (ch.id)}
					{@const meta = CHANNEL_META[ch.type as ChannelType]}
					<div class="ch-item" class:ch-deleting={deleteId === ch.id} style="--ch-c: {meta?.color ?? 'var(--primary)'}">
						<div class="ch-row">
							<span class="ch-icon" style={meta ? `color:${meta.color};` : ''}>
								<Icon icon={meta?.icon ?? 'tabler:plug'} width={15} height={15} />
							</span>
							<span class="ch-name font-mono">{ch.name}</span>
							<span class="ch-date font-mono">{relDate(ch.createdAt)}</span>
							<button
								class="ch-del font-mono"
								type="button"
								onclick={() => { deleteId = deleteId === ch.id ? null : ch.id; deleteError = null; }}
							>delete</button>
						</div>

						{#if deleteId === ch.id}
							<div class="danger-panel">
								<p class="delete-msg font-mono">
									Remove <strong>{ch.name}</strong>? Agents using it will lose access.
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

	/* ── Header ─────────────────────────────────────────────── */
	.head { padding: 1.75rem 3rem 2rem; border-bottom: 1px solid var(--border); flex-shrink: 0; }
	.crumb {
		font-size: 0.62rem;
		letter-spacing: 0.16em;
		text-transform: uppercase;
		color: color-mix(in oklch, var(--foreground) 35%, transparent);
		margin-bottom: 0.75rem;
	}
	.title { font-size: 3.5rem; line-height: 1; font-style: italic; letter-spacing: -0.015em; }
	.tag { margin-top: 0.9rem; color: var(--muted-foreground); font-size: 0.95rem; max-width: 36rem; }

	/* ── Body ────────────────────────────────────────────────── */
	.body { flex: 1; padding: 1.75rem 3rem 4rem; display: flex; flex-direction: column; gap: 1rem; }

	/* ── List header ──────────────────────────────────────── */
	.list-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding-bottom: 0.75rem;
		border-bottom: 1px solid var(--border);
	}
	.list-count {
		font-size: 0.62rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: color-mix(in oklch, var(--foreground) 40%, transparent);
	}
	.btn-add {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.68rem;
		letter-spacing: 0.04em;
		color: var(--primary);
		padding: 0.3rem 0.6rem;
		border-radius: 0.25rem;
		transition: background 150ms ease;
	}
	.btn-add:hover { background: color-mix(in oklch, var(--primary) 10%, transparent); }

	/* ── Form card ───────────────────────────────────────────── */
	.form-card {
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.45rem;
		padding: 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
		position: relative;
	}
	.form-card::before {
		content: '';
		position: absolute;
		top: -1px; left: 1.5rem; right: 1.5rem;
		height: 2px;
		background: var(--primary);
		opacity: 0.5;
		border-radius: 0 0 2px 2px;
	}

	/* ── Platform picker ─────────────────────────────────────── */
	.pick-label {
		font-size: 0.62rem;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--muted-foreground);
	}
	.type-grid { display: flex; flex-direction: column; gap: 0.5rem; }
	.type-btn {
		display: flex;
		align-items: center;
		gap: 0.9rem;
		padding: 0.85rem 1rem;
		border: 1px solid var(--border);
		border-left: 3px solid var(--c);
		border-radius: 0.35rem;
		background: var(--background);
		cursor: pointer;
		text-align: left;
		transition: background 140ms ease, transform 140ms ease, border-color 140ms ease;
	}
	.type-btn:hover {
		background: color-mix(in oklch, var(--c) 7%, var(--background));
		border-color: color-mix(in oklch, var(--c) 55%, var(--border));
		transform: translateX(2px);
	}
	.type-icon { color: var(--c); display: flex; align-items: center; flex-shrink: 0; }
	.type-name { flex: 1; font-size: 0.78rem; letter-spacing: 0.04em; color: var(--foreground); }
	.type-arr {
		font-size: 0.82rem;
		color: color-mix(in oklch, var(--foreground) 30%, transparent);
		transition: transform 140ms ease, color 140ms ease;
		flex-shrink: 0;
	}
	.type-btn:hover .type-arr { transform: translateX(3px); color: var(--c); }

	/* ── Form header (per-platform) ─────────────────────────── */
	.form-header { display: flex; align-items: center; gap: 0.6rem; }
	.form-plat-icon { color: var(--c); display: flex; align-items: center; }
	.form-title { font-size: 0.8rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--foreground); }

	/* ── Fields ──────────────────────────────────────────────── */
	.field { display: flex; flex-direction: column; gap: 0.4rem; }
	.field-label {
		font-size: 0.62rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: color-mix(in oklch, var(--foreground) 60%, transparent);
	}
	.field-input, .field-textarea {
		padding: 0.42rem 0.65rem;
		background: var(--background);
		border: 1px solid color-mix(in oklch, var(--border) 80%, transparent);
		border-radius: 0.2rem;
		font-size: 0.75rem;
		color: var(--foreground);
		letter-spacing: 0.02em;
		transition: border-color 120ms ease;
	}
	.field-textarea { resize: vertical; }
	.field-input:focus, .field-textarea:focus {
		border-color: color-mix(in oklch, var(--primary) 50%, var(--border));
	}
	.field-hint { font-size: 0.65rem; color: var(--muted-foreground); letter-spacing: 0.01em; line-height: 1.5; }
	.code {
		font-family: var(--font-mono);
		background: color-mix(in oklch, var(--foreground) 8%, transparent);
		padding: 0.05em 0.3em;
		border-radius: 3px;
	}

	.radio-group { display: flex; flex-direction: column; gap: 0.35rem; }
	.radio { display: flex; align-items: center; gap: 0.5rem; font-size: 0.72rem; color: var(--foreground); cursor: pointer; }
	.sub { color: var(--muted-foreground); font-size: 0.65rem; }
	.toggle { display: flex; align-items: center; gap: 0.5rem; font-size: 0.72rem; color: var(--foreground); cursor: pointer; }

	/* ── Channel list ──────────────────────────────────────── */
	.ch-list { display: flex; flex-direction: column; }
	.ch-item {
		border-bottom: 1px solid color-mix(in oklch, var(--border) 70%, transparent);
		border-left: 2px solid color-mix(in oklch, var(--ch-c) 35%, transparent);
		padding-left: 0.85rem;
		transition: background 150ms ease, border-left-color 150ms ease;
	}
	.ch-item:first-child { border-top: 1px solid color-mix(in oklch, var(--border) 70%, transparent); }
	.ch-item:hover {
		background: color-mix(in oklch, var(--ch-c) 4%, transparent);
		border-left-color: var(--ch-c);
	}
	.ch-item.ch-deleting { background: color-mix(in oklch, var(--card) 60%, transparent); }
	.ch-row { display: flex; align-items: center; gap: 0.85rem; padding: 0.9rem 0; }
	.ch-icon { display: flex; align-items: center; flex-shrink: 0; }
	.ch-name { flex: 1; font-size: 0.82rem; letter-spacing: 0.04em; color: var(--foreground); }
	.ch-date { font-size: 0.65rem; letter-spacing: 0.02em; color: var(--muted-foreground); flex-shrink: 0; }
	.ch-del {
		font-size: 0.65rem;
		letter-spacing: 0.06em;
		padding: 0.28rem 0.65rem;
		border-radius: 0.2rem;
		color: var(--muted-foreground);
		flex-shrink: 0;
		transition: color 150ms ease, background 150ms ease;
	}
	.ch-del:hover { color: var(--destructive); background: color-mix(in oklch, var(--destructive) 8%, transparent); }
	.danger-panel { padding: 0.5rem 0 1rem 1.75rem; display: flex; flex-direction: column; gap: 0.9rem; }

	/* ── Buttons ──────────────────────────────────────────── */
	.btn-primary {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.45rem 0.9rem;
		background: var(--primary);
		color: var(--primary-foreground);
		font-size: 0.68rem;
		letter-spacing: 0.04em;
		border-radius: 0.25rem;
		transition: filter 150ms ease;
	}
	.btn-primary:hover:not(:disabled) { filter: brightness(1.08); }
	.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
	.btn-ghost {
		padding: 0.45rem 0.75rem;
		font-size: 0.68rem;
		letter-spacing: 0.04em;
		color: var(--muted-foreground);
		border-radius: 0.25rem;
		transition: color 150ms ease, background 150ms ease;
	}
	.btn-ghost:hover { color: var(--foreground); background: var(--muted); }
	.btn-danger {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.45rem 0.9rem;
		background: color-mix(in oklch, var(--destructive) 10%, transparent);
		color: var(--destructive);
		border: 1px solid color-mix(in oklch, var(--destructive) 30%, transparent);
		font-size: 0.68rem;
		letter-spacing: 0.04em;
		border-radius: 0.25rem;
		transition: background 150ms ease;
	}
	.btn-danger:hover:not(:disabled) { background: color-mix(in oklch, var(--destructive) 16%, transparent); }
	.btn-danger:disabled { opacity: 0.6; cursor: not-allowed; }

	.form-error { font-size: 0.68rem; color: var(--destructive); letter-spacing: 0.02em; }
	.form-actions { display: flex; align-items: center; gap: 0.5rem; }
	.delete-msg { font-size: 0.72rem; color: var(--muted-foreground); letter-spacing: 0.01em; line-height: 1.5; }
	.delete-msg strong { color: var(--foreground); }

	/* ── Empty state ─────────────────────────────────────── */
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
		padding: 4rem 2rem;
		gap: 1rem;
	}
	.empty-icons { display: flex; gap: 0.65rem; margin-bottom: 0.25rem; }
	.empty-icon-item {
		width: 42px; height: 42px;
		display: flex; align-items: center; justify-content: center;
		background: color-mix(in oklch, var(--c) 9%, var(--card));
		border: 1px solid color-mix(in oklch, var(--c) 20%, var(--border));
		border-radius: 0.4rem;
		color: var(--c);
	}
	.empty-title { font-size: 1rem; font-weight: 500; color: var(--foreground); }
	.empty-sub { font-size: 0.85rem; line-height: 1.6; color: var(--muted-foreground); max-width: 28rem; }

	/* ── Spinner ──────────────────────────────────────────── */
	.spinner {
		display: inline-block;
		width: 10px; height: 10px;
		border-radius: 9999px;
		border: 1.5px solid currentColor;
		border-right-color: transparent;
		animation: spin 0.8s linear infinite;
	}
	.spinner--danger { border-color: var(--destructive); border-right-color: transparent; }
	@keyframes spin { to { transform: rotate(360deg); } }
</style>
