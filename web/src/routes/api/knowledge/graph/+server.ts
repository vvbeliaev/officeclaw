import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const GET: RequestHandler = async ({ locals }) => {
	if (!locals.session || !locals.user) error(401, 'Unauthorized');
	const token = (locals.user as unknown as { officeclawToken?: string }).officeclawToken;
	if (!token) error(401, 'No API token configured');

	const upstream = await fetch(`${API_URL}/knowledge/graph`, {
		headers: { Authorization: `Bearer ${token}` }
	});

	if (!upstream.ok) {
		const text = await upstream.text();
		error(upstream.status, text || 'Graph fetch failed');
	}

	return json(await upstream.json());
};
