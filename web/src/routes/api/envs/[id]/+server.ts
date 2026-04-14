import { error, json } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { workspaceEnvs, workspaces } from '$lib/server/db/app.schema';
import { and, eq } from 'drizzle-orm';
import type { RequestHandler } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

async function checkOwnership(envId: string, userId: string): Promise<boolean> {
	const [owned] = await db
		.select({ id: workspaceEnvs.id })
		.from(workspaceEnvs)
		.innerJoin(workspaces, eq(workspaces.id, workspaceEnvs.workspaceId))
		.where(and(eq(workspaceEnvs.id, envId), eq(workspaces.userId, userId)))
		.limit(1);
	return !!owned;
}

export const PATCH: RequestHandler = async ({ params, request, locals }) => {
	if (!locals.session) error(401, 'Unauthorized');
	if (!(await checkOwnership(params.id, locals.user!.id))) error(404, 'Env not found');

	const body = await request.json();

	const upstream = await fetch(`${API_URL}/envs/${params.id}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});

	if (!upstream.ok) {
		const text = await upstream.text();
		error(upstream.status, text || 'Failed to update env');
	}

	return json(await upstream.json());
};

export const DELETE: RequestHandler = async ({ params, locals }) => {
	if (!locals.session) error(401, 'Unauthorized');
	if (!(await checkOwnership(params.id, locals.user!.id))) error(404, 'Env not found');

	const upstream = await fetch(`${API_URL}/envs/${params.id}`, { method: 'DELETE' });

	if (!upstream.ok && upstream.status !== 204) {
		const text = await upstream.text();
		error(upstream.status, text || 'Failed to delete env');
	}

	return new Response(null, { status: 204 });
};
