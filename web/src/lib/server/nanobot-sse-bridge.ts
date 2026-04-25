/**
 * Bridge nanobot's SSE stream to Vercel AI SDK UIMessage chunks.
 *
 * Nanobot emits two interleaved channels in `/v1/chat/completions?stream=true`:
 *
 * 1. Standard OpenAI delta chunks (no `event:` line, just `data: {...}`):
 *    - `delta.content` → text deltas
 *    - `delta.tool_calls[]` → streamed tool-call args (per-index accumulation)
 *
 * 2. Custom `event: nanobot.*` lines for things outside the OpenAI spec:
 *    - `nanobot.tool_execution_start` → server-side execution began
 *    - `nanobot.tool_result` → server-side execution finished (no analogue
 *      in OpenAI streaming — nanobot runs tools internally, AI SDK never
 *      sees results otherwise)
 *    - `nanobot.reasoning_delta` → model reasoning chunks (Kimi/DeepSeek/etc.)
 *
 * Output: AI SDK `UIMessageChunk` events ready to feed a
 * `createUIMessageStream` writer. Lifecycle is per-tool-call: tool-input-start
 * → many tool-input-delta → tool-input-available → tool-output-available
 * (or tool-output-error). Text and reasoning each open exactly one block per
 * stream and emit deltas until the upstream finishes.
 */

import type { UIMessage, UIMessageStreamWriter } from 'ai';

type NanobotEventName =
	| 'nanobot.tool_execution_start'
	| 'nanobot.tool_result'
	| 'nanobot.reasoning_delta';

interface OpenAIToolCallDelta {
	index: number;
	id?: string;
	type?: 'function';
	function?: { name?: string; arguments?: string };
}

interface OpenAIDelta {
	role?: string;
	content?: string;
	tool_calls?: OpenAIToolCallDelta[];
}

interface OpenAIChunk {
	choices?: Array<{ delta?: OpenAIDelta; finish_reason?: string | null }>;
}

interface NanobotToolResult {
	call_id: string;
	name: string;
	result: string;
	error: string | null;
}

interface NanobotReasoningDelta {
	delta: string;
}

interface ParsedSseEvent {
	event: NanobotEventName | undefined;
	data: string;
}

/** Parse a raw SSE byte stream into discrete `event:`/`data:` records. */
async function* parseSseStream(body: ReadableStream<Uint8Array>): AsyncGenerator<ParsedSseEvent> {
	const reader = body.getReader();
	const decoder = new TextDecoder('utf-8');
	let buffer = '';

	try {
		while (true) {
			const { value, done } = await reader.read();
			if (done) break;
			buffer += decoder.decode(value, { stream: true });

			// SSE record separator is a blank line.
			let sep: number;
			while ((sep = buffer.indexOf('\n\n')) !== -1) {
				const raw = buffer.slice(0, sep);
				buffer = buffer.slice(sep + 2);
				yield parseRecord(raw);
			}
		}
		// Flush trailing record without a final blank line.
		const tail = buffer.trim();
		if (tail) yield parseRecord(tail);
	} finally {
		reader.releaseLock();
	}
}

function parseRecord(raw: string): ParsedSseEvent {
	let event: NanobotEventName | undefined;
	const dataLines: string[] = [];
	for (const line of raw.split('\n')) {
		if (line.startsWith('event:')) {
			event = line.slice(6).trim() as NanobotEventName;
		} else if (line.startsWith('data:')) {
			dataLines.push(line.slice(5).trimStart());
		}
	}
	return { event, data: dataLines.join('\n') };
}

/**
 * Drive a single nanobot SSE stream into AI SDK UIMessage chunks via *writer*.
 *
 * Side effects only — caller controls when to send `start` / `finish` chunks
 * around this call (createUIMessageStream emits those automatically when
 * `originalMessages` is set).
 */
export async function pipeNanobotSseToUiStream<UI_MESSAGE extends UIMessage>(
	body: ReadableStream<Uint8Array>,
	writer: UIMessageStreamWriter<UI_MESSAGE>,
	options: { textBlockId?: string; reasoningBlockId?: string } = {}
): Promise<void> {
	const textId = options.textBlockId ?? 'text-0';
	const reasoningId = options.reasoningBlockId ?? 'reasoning-0';

	let textOpen = false;
	let reasoningOpen = false;

	// Per-call accumulator: index → {id, name, args}.
	// Args are streamed in pieces; we tell the UI when input is "available"
	// the moment execution starts (nanobot.tool_execution_start), since that
	// signal is the authoritative "args are final, tool is dispatched".
	const toolCalls = new Map<
		number,
		{ id: string; name: string; argsBuffer: string; inputEmitted: boolean }
	>();
	const toolByCallId = new Map<string, { id: string; name: string; args: unknown }>();

	// The helpers below pass `unknown` chunks because they are shape-aware
	// only for the AI-SDK wire format; the writer's generic narrowing is
	// satisfied by the `as never` casts at every write site.
	const writeChunk = (chunk: unknown) => writer.write(chunk as never);

	const ensureTextOpen = () => {
		if (!textOpen) {
			writeChunk({ type: 'text-start', id: textId } as never);
			textOpen = true;
		}
	};
	const ensureReasoningOpen = () => {
		if (!reasoningOpen) {
			writeChunk({ type: 'reasoning-start', id: reasoningId } as never);
			reasoningOpen = true;
		}
	};

	for await (const evt of parseSseStream(body)) {
		// Standard OpenAI chunk (no event: line).
		if (evt.event === undefined) {
			if (evt.data === '[DONE]' || !evt.data) continue;
			let chunk: OpenAIChunk;
			try {
				chunk = JSON.parse(evt.data);
			} catch {
				continue;
			}
			const delta = chunk.choices?.[0]?.delta;
			if (!delta) continue;

			if (delta.content) {
				ensureTextOpen();
				writeChunk({ type: 'text-delta', id: textId, delta: delta.content } as never);
			}

			if (delta.tool_calls) {
				for (const tc of delta.tool_calls) {
					handleToolCallDelta(tc, toolCalls, writeChunk);
				}
			}
			continue;
		}

		// Custom nanobot events.
		if (evt.event === 'nanobot.tool_execution_start') {
			let payload: { call_id: string; name: string; arguments: unknown };
			try {
				payload = JSON.parse(evt.data);
			} catch {
				continue;
			}
			emitToolInputAvailable(payload, toolCalls, toolByCallId, writeChunk);
			continue;
		}

		if (evt.event === 'nanobot.tool_result') {
			let payload: NanobotToolResult;
			try {
				payload = JSON.parse(evt.data);
			} catch {
				continue;
			}
			if (payload.error) {
				writeChunk({
					type: 'tool-output-error',
					toolCallId: payload.call_id,
					errorText: payload.error
				} as never);
			} else {
				writeChunk({
					type: 'tool-output-available',
					toolCallId: payload.call_id,
					output: payload.result
				} as never);
			}
			continue;
		}

		if (evt.event === 'nanobot.reasoning_delta') {
			let payload: NanobotReasoningDelta;
			try {
				payload = JSON.parse(evt.data);
			} catch {
				continue;
			}
			if (payload.delta) {
				ensureReasoningOpen();
				writeChunk({ type: 'reasoning-delta', id: reasoningId, delta: payload.delta } as never);
			}
			continue;
		}
	}

	if (textOpen) writeChunk({ type: 'text-end', id: textId } as never);
	if (reasoningOpen) writeChunk({ type: 'reasoning-end', id: reasoningId } as never);
}

function handleToolCallDelta(
	tc: OpenAIToolCallDelta,
	toolCalls: Map<number, { id: string; name: string; argsBuffer: string; inputEmitted: boolean }>,
	write: (chunk: unknown) => void
): void {
	const idx = tc.index;
	let entry = toolCalls.get(idx);

	// First chunk for this index always carries the id+name in OpenAI format.
	if (!entry && tc.id && tc.function?.name) {
		entry = { id: tc.id, name: tc.function.name, argsBuffer: '', inputEmitted: false };
		toolCalls.set(idx, entry);
		write({ type: 'tool-input-start', toolCallId: entry.id, toolName: entry.name });
	}
	if (!entry) return;

	const argsDelta = tc.function?.arguments;
	if (argsDelta) {
		entry.argsBuffer += argsDelta;
		write({ type: 'tool-input-delta', toolCallId: entry.id, inputTextDelta: argsDelta });
	}
}

function emitToolInputAvailable(
	payload: { call_id: string; name: string; arguments: unknown },
	toolCalls: Map<number, { id: string; name: string; argsBuffer: string; inputEmitted: boolean }>,
	toolByCallId: Map<string, { id: string; name: string; args: unknown }>,
	write: (chunk: unknown) => void
): void {
	// Look up by call_id (we may not know the index from this event alone).
	let entry: { id: string; name: string; argsBuffer: string; inputEmitted: boolean } | undefined;
	for (const candidate of toolCalls.values()) {
		if (candidate.id === payload.call_id) {
			entry = candidate;
			break;
		}
	}

	// nanobot tells us the parsed arguments authoritatively — use that, not
	// the streamed text buffer (which may be incomplete or have JSON repair
	// applied server-side).
	const input = payload.arguments ?? {};
	toolByCallId.set(payload.call_id, { id: payload.call_id, name: payload.name, args: input });

	if (entry?.inputEmitted) return;

	write({
		type: 'tool-input-available',
		toolCallId: payload.call_id,
		toolName: payload.name,
		input
	});
	if (entry) entry.inputEmitted = true;
}
