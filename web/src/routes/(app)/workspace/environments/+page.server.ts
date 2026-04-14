import { db } from '$lib/server/db';
import { workspaceEnvs, workspaces } from '$lib/server/db/app.schema';
import { eq, desc } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => {
	const userId = locals.user!.id;
	const envs = await db
		.select({
			id: workspaceEnvs.id,
			name: workspaceEnvs.name,
			category: workspaceEnvs.category,
			createdAt: workspaceEnvs.createdAt
		})
		.from(workspaceEnvs)
		.innerJoin(workspaces, eq(workspaces.id, workspaceEnvs.workspaceId))
		.where(eq(workspaces.userId, userId))
		.orderBy(desc(workspaceEnvs.createdAt));
	return { envs };
};
