<script lang="ts">
	import type { UIMessage } from 'ai';
	import { Icon } from '$lib/icons';

	type Part = NonNullable<UIMessage['parts']>[number];

	interface Props {
		part: Part;
	}

	let { part }: Props = $props();

	type ToolPart = Part & { type: `tool-${string}` };

	function isToolPart(p: Part): p is ToolPart {
		return typeof p.type === 'string' && p.type.startsWith('tool-');
	}

	function partState(p: ToolPart): string | undefined {
		return (p as { state?: string }).state;
	}

	function partInput(p: ToolPart): unknown {
		return (p as { input?: unknown }).input;
	}

	function partOutput(p: ToolPart): unknown {
		return (p as { output?: unknown }).output;
	}

	function partError(p: ToolPart): string | undefined {
		return (p as { errorText?: string }).errorText;
	}

	const tool = $derived(isToolPart(part) ? part : null);
	const toolName = $derived(tool ? tool.type.slice('tool-'.length) : '');
	const toolState = $derived(tool ? partState(tool) : undefined);
	const input = $derived(tool ? partInput(tool) : undefined);
	const output = $derived(tool ? partOutput(tool) : undefined);
	const errorText = $derived(tool ? partError(tool) : undefined);

	const isRunning = $derived(
		toolState === 'input-streaming' || toolState === 'input-available'
	);
	const isError = $derived(toolState === 'output-error' || !!errorText);
	const isDone = $derived(toolState === 'output-available');

	let inputOpen = $state(false);
	let outputOpen = $state(false);

	function pretty(v: unknown): string {
		if (v == null) return '';
		if (typeof v === 'string') return v;
		try {
			return JSON.stringify(v, null, 2);
		} catch {
			return String(v);
		}
	}
</script>

{#if tool}
	<div class="tool-card" class:running={isRunning} class:done={isDone} class:error={isError}>
		<div class="tool-head">
			<span class="tool-icon">
				{#if isRunning}
					<span class="spinner" aria-label="running"></span>
				{:else if isError}
					<Icon icon="oc:error" width={11} height={11} />
				{:else}
					<Icon icon="tabler:check" width={11} height={11} />
				{/if}
			</span>
			<span class="tool-name font-mono">{toolName}</span>
			<span class="tool-status font-mono">
				{#if isRunning}running…{:else if isError}failed{:else}done{/if}
			</span>
		</div>

		{#if input !== undefined}
			<button
				type="button"
				class="tool-section-toggle font-mono"
				onclick={() => (inputOpen = !inputOpen)}
				aria-expanded={inputOpen}
			>
				<Icon
					icon={inputOpen ? 'tabler:chevron-down' : 'tabler:chevron-right'}
					width={10}
					height={10}
				/>
				<span>input</span>
			</button>
			{#if inputOpen}
				<pre class="tool-payload">{pretty(input)}</pre>
			{/if}
		{/if}

		{#if isError && errorText}
			<pre class="tool-error">{errorText}</pre>
		{:else if output !== undefined}
			<button
				type="button"
				class="tool-section-toggle font-mono"
				onclick={() => (outputOpen = !outputOpen)}
				aria-expanded={outputOpen}
			>
				<Icon
					icon={outputOpen ? 'tabler:chevron-down' : 'tabler:chevron-right'}
					width={10}
					height={10}
				/>
				<span>output</span>
			</button>
			{#if outputOpen}
				<pre class="tool-payload">{pretty(output)}</pre>
			{/if}
		{/if}
	</div>
{/if}

<style>
	.tool-card {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
		padding: 0.6rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: 0.5rem;
		background: color-mix(in oklch, var(--card) 60%, transparent);
		font-size: 0.78rem;
	}
	.tool-card.running {
		border-color: color-mix(in oklch, var(--primary) 40%, var(--border));
	}
	.tool-card.done {
		border-color: color-mix(in oklch, var(--border) 80%, transparent);
	}
	.tool-card.error {
		border-color: color-mix(in oklch, var(--destructive) 40%, var(--border));
		background: color-mix(in oklch, var(--destructive) 6%, transparent);
	}

	.tool-head {
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}

	.tool-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 14px;
		height: 14px;
	}

	.tool-name {
		font-size: 0.74rem;
		color: var(--foreground);
	}

	.tool-status {
		margin-left: auto;
		font-size: 0.62rem;
		letter-spacing: 0.04em;
		color: var(--muted-foreground);
	}

	.tool-section-toggle {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		font-size: 0.62rem;
		color: var(--muted-foreground);
		padding: 0.05rem 0;
		width: fit-content;
	}
	.tool-section-toggle:hover {
		color: var(--foreground);
	}

	.tool-payload {
		margin: 0;
		padding: 0.5rem 0.6rem;
		font-family: var(--font-mono);
		font-size: 0.7rem;
		line-height: 1.45;
		color: color-mix(in oklch, var(--foreground) 80%, transparent);
		background: color-mix(in oklch, var(--foreground) 4%, transparent);
		border-radius: 0.3rem;
		overflow-x: auto;
		white-space: pre-wrap;
		word-break: break-word;
	}

	.tool-error {
		margin: 0;
		padding: 0.5rem 0.6rem;
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--destructive);
		background: color-mix(in oklch, var(--destructive) 6%, transparent);
		border-radius: 0.3rem;
		white-space: pre-wrap;
	}

	.spinner {
		width: 9px;
		height: 9px;
		border-radius: 9999px;
		border: 1.5px solid var(--primary);
		border-right-color: transparent;
		animation: tool-spin 0.75s linear infinite;
	}
	@keyframes tool-spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
