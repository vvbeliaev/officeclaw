<div class="shell">
	<header class="head">
		<div class="crumb font-mono">workspace / skills</div>
		<h1 class="title font-display">Skills</h1>
		<p class="tag">reusable capabilities you teach once and wire into any agent.</p>
	</header>
	<div class="stub">
		<p class="quote font-display"><em>"Ask your Admin"</em></p>
		<p class="desc">
			Skill management happens through conversation with your Admin agent —
			<em>"add a GitHub skill"</em>, <em>"create a research skill"</em>, and so on.
			This page will surface what Admin has set up for you.
		</p>
		<a href="/" class="back font-mono">← back to Admin</a>
	</div>
</div>

<style>
	.shell { flex: 1; display: flex; flex-direction: column; overflow-y: auto; }
	.head { padding: 1.75rem 3rem 2rem; border-bottom: 1px solid var(--border); flex-shrink: 0; }
	.crumb {
		font-size: 0.62rem;
		letter-spacing: 0.16em;
		text-transform: uppercase;
		color: color-mix(in oklch, var(--foreground) 35%, transparent);
		margin-bottom: 0.75rem;
	}
	.title { font-size: 3.25rem; line-height: 1; font-style: italic; letter-spacing: -0.015em; }
	.tag { margin-top: 0.85rem; color: var(--muted-foreground); font-size: 0.95rem; max-width: 36rem; }

	.stub {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 3rem;
		text-align: center;
		gap: 1rem;
	}
	.quote { font-size: 2rem; line-height: 1.1; color: var(--foreground); }
	.quote em { color: var(--primary); }
	.desc { font-size: 0.88rem; line-height: 1.65; color: var(--muted-foreground); max-width: 28rem; }
	.desc em { color: var(--foreground); font-style: italic; }
	.back { font-size: 0.7rem; color: var(--primary); letter-spacing: 0.04em; text-decoration: none; }
	.back:hover { text-decoration: underline; text-underline-offset: 4px; }
</style>
