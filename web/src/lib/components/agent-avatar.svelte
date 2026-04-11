<script lang="ts">
	import { Icon } from '$lib/icons';

	type Props = {
		name: string;
		isAdmin?: boolean;
		avatarUrl?: string | null;
		size?: number;
		class?: string;
	};

	let { name, isAdmin = false, avatarUrl = null, size = 36, class: className = '' }: Props = $props();

	// Deterministic hue from name — stable per-agent tint.
	function hashHue(input: string): number {
		let h = 0;
		for (let i = 0; i < input.length; i++) {
			h = (h * 31 + input.charCodeAt(i)) >>> 0;
		}
		// Biased toward warm hues (30°–340°, wrapping)
		return h % 360;
	}

	const initials = $derived(
		name
			.trim()
			.split(/\s+/)
			.map((w) => w[0] ?? '')
			.join('')
			.slice(0, 2)
			.toUpperCase() || '·'
	);

	const hue = $derived(hashHue(name));
	// Admin always uses primary amber; others use hashed hue for identity.
	const bg = $derived(
		isAdmin
			? 'color-mix(in oklch, var(--primary) 22%, var(--card))'
			: `oklch(0.92 0.045 ${hue} / 0.55)`
	);
	const ring = $derived(
		isAdmin
			? 'color-mix(in oklch, var(--primary) 45%, transparent)'
			: `oklch(0.62 0.09 ${hue} / 0.35)`
	);
	const fg = $derived(
		isAdmin ? 'var(--primary)' : `oklch(0.32 0.05 ${hue})`
	);
</script>

<div
	class="agent-avatar font-display {className}"
	style="
		width: {size}px;
		height: {size}px;
		background: {avatarUrl ? 'transparent' : bg};
		color: {fg};
		box-shadow: inset 0 0 0 1px {ring};
		font-size: {Math.round(size * 0.4)}px;
	"
>
	{#if avatarUrl}
		<img src={avatarUrl} alt={name} class="avatar-img" />
	{:else if isAdmin}
		<Icon icon="oc:claw" width={Math.round(size * 0.5)} height={Math.round(size * 0.5)} />
	{:else}
		<span class="italic leading-none tracking-tight">{initials}</span>
	{/if}
</div>

<style>
	.agent-avatar {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		border-radius: 9999px;
		flex-shrink: 0;
		position: relative;
		font-weight: 400;
		overflow: hidden;
	}

	.avatar-img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		border-radius: 9999px;
	}

	:global(.dark) .agent-avatar {
		box-shadow: inset 0 0 0 1px oklch(1 0 0 / 0.08);
	}
</style>
