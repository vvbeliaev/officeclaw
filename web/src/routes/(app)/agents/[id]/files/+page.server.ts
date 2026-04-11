import { error } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { agents, agentFiles } from '$lib/server/db/app.schema';
import { and, eq } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, locals }) => {
	const [agent] = await db
		.select()
		.from(agents)
		.where(and(eq(agents.id, params.id), eq(agents.userId, locals.user!.id)))
		.limit(1);

	if (!agent) error(404, 'Agent not found');

	const files = await db
		.select({ path: agentFiles.path, content: agentFiles.content, updatedAt: agentFiles.updatedAt })
		.from(agentFiles)
		.where(eq(agentFiles.agentId, params.id))
		.orderBy(agentFiles.path);

	return { agent, files };
};
