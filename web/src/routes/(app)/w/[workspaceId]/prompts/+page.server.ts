import { db } from '$lib/server/db';
import { workspaceTemplates } from '$lib/server/db/app.schema';
import { and, eq, ne } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params }) => {
	const rows = await db
		.select({ template: workspaceTemplates })
		.from(workspaceTemplates)
		.where(and(eq(workspaceTemplates.workspaceId, params.workspaceId), ne(workspaceTemplates.templateType, 'user')))
		.orderBy(workspaceTemplates.createdAt);

	return { templates: rows.map((r) => r.template) };
};
