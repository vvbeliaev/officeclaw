import { db } from '$lib/server/db';
import { workspaceChannels } from '$lib/server/db/app.schema';
import { eq, desc } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ parent }) => {
	const { workspace } = await parent();
	const channels = await db
		.select({
			id: workspaceChannels.id,
			name: workspaceChannels.name,
			type: workspaceChannels.type,
			createdAt: workspaceChannels.createdAt
		})
		.from(workspaceChannels)
		.where(eq(workspaceChannels.workspaceId, workspace.id))
		.orderBy(desc(workspaceChannels.createdAt));
	return { channels };
};
