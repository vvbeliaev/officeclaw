import { db } from '$lib/server/db';
import { workspaceEnvs } from '$lib/server/db/app.schema';
import { eq, desc } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params }) => {
	const envs = await db
		.select({
			id: workspaceEnvs.id,
			name: workspaceEnvs.name,
			category: workspaceEnvs.category,
			createdAt: workspaceEnvs.createdAt
		})
		.from(workspaceEnvs)
		.where(eq(workspaceEnvs.workspaceId, params.workspaceId))
		.orderBy(desc(workspaceEnvs.createdAt));
	return { envs };
};
