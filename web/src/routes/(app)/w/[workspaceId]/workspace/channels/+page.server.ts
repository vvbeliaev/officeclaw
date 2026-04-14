import { db } from '$lib/server/db';
import { workspaceChannels } from '$lib/server/db/app.schema';
import { eq, desc } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params }) => {
	const channels = await db
		.select({
			id: workspaceChannels.id,
			name: workspaceChannels.name,
			type: workspaceChannels.type,
			createdAt: workspaceChannels.createdAt
		})
		.from(workspaceChannels)
		.where(eq(workspaceChannels.workspaceId, params.workspaceId))
		.orderBy(desc(workspaceChannels.createdAt));
	return { channels };
};
