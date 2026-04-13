import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const POST: RequestHandler = async ({ request, locals }) => {
	if (!locals.session || !locals.user) error(401, 'Unauthorized');
	const token = (locals.user as unknown as { officeclawToken?: string }).officeclawToken;
	if (!token) error(401, 'No API token configured');

	// Forward multipart/form-data directly — let fetch set the boundary
	const formData = await request.formData();

	const upstream = await fetch(`${API_URL}/knowledge/ingest/file`, {
		method: 'POST',
		headers: { Authorization: `Bearer ${token}` },
		body: formData
	});

	if (!upstream.ok) {
		const text = await upstream.text();
		error(upstream.status, text || 'File ingest failed');
	}

	return json(await upstream.json(), { status: 202 });
};
