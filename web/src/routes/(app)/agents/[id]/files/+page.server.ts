import { error, fail } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { agents, agentFiles } from '$lib/server/db/app.schema';
import { and, eq } from 'drizzle-orm';
import type { PageServerLoad, Actions } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

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

export const actions: Actions = {
	save: async ({ params, request, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');

		const form = await request.formData();
		const path = form.get('path')?.toString();
		const content = form.get('content')?.toString() ?? '';

		if (!path) return fail(400, { error: 'path required' });

		const res = await fetch(`${API_URL}/agents/${params.id}/files`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ path, content })
		});

		if (!res.ok) {
			const text = await res.text();
			return fail(res.status, { error: text || 'Failed to save' });
		}

		return { saved: path };
	}
};
