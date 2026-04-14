import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const POST: RequestHandler = async ({ request, locals }) => {
	if (!locals.session) error(401, 'Unauthorized');

	const body = await request.json();
	const type = body.type?.toString().trim();
	if (!type) error(400, 'Channel type is required');
	const name = body.name?.toString().trim();
	if (!name) error(400, 'Channel name is required');

	const config: Record<string, unknown> = body.config ?? {};

	const upstream = await fetch(`${API_URL}/channels`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			user_id: locals.user!.id,
			workspace_id: body.workspace_id,
			name,
			type,
			config
		})
	});

	if (!upstream.ok) {
		const text = await upstream.text();
		error(upstream.status, text || 'Failed to create channel');
	}

	return json(await upstream.json(), { status: 201 });
};
