import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const POST: RequestHandler = async ({ locals, request }) => {
	if (!locals.session) error(401, 'Unauthorized');
	const userId = locals.user!.id;
	const body = await request.json();

	const res = await fetch(`${API_URL}/templates`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ ...body, user_id: userId })
	});

	if (!res.ok) error(res.status, await res.text());
	return json(await res.json(), { status: 201 });
};
