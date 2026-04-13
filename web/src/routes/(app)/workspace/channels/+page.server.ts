import { db } from '$lib/server/db';
import { userChannels } from '$lib/server/db/app.schema';
import { eq, desc } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => {
	const userId = locals.user!.id;
	const channels = await db
		.select({
			id: userChannels.id,
			name: userChannels.name,
			type: userChannels.type,
			createdAt: userChannels.createdAt
		})
		.from(userChannels)
		.where(eq(userChannels.userId, userId))
		.orderBy(desc(userChannels.createdAt));
	return { channels };
};
