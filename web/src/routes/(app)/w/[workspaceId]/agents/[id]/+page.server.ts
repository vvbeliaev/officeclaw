import { error } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { agents } from '$lib/server/db/app.schema';
import { and, eq } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params }) => {
	const [agent] = await db
		.select()
		.from(agents)
		.where(and(eq(agents.id, params.id), eq(agents.workspaceId, params.workspaceId)))
		.limit(1);

	if (!agent) {
		error(404, 'Agent not found');
	}

	return { agent };
};
