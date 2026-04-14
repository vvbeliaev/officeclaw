import { db } from '$lib/server/db';
import { workspaceMcp, workspaces } from '$lib/server/db/app.schema';
import { eq, desc } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => {
	const userId = locals.user!.id;
	const mcps = await db
		.select({ id: workspaceMcp.id, name: workspaceMcp.name, type: workspaceMcp.type, createdAt: workspaceMcp.createdAt })
		.from(workspaceMcp)
		.innerJoin(workspaces, eq(workspaces.id, workspaceMcp.workspaceId))
		.where(eq(workspaces.userId, userId))
		.orderBy(desc(workspaceMcp.createdAt));
	return { mcps };
};
