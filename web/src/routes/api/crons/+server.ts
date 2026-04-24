import { error, json } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { workspaces } from '$lib/server/db/app.schema';
import { and, eq } from 'drizzle-orm';
import type { RequestHandler } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const POST: RequestHandler = async ({ request, locals }) => {
	if (!locals.session) error(401, 'Unauthorized');

	const body = await request.json();
	const workspaceId = body.workspace_id?.toString();
	if (!workspaceId) error(400, 'workspace_id required');

	const [owned] = await db
		.select({ id: workspaces.id })
		.from(workspaces)
		.where(and(eq(workspaces.id, workspaceId), eq(workspaces.userId, locals.user!.id)))
		.limit(1);
	if (!owned) error(404, 'Workspace not found');

	const upstream = await fetch(`${API_URL}/crons`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});

	if (!upstream.ok) {
		const text = await upstream.text();
		error(upstream.status, text || 'Failed to create cron');
	}

	return json(await upstream.json(), { status: 201 });
};
