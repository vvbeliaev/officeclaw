<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { EditorView, keymap, lineNumbers, highlightActiveLine, drawSelection } from '@codemirror/view';
	import type { ViewUpdate } from '@codemirror/view';
	import { EditorState, Compartment } from '@codemirror/state';
	import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands';
	import { syntaxHighlighting, defaultHighlightStyle, indentOnInput, bracketMatching } from '@codemirror/language';
	import { python } from '@codemirror/lang-python';
	import { json } from '@codemirror/lang-json';
	import { markdown } from '@codemirror/lang-markdown';
	import { yaml } from '@codemirror/lang-yaml';

	type Props = {
		path: string;
		content: string;
		onsave?: (content: string) => void;
		onchange?: (content: string) => void;
	};

	let { path, content, onsave, onchange }: Props = $props();

	let container: HTMLDivElement;
	let view: EditorView | null = null;
	let langCompartment = new Compartment();

	function getLang(p: string) {
		const ext = p.split('.').at(-1) ?? '';
		if (ext === 'py') return python();
		if (ext === 'json') return json();
		if (ext === 'md') return markdown();
		if (ext === 'yaml' || ext === 'yml') return yaml();
		return [];
	}

	function save() {
		if (view && onsave) onsave(view.state.doc.toString());
	}

	const saveKeymap = keymap.of([
		{ key: 'Mod-s', run: () => { save(); return true; } }
	]);

	const theme = EditorView.theme({
		'&': {
			height: '100%',
			fontSize: '0.76rem',
			fontFamily: 'var(--font-mono)',
			background: 'transparent',
		},
		'.cm-scroller': {
			overflow: 'auto',
			lineHeight: '1.65',
			padding: '0.75rem 0',
		},
		'.cm-content': {
			padding: '0 1.25rem',
			caretColor: 'var(--foreground)',
		},
		'.cm-line': { padding: '0' },
		'.cm-gutters': {
			background: 'transparent',
			border: 'none',
			color: 'color-mix(in oklch, var(--foreground) 25%, transparent)',
			paddingLeft: '0.75rem',
			paddingRight: '0.5rem',
			minWidth: '2.5rem',
		},
		'.cm-activeLineGutter': { background: 'transparent' },
		'.cm-activeLine': {
			background: 'color-mix(in oklch, var(--foreground) 4%, transparent)',
		},
		'.cm-selectionBackground, ::selection': {
			background: 'color-mix(in oklch, var(--primary) 22%, transparent) !important',
		},
		'.cm-cursor': {
			borderLeftColor: 'var(--foreground)',
			borderLeftWidth: '1.5px',
		},
		'.cm-matchingBracket': {
			background: 'color-mix(in oklch, var(--primary) 15%, transparent)',
			outline: 'none',
		},
	});

	const changeListener = EditorView.updateListener.of((update: ViewUpdate) => {
		if (update.docChanged && onchange) {
			onchange(update.state.doc.toString());
		}
	});

	onMount(() => {
		view = new EditorView({
			state: EditorState.create({
				doc: content,
				extensions: [
					history(),
					drawSelection(),
					lineNumbers(),
					highlightActiveLine(),
					indentOnInput(),
					bracketMatching(),
					syntaxHighlighting(defaultHighlightStyle),
					langCompartment.of(getLang(path)),
					keymap.of([...defaultKeymap, ...historyKeymap, indentWithTab]),
					saveKeymap,
					changeListener,
					theme,
					EditorView.lineWrapping,
				],
			}),
			parent: container,
		});
	});

	onDestroy(() => view?.destroy());

	// Swap language when file changes
	$effect(() => {
		if (view && path) {
			view.dispatch({ effects: langCompartment.reconfigure(getLang(path)) });
		}
	});

	// Replace content when a different file is selected
	$effect(() => {
		if (view && content !== undefined) {
			const current = view.state.doc.toString();
			if (current !== content) {
				view.dispatch({
					changes: { from: 0, to: current.length, insert: content }
				});
			}
		}
	});
</script>

<div class="editor-wrap" bind:this={container}></div>

<style>
	.editor-wrap {
		height: 100%;
		overflow: hidden;
	}

	/* syntax token colours — use CSS vars so they respect dark/light */
	:global(.ck-keyword)   { color: color-mix(in oklch, var(--primary) 85%, var(--foreground)); font-weight: 500; }
	:global(.ck-string)    { color: color-mix(in oklch, var(--primary) 55%, #5c9e6e); }
	:global(.ck-comment)   { color: color-mix(in oklch, var(--foreground) 38%, transparent); font-style: italic; }
	:global(.ck-number)    { color: color-mix(in oklch, var(--primary) 60%, #d07020); }
	:global(.ck-operator)  { color: var(--foreground); }
</style>
