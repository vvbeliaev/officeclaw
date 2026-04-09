import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const POST: RequestHandler = async ({ params, request, locals }) => {
	if (!locals.session) {
		error(401, 'Unauthorized');
	}

	const body = await request.arrayBuffer();

	const upstream = await fetch(`${API_URL}/agents/${params.id}/chat`, {
		method: 'POST',
		headers: {
			'Content-Type': request.headers.get('content-type') ?? 'application/json',
			Accept: 'text/event-stream'
		},
		body,
		// @ts-expect-error — Node 18+ fetch supports duplex for streaming
		duplex: 'half'
	});

	if (!upstream.ok) {
		const text = await upstream.text();
		error(upstream.status, text);
	}

	return new Response(upstream.body, {
		headers: {
			'Content-Type': 'text/event-stream',
			'Cache-Control': 'no-cache',
			Connection: 'keep-alive'
		}
	});
};
