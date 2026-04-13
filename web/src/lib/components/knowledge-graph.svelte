<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import Graph from 'graphology';
	import Sigma from 'sigma';
	import forceAtlas2 from 'graphology-layout-forceatlas2';

	type GraphNode = { id: string; type: string; description: string };
	type GraphEdge = { source: string; target: string; label: string; weight: number };
	type GraphData = { nodes: GraphNode[]; edges: GraphEdge[] };

	// ── Colour palette by entity type ─────────────────────
	const TYPE_COLORS: Record<string, string> = {
		PERSON: '#a78bfa',
		ORGANIZATION: '#60a5fa',
		CONCEPT: '#34d399',
		LOCATION: '#fb923c',
		EVENT: '#f472b6',
		TECHNOLOGY: '#22d3ee',
		PRODUCT: '#facc15',
		CATEGORY: '#a3e635',
		MISC: '#94a3b8'
	};

	function colorFor(type: string): string {
		return TYPE_COLORS[type?.toUpperCase()] ?? '#6b7280';
	}

	let container: HTMLDivElement;
	let renderer: Sigma | null = null;

	let loading = $state(true);
	let error = $state('');
	let nodeCount = $state(0);
	let edgeCount = $state(0);
	let layoutRunning = $state(false);
	let searchQuery = $state('');
	let hoveredNode = $state<string | null>(null);
	let hoveredAttr = $state<{ type: string; description: string } | null>(null);

	// ── Internal graph instance (non-reactive) ─────────────
	let g: Graph | null = null;
	// Store original colors separately so we can restore without reading stale attrs
	const origColors = new Map<string, string>();

	async function loadGraph() {
		loading = true;
		error = '';
		try {
			const res = await fetch('/api/knowledge/graph');
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			const data: GraphData = await res.json();

			if (!data.nodes.length) {
				loading = false;
				return;
			}

			buildSigma(data);
		} catch (e) {
			error = e instanceof Error ? e.message : 'unknown error';
		} finally {
			loading = false;
		}
	}

	function buildSigma(data: GraphData) {
		if (renderer) {
			renderer.kill();
			renderer = null;
		}

		g = new Graph({ multi: false, type: 'mixed' });

		// degree for node sizing
		const deg: Record<string, number> = {};
		data.edges.forEach((e) => {
			deg[e.source] = (deg[e.source] ?? 0) + 1;
			deg[e.target] = (deg[e.target] ?? 0) + 1;
		});

		// add nodes with random positions
		data.nodes.forEach((n) => {
			const color = colorFor(n.type);
			origColors.set(n.id, color);
			g!.addNode(n.id, {
				label: n.id,
				size: Math.max(4, 3 + (deg[n.id] ?? 0) * 2),
				color,
				x: (Math.random() - 0.5) * 100,
				y: (Math.random() - 0.5) * 100,
				nodeType: n.type,
				description: n.description
			});
		});

		// add edges
		data.edges.forEach((e) => {
			if (g!.hasNode(e.source) && g!.hasNode(e.target) && !g!.hasEdge(e.source, e.target)) {
				g!.addEdge(e.source, e.target, {
					label: e.label,
					size: Math.max(0.5, e.weight * 0.6),
					color: 'rgba(255,255,255,0.06)'
				});
			}
		});

		nodeCount = g.order;
		edgeCount = g.size;

		// ForceAtlas2 — run synchronously for a few hundred iterations to get initial layout
		forceAtlas2.assign(g, {
			iterations: 150,
			settings: {
				...forceAtlas2.inferSettings(g),
				gravity: 1,
				scalingRatio: 2
			}
		});

		renderer = new Sigma(g, container, {
			renderEdgeLabels: false,
			defaultEdgeColor: 'rgba(255,255,255,0.06)',
			labelColor: { color: '#9ca3af' },
			labelSize: 11,
			labelWeight: '400',
			minCameraRatio: 0.05,
			maxCameraRatio: 10,
			allowInvalidContainer: true,
			// Override hover renderer: replace white background with dark theme
			defaultDrawNodeHover(ctx, data, settings) {
				const size = settings.labelSize;
				const font = settings.labelFont;
				const weight = settings.labelWeight;
				ctx.font = `${weight} ${size}px ${font}`;

				// Dark bubble instead of white
				ctx.fillStyle = '#1a1a1a';
				ctx.shadowOffsetX = 0;
				ctx.shadowOffsetY = 0;
				ctx.shadowBlur = 12;
				ctx.shadowColor = 'rgba(0,0,0,0.8)';

				const PADDING = 2;
				if (typeof data.label === 'string') {
					const textWidth = ctx.measureText(data.label).width;
					const boxWidth = Math.round(textWidth + 5);
					const boxHeight = Math.round(size + 2 * PADDING);
					const radius = Math.max(data.size, size / 2) + PADDING;
					const angleRadian = Math.asin(boxHeight / 2 / radius);
					const xDeltaCoord = Math.sqrt(Math.abs(radius ** 2 - (boxHeight / 2) ** 2));

					ctx.beginPath();
					ctx.moveTo(data.x + xDeltaCoord, data.y + boxHeight / 2);
					ctx.lineTo(data.x + radius + boxWidth, data.y + boxHeight / 2);
					ctx.lineTo(data.x + radius + boxWidth, data.y - boxHeight / 2);
					ctx.lineTo(data.x + xDeltaCoord, data.y - boxHeight / 2);
					ctx.arc(data.x, data.y, radius, angleRadian, -angleRadian);
					ctx.closePath();
					ctx.fill();
				} else {
					ctx.beginPath();
					ctx.arc(data.x, data.y, data.size + PADDING, 0, Math.PI * 2);
					ctx.closePath();
					ctx.fill();
				}

				ctx.shadowOffsetX = 0;
				ctx.shadowOffsetY = 0;
				ctx.shadowBlur = 0;

				// Border ring
				ctx.strokeStyle = 'rgba(255,255,255,0.15)';
				ctx.lineWidth = 1;
				ctx.beginPath();
				ctx.arc(data.x, data.y, data.size + PADDING, 0, Math.PI * 2);
				ctx.closePath();
				ctx.stroke();

				// Label text
				if (typeof data.label === 'string') {
					ctx.fillStyle = '#e8e6e3';
					ctx.font = `${weight} ${size}px ${font}`;
					ctx.fillText(data.label, data.x + data.size + 3, data.y + size / 3);
				}
			}
		});

		layoutRunning = false;

		// hover — highlight neighbours
		renderer.on('enterNode', ({ node }) => {
			hoveredNode = node;
			const attr = g!.getNodeAttributes(node);
			hoveredAttr = { type: attr.nodeType, description: attr.description };

			const neighbours = new Set<string>(g!.neighbors(node));
			neighbours.add(node);

			g!.forEachNode((n) => {
				g!.setNodeAttribute(n, 'color', neighbours.has(n) ? origColors.get(n) : 'rgba(255,255,255,0.06)');
			});
			g!.forEachEdge((e, _a, s, t) => {
				const connected = s === node || t === node;
				g!.setEdgeAttribute(e, 'color', connected ? 'rgba(255,255,255,0.25)' : 'rgba(255,255,255,0.02)');
			});
			renderer!.refresh();
		});

		renderer.on('leaveNode', () => {
			hoveredNode = null;
			hoveredAttr = null;
			restoreColors();
		});
	}

	function restoreColors() {
		if (!g || !renderer) return;
		applySearch(searchQuery);
	}

	function applySearch(q: string) {
		if (!g || !renderer) return;
		const query = q.trim().toLowerCase();

		g.forEachNode((n) => {
			const match = !query || n.toLowerCase().includes(query);
			g!.setNodeAttribute(n, 'color', match ? origColors.get(n) : 'rgba(255,255,255,0.05)');
		});
		g.forEachEdge((e) => {
			g!.setEdgeAttribute(e, 'color', 'rgba(255,255,255,0.06)');
		});
		renderer.refresh();
	}

	$effect(() => {
		if (hoveredNode === null) applySearch(searchQuery);
	});

	function rerunLayout() {
		if (!g || !renderer || layoutRunning) return;
		layoutRunning = true;
		// Run more FA2 iterations
		forceAtlas2.assign(g, {
			iterations: 200,
			settings: { ...forceAtlas2.inferSettings(g), gravity: 1, scalingRatio: 2 }
		});
		renderer.refresh();
		layoutRunning = false;
	}

	onMount(() => {
		loadGraph();
	});

	onDestroy(() => {
		renderer?.kill();
	});
</script>

<div class="graph-root">
	<!-- toolbar -->
	<div class="toolbar">
		<div class="stat font-mono"><span class="val">{nodeCount}</span> nodes</div>
		<div class="stat font-mono"><span class="val">{edgeCount}</span> edges</div>
		<button class="tool-btn font-mono" onclick={rerunLayout} disabled={layoutRunning || loading}>
			{layoutRunning ? 'laying out…' : 're-layout'}
		</button>
		<button class="tool-btn font-mono" onclick={loadGraph} disabled={loading}>
			{loading ? 'loading…' : 'refresh'}
		</button>
	</div>

	<!-- search -->
	<div class="search-wrap">
		<input
			class="search font-mono"
			bind:value={searchQuery}
			placeholder="search nodes…"
			oninput={() => applySearch(searchQuery)}
		/>
	</div>

	<!-- canvas -->
	<div class="canvas-wrap" bind:this={container}></div>

	<!-- loading / empty states -->
	{#if loading}
		<div class="overlay">
			<div class="spinner"></div>
			<p class="overlay-text font-mono">loading graph…</p>
		</div>
	{:else if error}
		<div class="overlay">
			<p class="overlay-text font-mono err">{error}</p>
			<button class="tool-btn font-mono" onclick={loadGraph}>retry</button>
		</div>
	{:else if nodeCount === 0}
		<div class="overlay">
			<p class="overlay-text font-mono">no graph yet — ingest some content first.</p>
		</div>
	{/if}

	<!-- hover tooltip -->
	{#if hoveredNode && hoveredAttr}
		<div class="tooltip">
			<div class="tt-type font-mono">{hoveredAttr.type}</div>
			<div class="tt-label">{hoveredNode}</div>
			{#if hoveredAttr.description}
				<div class="tt-desc">{hoveredAttr.description}</div>
			{/if}
		</div>
	{/if}

	<!-- legend -->
	<div class="legend">
		{#each Object.entries(TYPE_COLORS) as [type, color]}
			<div class="legend-item">
				<span class="legend-dot" style="background:{color}"></span>
				<span class="font-mono">{type}</span>
			</div>
		{/each}
	</div>
</div>

<style>
	.graph-root {
		position: relative;
		flex: 1;
		display: flex;
		flex-direction: column;
		min-height: 0;
		overflow: hidden;
	}

	/* ── Canvas ───────────────────────────────────────── */
	.canvas-wrap {
		flex: 1;
		min-height: 0;
		background: var(--background, #0d0d0d);
	}

	/* Sigma injects canvas elements — keep them transparent so .canvas-wrap bg shows */
	.canvas-wrap :global(canvas) {
		background: transparent !important;
	}

	/* Sigma label layer uses a separate div — make it readable on dark bg */
	.canvas-wrap :global(.sigma-labels) {
		color: #9ca3af;
	}

	/* ── Toolbar ─────────────────────────────────────── */
	.toolbar {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1.5rem;
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
	}

	.stat {
		font-size: 0.6rem;
		letter-spacing: 0.08em;
		color: color-mix(in oklch, var(--foreground) 35%, transparent);
		padding: 0.2rem 0.6rem;
		border: 1px solid var(--border);
		border-radius: 0.2rem;
	}

	.stat .val {
		color: var(--foreground);
	}

	.tool-btn {
		font-size: 0.6rem;
		letter-spacing: 0.08em;
		padding: 0.2rem 0.65rem;
		border: 1px solid var(--border);
		border-radius: 0.2rem;
		color: color-mix(in oklch, var(--foreground) 45%, transparent);
		transition: color 120ms ease, border-color 120ms ease;
	}

	.tool-btn:hover:not(:disabled) {
		color: var(--foreground);
		border-color: color-mix(in oklch, var(--foreground) 40%, transparent);
	}

	.tool-btn:disabled {
		opacity: 0.4;
		cursor: default;
	}

	/* ── Search ──────────────────────────────────────── */
	.search-wrap {
		position: absolute;
		top: 3.2rem;
		right: 1.5rem;
		z-index: 10;
	}

	.search {
		font-size: 0.68rem;
		background: color-mix(in oklch, var(--background, #0d0d0d) 90%, transparent);
		border: 1px solid var(--border);
		border-radius: 0.25rem;
		padding: 0.3rem 0.75rem;
		color: var(--foreground);
		outline: none;
		width: 180px;
		transition: border-color 150ms ease;
		backdrop-filter: blur(6px);
	}

	.search::placeholder {
		color: color-mix(in oklch, var(--foreground) 22%, transparent);
	}

	.search:focus {
		border-color: color-mix(in oklch, var(--foreground) 40%, transparent);
	}

	/* ── Overlay (loading / empty / error) ───────────── */
	.overlay {
		position: absolute;
		inset: 3rem 0 0 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		pointer-events: none;
	}

	.overlay-text {
		font-size: 0.72rem;
		letter-spacing: 0.06em;
		color: color-mix(in oklch, var(--foreground) 30%, transparent);
	}

	.overlay-text.err {
		color: var(--destructive, #e05555);
	}

	.spinner {
		width: 20px;
		height: 20px;
		border-radius: 50%;
		border: 1.5px solid color-mix(in oklch, var(--foreground) 15%, transparent);
		border-top-color: color-mix(in oklch, var(--foreground) 60%, transparent);
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* ── Tooltip ─────────────────────────────────────── */
	.tooltip {
		position: absolute;
		bottom: 1.5rem;
		left: 1.5rem;
		background: color-mix(in oklch, var(--background, #111) 95%, transparent);
		border: 1px solid var(--border);
		border-radius: 0.4rem;
		padding: 0.75rem 1rem;
		z-index: 20;
		max-width: 260px;
		backdrop-filter: blur(8px);
		pointer-events: none;
	}

	.tt-type {
		font-size: 0.55rem;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--primary);
		margin-bottom: 0.2rem;
	}

	.tt-label {
		font-size: 0.82rem;
		font-weight: 600;
		color: var(--foreground);
		margin-bottom: 0.3rem;
	}

	.tt-desc {
		font-size: 0.7rem;
		color: color-mix(in oklch, var(--foreground) 50%, transparent);
		line-height: 1.5;
	}

	/* ── Legend ──────────────────────────────────────── */
	.legend {
		position: absolute;
		bottom: 1.5rem;
		right: 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
		z-index: 10;
		pointer-events: none;
	}

	.legend-item {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.56rem;
		letter-spacing: 0.08em;
		color: color-mix(in oklch, var(--foreground) 35%, transparent);
	}

	.legend-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		flex-shrink: 0;
	}
</style>
