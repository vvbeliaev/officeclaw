import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const PATCH: RequestHandler = async ({ params, request, locals }) => {
	if (!locals.session) error(401, 'Unauthorized');

	const body = await request.json();
	const upstream = await fetch(`${API_URL}/workspaces/${params.id}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});

	if (!upstream.ok) {
		const text = await upstream.text();
		error(upstream.status, text || 'Failed to update workspace');
	}

	return json(await upstream.json());
};

export const DELETE: RequestHandler = async ({ params, locals }) => {
	if (!locals.session) error(401, 'Unauthorized');

	const upstream = await fetch(`${API_URL}/workspaces/${params.id}`, {
		method: 'DELETE'
	});

	if (!upstream.ok && upstream.status !== 204) {
		const text = await upstream.text();
		error(upstream.status, text || 'Failed to delete workspace');
	}

	return new Response(null, { status: 204 });
};
