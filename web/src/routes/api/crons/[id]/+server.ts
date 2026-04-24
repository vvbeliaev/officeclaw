import { error, json } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { workspaceCrons, workspaces } from '$lib/server/db/app.schema';
import { and, eq } from 'drizzle-orm';
import type { RequestHandler } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

async function checkOwnership(cronId: string, userId: string): Promise<boolean> {
	const [owned] = await db
		.select({ id: workspaceCrons.id })
		.from(workspaceCrons)
		.innerJoin(workspaces, eq(workspaces.id, workspaceCrons.workspaceId))
		.where(and(eq(workspaceCrons.id, cronId), eq(workspaces.userId, userId)))
		.limit(1);
	return !!owned;
}

export const PATCH: RequestHandler = async ({ params, request, locals }) => {
	if (!locals.session) error(401, 'Unauthorized');
	if (!(await checkOwnership(params.id, locals.user!.id))) error(404, 'Cron not found');

	const body = await request.json();

	const upstream = await fetch(`${API_URL}/crons/${params.id}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});

	if (!upstream.ok) {
		const text = await upstream.text();
		error(upstream.status, text || 'Failed to update cron');
	}

	return json(await upstream.json());
};

export const DELETE: RequestHandler = async ({ params, locals }) => {
	if (!locals.session) error(401, 'Unauthorized');
	if (!(await checkOwnership(params.id, locals.user!.id))) error(404, 'Cron not found');

	const upstream = await fetch(`${API_URL}/crons/${params.id}`, { method: 'DELETE' });

	if (!upstream.ok && upstream.status !== 204) {
		const text = await upstream.text();
		error(upstream.status, text || 'Failed to delete cron');
	}

	return new Response(null, { status: 204 });
};
