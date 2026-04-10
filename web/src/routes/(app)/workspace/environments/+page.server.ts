import { db } from '$lib/server/db';
import { userEnvs } from '$lib/server/db/app.schema';
import { eq, desc } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => {
	const userId = locals.user!.id;
	const envs = await db
		.select({ id: userEnvs.id, name: userEnvs.name, createdAt: userEnvs.createdAt })
		.from(userEnvs)
		.where(eq(userEnvs.userId, userId))
		.orderBy(desc(userEnvs.createdAt));
	return { envs };
};
