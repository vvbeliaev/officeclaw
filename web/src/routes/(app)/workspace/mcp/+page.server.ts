import { db } from '$lib/server/db';
import { userMcp } from '$lib/server/db/app.schema';
import { eq, desc } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => {
	const userId = locals.user!.id;
	const mcps = await db
		.select({ id: userMcp.id, name: userMcp.name, type: userMcp.type, createdAt: userMcp.createdAt })
		.from(userMcp)
		.where(eq(userMcp.userId, userId))
		.orderBy(desc(userMcp.createdAt));
	return { mcps };
};
