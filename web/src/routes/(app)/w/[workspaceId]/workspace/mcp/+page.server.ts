import { db } from '$lib/server/db';
import { workspaceMcp } from '$lib/server/db/app.schema';
import { eq, desc } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ parent }) => {
	const { workspace } = await parent();
	const mcps = await db
		.select({ id: workspaceMcp.id, name: workspaceMcp.name, type: workspaceMcp.type, createdAt: workspaceMcp.createdAt })
		.from(workspaceMcp)
		.where(eq(workspaceMcp.workspaceId, workspace.id))
		.orderBy(desc(workspaceMcp.createdAt));
	return { mcps };
};
