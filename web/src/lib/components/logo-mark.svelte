<script lang="ts">
	import { Icon } from '$lib/icons';

	let { size = 28 }: { size?: number } = $props();
</script>

<div class="mark" style:width="{size}px" style:height="{size}px">
	<Icon icon="oc:claw" width={Math.round(size * 0.57)} height={Math.round(size * 0.57)} />
</div>

<style>
	.mark {
		background: var(--primary);
		color: var(--primary-foreground);
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		clip-path: polygon(0 0, 100% 0, 100% 75%, 75% 100%, 0 100%);
	}
</style>
