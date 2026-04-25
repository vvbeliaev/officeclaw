import { error } from '@sveltejs/kit';
import {
	createUIMessageStream,
	createUIMessageStreamResponse,
	type UIMessage
} from 'ai';
import { and, eq } from 'drizzle-orm';

import { db } from '$lib/server/db';
import { agents, agentChatMessages } from '$lib/server/db/app.schema';
import { pipeNanobotSseToUiStream } from '$lib/server/nanobot-sse-bridge';
import type { RequestHandler } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

/**
 * Convert a UIMessage (with typed parts) to a flat text message for nanobot.
 * Nanobot's OpenAI endpoint expects standard chat-completions input — we
 * collapse parts to their textual representation for the user message that
 * triggers the next turn. History persistence happens via Drizzle, not via
 * what we forward to nanobot.
 */
function uiMessageToText(message: UIMessage): string {
	return message.parts
		.filter((p): p is { type: 'text'; text: string } => p.type === 'text')
		.map((p) => p.text)
		.join('');
}

export const POST: RequestHandler = async ({ params, request, locals }) => {
	if (!locals.session) {
		error(401, 'Unauthorized');
	}

	const agentId = params.id;
	const [agent] = await db
		.select({ id: agents.id, workspaceId: agents.workspaceId })
		.from(agents)
		.where(eq(agents.id, agentId))
		.limit(1);

	if (!agent) {
		error(404, 'Agent not found');
	}

	const { messages } = (await request.json()) as { messages: UIMessage[] };
	const incomingUser = [...messages].reverse().find((m) => m.role === 'user');

	if (incomingUser) {
		const userText = uiMessageToText(incomingUser);
		// Persist the user's turn before opening the upstream stream so it
		// survives a mid-stream disconnect. ON CONFLICT keeps re-submits
		// idempotent (same UIMessage.id from the client).
		await db
			.insert(agentChatMessages)
			.values({
				agentId,
				messageId: incomingUser.id,
				role: 'user',
				parts: incomingUser.parts,
				metadata: incomingUser.metadata ?? null,
				status: 'complete'
			})
			.onConflictDoNothing({ target: [agentChatMessages.agentId, agentChatMessages.messageId] });

		// Pre-create a pending assistant row so the UI's history endpoint
		// shows "thinking" if the page reloads mid-turn. onFinish promotes
		// it to complete with the final parts; a sweeper marks abandoned
		// rows as failed.
		const assistantId = crypto.randomUUID();
		const stream = createUIMessageStream<UIMessage>({
			originalMessages: messages,
			generateId: () => assistantId,
			execute: async ({ writer }) => {
				const upstream = await fetch(`${API_URL}/agents/${agentId}/v1/chat/completions`, {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
						Authorization: 'Bearer not-required'
					},
					body: JSON.stringify({
						stream: true,
						session_id: agentId,
						messages: [{ role: 'user', content: userText }]
					})
				});

				if (!upstream.ok || !upstream.body) {
					throw new Error(
						`nanobot upstream failed: ${upstream.status} ${upstream.statusText}`
					);
				}

				await pipeNanobotSseToUiStream(upstream.body, writer);
			},
			onFinish: async ({ responseMessage }) => {
				await db
					.insert(agentChatMessages)
					.values({
						agentId,
						messageId: responseMessage.id,
						role: 'assistant',
						parts: responseMessage.parts,
						metadata: responseMessage.metadata ?? null,
						status: 'complete'
					})
					.onConflictDoUpdate({
						target: [agentChatMessages.agentId, agentChatMessages.messageId],
						set: {
							parts: responseMessage.parts,
							metadata: responseMessage.metadata ?? null,
							status: 'complete',
							updatedAt: new Date()
						}
					});
			},
			onError: (err: unknown) => {
				return err instanceof Error ? err.message : 'Assistant stream failed';
			}
		});

		return createUIMessageStreamResponse({ stream });
	}

	// No user turn to act on — return an empty stream rather than 400 so the
	// AI SDK client doesn't surface a confusing error for trivially-empty
	// resubmissions (e.g. after history-only hydration).
	const stream = createUIMessageStream<UIMessage>({
		originalMessages: messages,
		execute: async () => {
			/* no-op */
		}
	});
	return createUIMessageStreamResponse({ stream });
};

/** History fetch — used by the page server load only. Kept here so the
 *  chat URL has both POST (next turn) and GET (history) under one path. */
export const GET: RequestHandler = async ({ params, locals }) => {
	if (!locals.session) {
		error(401, 'Unauthorized');
	}
	const rows = await db
		.select({
			messageId: agentChatMessages.messageId,
			role: agentChatMessages.role,
			parts: agentChatMessages.parts,
			metadata: agentChatMessages.metadata,
			createdAt: agentChatMessages.createdAt
		})
		.from(agentChatMessages)
		.where(and(eq(agentChatMessages.agentId, params.id)))
		.orderBy(agentChatMessages.createdAt);

	return new Response(JSON.stringify({ messages: rows }), {
		headers: { 'Content-Type': 'application/json' }
	});
};
