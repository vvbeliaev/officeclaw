import { error } from '@sveltejs/kit';
import { createOpenAI } from '@ai-sdk/openai';
import { convertToModelMessages, streamText } from 'ai';
import type { UIMessage } from 'ai';
import type { RequestHandler } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const POST: RequestHandler = async ({ params, request, locals }) => {
	if (!locals.session) {
		error(401, 'Unauthorized');
	}

	const body = (await request.json()) as { messages: UIMessage[] };

	const nanobot = createOpenAI({
		baseURL: `${API_URL}/agents/${params.id}/v1`,
		apiKey: 'not-required'
	});

	const result = streamText({
		model: nanobot('nanobot'),
		messages: await convertToModelMessages(body.messages)
	});

	return result.toUIMessageStreamResponse();
};
