import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { getWorkspaceToken } from '$lib/server/workspace-token';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const GET: RequestHandler = async ({ url, locals }) => {
	if (!locals.session || !locals.user) error(401, 'Unauthorized');

	const workspace_id = url.searchParams.get('workspace_id');
	if (!workspace_id) error(400, 'workspace_id required');

	const token = await getWorkspaceToken(workspace_id, locals.user.id);
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
