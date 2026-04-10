<script lang="ts">
	import { Icon } from '$lib/icons';
</script>

<div class="empty">
	<div class="inner">
		<div class="mark">
			<Icon icon="oc:claw" width={28} height={28} />
		</div>
		<h1 class="title font-display">
			Your <em>Admin</em> is still being forged.
		</h1>
		<p class="sub">
			Bootstrap spins up the workspace, generates your token, and scaffolds
			the Admin agent's files. It will appear in the sidebar in a moment.
		</p>
		<p class="mono">waiting for fleet…</p>
	</div>
</div>

<style>
	.empty {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 4rem 2rem;
	}

	.inner {
		max-width: 32rem;
		text-align: center;
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.mark {
		width: 56px;
		height: 56px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: color-mix(in oklch, var(--primary) 10%, transparent);
		color: var(--primary);
		margin-bottom: 1.75rem;
		clip-path: polygon(0 0, 100% 0, 100% 75%, 75% 100%, 0 100%);
	}

	.title {
		font-size: 2.5rem;
		line-height: 1.05;
		margin-bottom: 1rem;
		letter-spacing: -0.01em;
	}

	.title em {
		color: var(--primary);
	}

	.sub {
		color: var(--muted-foreground);
		font-size: 0.92rem;
		line-height: 1.55;
		max-width: 28rem;
		margin-bottom: 2rem;
	}

	.mono {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: color-mix(in oklch, var(--foreground) 30%, transparent);
	}
</style>
