<script lang="ts">
	import { marked, Renderer } from 'marked';

	let { text, streaming = false }: { text: string; streaming?: boolean } = $props();

	// Custom renderer — open links in new tab, strip dangerous attrs
	const renderer = new Renderer();
	renderer.link = ({ href, title, text: label }) =>
		`<a href="${href}"${title ? ` title="${title}"` : ''} target="_blank" rel="noopener noreferrer">${label}</a>`;

	const html = $derived.by(() => {
		const src = streaming ? text : text; // same for now; streaming branch reserved for cursor
		return marked.parse(src, { renderer, async: false, breaks: true }) as string;
	});
</script>

<div class="md">
	{@html html}
	{#if streaming}<span class="cursor">▋</span>{/if}
</div>

<style>
	.md {
		font-size: 0.975rem;
		line-height: 1.7;
		color: var(--foreground);
		word-wrap: break-word;
	}

	/* ── Paragraphs ──────────────────────────────────────────── */
	.md :global(p) {
		margin: 0.6em 0;
	}
	.md :global(p:first-child) { margin-top: 0; }
	.md :global(p:last-child)  { margin-bottom: 0; }

	/* ── Inline ──────────────────────────────────────────────── */
	.md :global(strong) {
		font-weight: 620;
		color: var(--foreground);
	}
	.md :global(em) {
		font-style: italic;
	}
	.md :global(del) {
		text-decoration: line-through;
		opacity: 0.55;
	}

	/* ── Headings ────────────────────────────────────────────── */
	.md :global(h1),
	.md :global(h2),
	.md :global(h3) {
		font-family: var(--font-display);
		letter-spacing: -0.01em;
		line-height: 1.15;
		margin: 1.4em 0 0.45em;
		color: var(--foreground);
	}
	.md :global(h1:first-child),
	.md :global(h2:first-child),
	.md :global(h3:first-child) { margin-top: 0; }

	.md :global(h1) {
		font-size: 1.45rem;
		font-variation-settings: 'opsz' 36, 'wght' 720;
	}
	.md :global(h2) {
		font-size: 1.15rem;
		font-variation-settings: 'opsz' 24, 'wght' 680;
	}
	.md :global(h3) {
		font-size: 1rem;
		font-variation-settings: 'opsz' 18, 'wght' 640;
	}

	/* ── Lists ───────────────────────────────────────────────── */
	.md :global(ul),
	.md :global(ol) {
		margin: 0.55em 0;
		padding-left: 1.5em;
	}
	.md :global(li) {
		margin: 0.25em 0;
	}
	.md :global(li > p) {
		margin: 0.2em 0;
	}
	.md :global(ul) {
		list-style: none;
		padding-left: 1.25em;
	}
	.md :global(ul > li::before) {
		content: '–';
		position: absolute;
		margin-left: -1.1em;
		color: var(--primary);
		opacity: 0.7;
	}
	.md :global(ul > li) {
		position: relative;
	}
	.md :global(ol) {
		list-style: decimal;
	}
	.md :global(ol > li::marker) {
		color: var(--primary);
		opacity: 0.7;
		font-family: var(--font-mono);
		font-size: 0.85em;
	}

	/* ── Code — inline ───────────────────────────────────────── */
	.md :global(code:not(pre > code)) {
		font-family: var(--font-mono);
		font-size: 0.85em;
		padding: 0.12em 0.38em;
		border-radius: 0.25rem;
		background: color-mix(in oklch, var(--primary) 9%, var(--card));
		border: 1px solid color-mix(in oklch, var(--primary) 15%, var(--border));
		color: color-mix(in oklch, var(--primary) 70%, var(--foreground));
	}

	/* ── Code — blocks ───────────────────────────────────────── */
	.md :global(pre) {
		margin: 0.85em 0;
		padding: 1rem 1.1rem;
		border-radius: 0.5rem;
		background: oklch(0.10 0.014 55);
		border: 1px solid oklch(1 0 0 / 7%);
		overflow-x: auto;
	}
	.md :global(pre > code) {
		font-family: var(--font-mono);
		font-size: 0.82rem;
		line-height: 1.65;
		color: oklch(0.84 0.012 80);
		background: none;
		border: none;
		padding: 0;
	}

	/* ── Blockquote ──────────────────────────────────────────── */
	.md :global(blockquote) {
		margin: 0.75em 0;
		padding: 0.1em 0 0.1em 1rem;
		border-left: 3px solid color-mix(in oklch, var(--primary) 45%, transparent);
		color: var(--muted-foreground);
	}
	.md :global(blockquote > p) {
		font-style: italic;
	}

	/* ── Links ───────────────────────────────────────────────── */
	.md :global(a) {
		color: var(--primary);
		text-decoration: underline;
		text-underline-offset: 3px;
		text-decoration-thickness: 1px;
		transition: opacity 120ms ease;
	}
	.md :global(a:hover) {
		opacity: 0.75;
	}

	/* ── Horizontal rule ─────────────────────────────────────── */
	.md :global(hr) {
		border: none;
		border-top: 1px solid var(--border);
		margin: 1.25em 0;
	}

	/* ── Tables ──────────────────────────────────────────────── */
	.md :global(table) {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.875em;
		margin: 0.85em 0;
	}
	.md :global(th) {
		font-weight: 600;
		text-align: left;
		padding: 0.45em 0.75em;
		border-bottom: 1px solid var(--border);
		color: var(--muted-foreground);
		font-family: var(--font-mono);
		font-size: 0.8em;
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}
	.md :global(td) {
		padding: 0.4em 0.75em;
		border-bottom: 1px solid color-mix(in oklch, var(--border) 50%, transparent);
	}
	.md :global(tr:last-child > td) {
		border-bottom: none;
	}

	/* ── Streaming cursor ────────────────────────────────────── */
	.cursor {
		display: inline-block;
		color: var(--primary);
		animation: cursor-blink 1.1s ease-in-out infinite;
		margin-left: 1px;
		font-family: var(--font-mono);
		font-size: 0.85em;
		vertical-align: baseline;
	}
	@keyframes cursor-blink {
		0%, 100% { opacity: 1; }
		50%       { opacity: 0.1; }
	}
</style>
