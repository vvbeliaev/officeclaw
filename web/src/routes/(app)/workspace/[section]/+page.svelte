<script lang="ts">
	let { data } = $props();
</script>

<div class="shell">
	<header class="head">
		<div class="crumb font-mono">workspace / {data.key}</div>
		<h1 class="title font-display">{data.section.title}</h1>
		<p class="tag">{data.section.tagline}</p>
	</header>

	<div class="empty">
		<div class="empty-card">
			<div class="quote font-display">
				<em>"Ask your Admin"</em>
			</div>
			<p class="desc">
				This surface is intentionally read-only. Most configuration in OfficeClaw
				happens through conversation with your Admin agent — <em>"add a GitHub
				skill to my research agent"</em>, <em>"connect my Slack"</em>, and so on.
				This page will soon show what Admin has set up for you.
			</p>
			<a href="/" class="back font-mono">← back to Admin</a>
		</div>
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
		padding: 3rem 3rem 2rem;
		border-bottom: 1px solid var(--border);
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

	.empty {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 3rem;
	}

	.empty-card {
		max-width: 32rem;
		text-align: center;
		padding: 2.5rem 2rem;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.35rem;
		position: relative;
	}

	.empty-card::before {
		content: '';
		position: absolute;
		top: -1px;
		left: 2rem;
		right: 2rem;
		height: 2px;
		background: var(--primary);
		opacity: 0.6;
	}

	.quote {
		font-size: 1.75rem;
		line-height: 1.1;
		color: var(--foreground);
		margin-bottom: 1.25rem;
	}

	.quote em {
		color: var(--primary);
	}

	.desc {
		color: var(--muted-foreground);
		font-size: 0.88rem;
		line-height: 1.65;
		margin-bottom: 2rem;
	}

	.desc em {
		color: var(--foreground);
		font-style: italic;
	}

	.back {
		font-size: 0.7rem;
		color: var(--primary);
		letter-spacing: 0.04em;
		text-decoration: none;
	}

	.back:hover {
		text-decoration: underline;
		text-underline-offset: 4px;
	}
</style>
