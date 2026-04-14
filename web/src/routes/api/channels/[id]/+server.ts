import { error } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { workspaceChannels, workspaces } from '$lib/server/db/app.schema';
import { and, eq } from 'drizzle-orm';
import type { RequestHandler } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

async function checkOwnership(channelId: string, userId: string): Promise<boolean> {
	const [owned] = await db
		.select({ id: workspaceChannels.id })
		.from(workspaceChannels)
		.innerJoin(workspaces, eq(workspaces.id, workspaceChannels.workspaceId))
		.where(and(eq(workspaceChannels.id, channelId), eq(workspaces.userId, userId)))
		.limit(1);
	return !!owned;
}

export const DELETE: RequestHandler = async ({ params, locals }) => {
	if (!locals.session) error(401, 'Unauthorized');
	if (!(await checkOwnership(params.id, locals.user!.id))) error(404, 'Channel not found');

	const upstream = await fetch(`${API_URL}/channels/${params.id}`, { method: 'DELETE' });

	if (!upstream.ok && upstream.status !== 204) {
		const text = await upstream.text();
		error(upstream.status, text || 'Failed to delete channel');
	}

	return new Response(null, { status: 204 });
};
