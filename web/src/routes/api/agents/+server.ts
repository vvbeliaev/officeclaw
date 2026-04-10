import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const POST: RequestHandler = async ({ request, locals }) => {
	if (!locals.session) error(401, 'Unauthorized');

	const body = await request.json();
	const name = body.name?.toString().trim();

	if (!name) error(400, 'Name is required');

	const upstream = await fetch(`${API_URL}/agents`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			user_id: locals.user!.id,
			name,
			image: body.image ?? 'localhost:5005/officeclaw/agent:latest',
			is_admin: false
		})
	});

	if (!upstream.ok) {
		const text = await upstream.text();
		error(upstream.status, text || 'Failed to create agent');
	}

	return json(await upstream.json(), { status: 201 });
};
