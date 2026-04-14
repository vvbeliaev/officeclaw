import { error } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { agents, workspaces } from '$lib/server/db/app.schema';
import { and, eq } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, locals }) => {
	const [agent] = await db
		.select()
		.from(agents)
		.innerJoin(workspaces, eq(workspaces.id, agents.workspaceId))
		.where(and(eq(agents.id, params.id), eq(workspaces.userId, locals.user!.id)))
		.limit(1);

	if (!agent) {
		error(404, 'Agent not found');
	}

	return { agent: agent.agents };
};
