import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const PATCH: RequestHandler = async ({ locals, params, request }) => {
	if (!locals.session) error(401, 'Unauthorized');
	const body = await request.json();

	const res = await fetch(`${API_URL}/templates/${params.id}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});

	if (!res.ok) error(res.status, await res.text());
	return json(await res.json());
};

export const DELETE: RequestHandler = async ({ locals, params }) => {
	if (!locals.session) error(401, 'Unauthorized');

	const res = await fetch(`${API_URL}/templates/${params.id}`, { method: 'DELETE' });
	if (!res.ok && res.status !== 204) error(res.status, await res.text());
	return new Response(null, { status: 204 });
};
