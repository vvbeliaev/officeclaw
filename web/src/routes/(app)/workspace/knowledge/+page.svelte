<div class="shell">
	<header class="head">
		<div class="crumb font-mono">workspace / knowledge</div>
		<div class="title-row">
			<h1 class="title font-display">Knowledge</h1>
			<span class="soon-badge font-mono">coming soon</span>
		</div>
		<p class="tag">documents, notes, and sources your fleet can draw from.</p>
	</header>
	<div class="stub">
		<div class="stub-wm font-display" aria-hidden="true">Soon</div>
		<p class="quote font-display"><em>"Ask your Admin"</em></p>
		<p class="desc">
			Knowledge management happens through conversation with your Admin agent —
			<em>"add this document"</em>, <em>"index my notes"</em>, and so on.
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
	.title-row { display: flex; align-items: baseline; gap: 1.25rem; flex-wrap: wrap; }
	.title { font-size: 3.5rem; line-height: 1; font-style: italic; letter-spacing: -0.015em; }
	.soon-badge {
		font-size: 0.58rem;
		letter-spacing: 0.2em;
		text-transform: uppercase;
		color: var(--primary);
		background: color-mix(in oklch, var(--primary) 10%, transparent);
		border: 1px solid color-mix(in oklch, var(--primary) 28%, transparent);
		padding: 0.22rem 0.7rem;
		border-radius: 100px;
		white-space: nowrap;
		flex-shrink: 0;
	}
	.tag { margin-top: 0.9rem; color: var(--muted-foreground); font-size: 0.95rem; max-width: 36rem; }

	.stub {
		flex: 1;
		position: relative;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 3rem;
		text-align: center;
		gap: 1rem;
	}
	.stub-wm {
		position: absolute;
		font-size: min(22vw, 18rem);
		font-style: italic;
		font-variation-settings: 'opsz' 144, 'wght' 300;
		color: color-mix(in oklch, var(--foreground) 3.5%, transparent);
		user-select: none;
		pointer-events: none;
		letter-spacing: -0.06em;
		line-height: 1;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		white-space: nowrap;
	}
	.quote { position: relative; font-size: 2rem; line-height: 1.1; color: var(--foreground); }
	.quote em { color: var(--primary); }
	.desc { position: relative; font-size: 0.88rem; line-height: 1.65; color: var(--muted-foreground); max-width: 28rem; }
	.desc em { color: var(--foreground); font-style: italic; }
	.back { position: relative; font-size: 0.7rem; color: var(--primary); letter-spacing: 0.04em; text-decoration: none; }
	.back:hover { text-decoration: underline; text-underline-offset: 4px; }
</style>
