import { error } from '@sveltejs/kit';
import { createOpenAICompatible } from '@ai-sdk/openai-compatible';
import { convertToModelMessages, streamText } from 'ai';
import type { UIMessage } from 'ai';
import type { RequestHandler } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const POST: RequestHandler = async ({ params, request, locals }) => {
	if (!locals.session) {
		error(401, 'Unauthorized');
	}

	const body = (await request.json()) as { messages: UIMessage[] };

	// Inject session_id so nanobot uses an isolated session per agent
	// (nanobot server.py: session_key = f"api:{session_id}").
	const sessionId = params.id;
	const nanobot = createOpenAICompatible({
		name: 'google/gemma-4-31b-it',
		baseURL: `${API_URL}/agents/${params.id}/v1`,
		headers: { Authorization: 'Bearer not-required' },
		fetch: async (url, init) => {
			const body = JSON.parse((init?.body as string) ?? '{}');
			return fetch(url, { ...init, body: JSON.stringify({ ...body, session_id: sessionId }) });
		}
	});

	const result = streamText({
		model: nanobot('google/gemma-4-31b-it'),
		messages: await convertToModelMessages(body.messages)
	});

	return result.toUIMessageStreamResponse();
};
