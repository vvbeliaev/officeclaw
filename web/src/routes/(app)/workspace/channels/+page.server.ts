import { db } from '$lib/server/db';
import { workspaceChannels, workspaces } from '$lib/server/db/app.schema';
import { eq, desc } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => {
	const userId = locals.user!.id;
	const channels = await db
		.select({
			id: workspaceChannels.id,
			name: workspaceChannels.name,
			type: workspaceChannels.type,
			createdAt: workspaceChannels.createdAt
		})
		.from(workspaceChannels)
		.innerJoin(workspaces, eq(workspaces.id, workspaceChannels.workspaceId))
		.where(eq(workspaces.userId, userId))
		.orderBy(desc(workspaceChannels.createdAt));
	return { channels };
};
