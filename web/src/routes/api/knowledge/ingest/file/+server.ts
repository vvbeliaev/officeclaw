import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { getWorkspaceToken } from '$lib/server/workspace-token';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const POST: RequestHandler = async ({ request, locals }) => {
	if (!locals.session || !locals.user) error(401, 'Unauthorized');

	const formData = await request.formData();
	const workspace_id = formData.get('workspace_id') as string | null;
	if (!workspace_id) error(400, 'workspace_id required');
	formData.delete('workspace_id');

	const token = await getWorkspaceToken(workspace_id, locals.user.id);
	if (!token) error(401, 'No API token configured');

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
