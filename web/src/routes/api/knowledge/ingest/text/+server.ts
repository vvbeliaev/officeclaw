import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const POST: RequestHandler = async ({ request, locals }) => {
	if (!locals.session || !locals.user) error(401, 'Unauthorized');
	const token = (locals.user as unknown as { officeclawToken?: string }).officeclawToken;
	if (!token) error(401, 'No API token configured');

	const body = await request.json();

	const upstream = await fetch(`${API_URL}/knowledge/ingest/text`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(body)
	});

	if (!upstream.ok) {
		const text = await upstream.text();
		error(upstream.status, text || 'Ingest failed');
	}

	return json(await upstream.json(), { status: 202 });
};
