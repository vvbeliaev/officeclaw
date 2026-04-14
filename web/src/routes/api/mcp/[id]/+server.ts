import { json, error } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { workspaceMcp, workspaces } from '$lib/server/db/app.schema';
import { and, eq } from 'drizzle-orm';
import type { RequestHandler } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

async function checkOwnership(mcpId: string, userId: string): Promise<boolean> {
	const [owned] = await db
		.select({ id: workspaceMcp.id })
		.from(workspaceMcp)
		.innerJoin(workspaces, eq(workspaces.id, workspaceMcp.workspaceId))
		.where(and(eq(workspaceMcp.id, mcpId), eq(workspaces.userId, userId)))
		.limit(1);
	return !!owned;
}

export const GET: RequestHandler = async ({ params, locals }) => {
	if (!locals.session) error(401, 'Unauthorized');
	if (!(await checkOwnership(params.id, locals.user!.id))) error(404, 'MCP not found');

	const upstream = await fetch(`${API_URL}/user-mcp/${params.id}/config`);
	if (!upstream.ok) {
		const text = await upstream.text();
		error(upstream.status, text || 'Failed to fetch MCP config');
	}
	return json(await upstream.json());
};

export const PATCH: RequestHandler = async ({ params, locals, request }) => {
	if (!locals.session) error(401, 'Unauthorized');
	if (!(await checkOwnership(params.id, locals.user!.id))) error(404, 'MCP not found');

	const body = await request.json();
	const upstream = await fetch(`${API_URL}/user-mcp/${params.id}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body),
	});

	if (!upstream.ok) {
		const text = await upstream.text();
		error(upstream.status, text || 'Failed to update MCP');
	}
	return json(await upstream.json());
};

export const DELETE: RequestHandler = async ({ params, locals }) => {
	if (!locals.session) error(401, 'Unauthorized');
	if (!(await checkOwnership(params.id, locals.user!.id))) error(404, 'MCP not found');

	const res = await fetch(`${API_URL}/user-mcp/${params.id}`, { method: 'DELETE' });
	if (!res.ok && res.status !== 204) {
		const text = await res.text();
		error(res.status, text);
	}
	return new Response(null, { status: 204 });
};
