import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { resolveWorkspaceId } from '$lib/server/workspace-token';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const POST: RequestHandler = async ({ request, locals }) => {
	if (!locals.session) error(401, 'Unauthorized');

	const body = await request.json();
	const name = body.name?.toString().trim();
	const workspaceParam = body.workspace_id?.toString();

	if (!name) error(400, 'Name is required');
	if (!workspaceParam) error(400, 'workspace_id is required');

	const workspaceId = await resolveWorkspaceId(workspaceParam, locals.user!.id);
	if (!workspaceId) error(404, 'Workspace not found');

	const upstream = await fetch(`${API_URL}/agents`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			workspace_id: workspaceId,
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
