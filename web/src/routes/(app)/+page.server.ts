import { db } from '$lib/server/db';
import { agents } from '$lib/server/db/app.schema';
import { eq } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => {
	const userAgents = await db
		.select()
		.from(agents)
		.where(eq(agents.userId, locals.user!.id));

	return { agents: userAgents };
};
