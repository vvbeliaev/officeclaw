import { redirect } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { userTemplates } from '$lib/server/db/app.schema';
import { and, eq, ne } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => {
	if (!locals.session) redirect(302, '/auth');
	const userId = locals.user!.id;

	const templates = await db
		.select()
		.from(userTemplates)
		.where(and(eq(userTemplates.userId, userId), ne(userTemplates.templateType, 'user')))
		.orderBy(userTemplates.createdAt);

	return { templates };
};
