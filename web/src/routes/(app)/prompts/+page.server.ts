import { redirect } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { workspaceTemplates, workspaces } from '$lib/server/db/app.schema';
import { and, eq, ne } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => {
	if (!locals.session) redirect(302, '/auth');
	const userId = locals.user!.id;

	const rows = await db
		.select({ template: workspaceTemplates })
		.from(workspaceTemplates)
		.innerJoin(workspaces, eq(workspaces.id, workspaceTemplates.workspaceId))
		.where(and(eq(workspaces.userId, userId), ne(workspaceTemplates.templateType, 'user')))
		.orderBy(workspaceTemplates.createdAt);

	return { templates: rows.map((r) => r.template) };
};
