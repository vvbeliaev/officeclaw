import { redirect } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { agents, workspaces } from '$lib/server/db/app.schema';
import { and, eq } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => {
	// Admin-first UX: if the user has an Admin agent, land on its chat.
	// Otherwise fall through to the empty state page.
	const [admin] = await db
		.select({ id: agents.id })
		.from(agents)
		.innerJoin(workspaces, eq(workspaces.id, agents.workspaceId))
		.where(and(eq(workspaces.userId, locals.user!.id), eq(agents.isAdmin, true)))
		.limit(1);

	if (admin) {
		redirect(302, `/agents/${admin.id}`);
	}

	return {};
};
