import { redirect } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { agents } from '$lib/server/db/app.schema';
import { and, eq } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params }) => {
	const [admin] = await db
		.select({ id: agents.id })
		.from(agents)
		.where(and(eq(agents.workspaceId, params.workspaceId), eq(agents.isAdmin, true)))
		.limit(1);

	if (admin) redirect(302, `/w/${params.workspaceId}/agents/${admin.id}`);

	return {};
};
