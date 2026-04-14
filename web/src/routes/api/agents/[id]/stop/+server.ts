import { error, json } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { agents, workspaces } from '$lib/server/db/app.schema';
import { and, eq } from 'drizzle-orm';
import type { RequestHandler } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const POST: RequestHandler = async ({ params, locals }) => {
	if (!locals.session) error(401, 'Unauthorized');

	const [owned] = await db
		.select({ id: agents.id })
		.from(agents)
		.innerJoin(workspaces, eq(workspaces.id, agents.workspaceId))
		.where(and(eq(agents.id, params.id), eq(workspaces.userId, locals.user!.id)))
		.limit(1);
	if (!owned) error(404, 'Agent not found');

	const upstream = await fetch(`${API_URL}/agents/${params.id}/stop`, {
		method: 'POST'
	});

	if (!upstream.ok) {
		const text = await upstream.text();
		error(upstream.status, text || 'Failed to stop sandbox');
	}

	return json(await upstream.json());
};
