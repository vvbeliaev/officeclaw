<script lang="ts">
	import LogoMark from './logo-mark.svelte';

	let { markSize = 28 }: { markSize?: number } = $props();
</script>

<div class="logo">
	<LogoMark size={markSize} />
	<span class="text">Office<strong>Claw</strong></span>
</div>

<style>
	.logo {
		display: flex;
		align-items: center;
		gap: 0.65rem;
	}

	.text {
		font-size: 0.875rem;
		letter-spacing: -0.01em;
		color: var(--sidebar-foreground);
		font-weight: 400;
	}

	strong {
		font-weight: 600;
	}
</style>
