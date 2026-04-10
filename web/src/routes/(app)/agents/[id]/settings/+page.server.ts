import { error, fail, redirect } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { agents } from '$lib/server/db/app.schema';
import { and, eq } from 'drizzle-orm';
import type { PageServerLoad, Actions } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const load: PageServerLoad = async ({ params, locals }) => {
	if (!locals.session) redirect(302, '/auth');

	const [agent] = await db
		.select()
		.from(agents)
		.where(and(eq(agents.id, params.id), eq(agents.userId, locals.user!.id)))
		.limit(1);

	if (!agent) error(404, 'Agent not found');

	return { agent };
};

export const actions: Actions = {
	update: async ({ params, request, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');

		const form = await request.formData();
		const name = form.get('name')?.toString().trim();

		if (!name) return fail(400, { error: 'Name is required' });

		const upstream = await fetch(`${API_URL}/agents/${params.id}`, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ name })
		});

		if (!upstream.ok) {
			const text = await upstream.text();
			return fail(upstream.status, { error: text || 'Failed to update agent' });
		}

		return { success: true };
	},

	delete: async ({ params, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');

		const [agent] = await db
			.select({ id: agents.id, isAdmin: agents.isAdmin })
			.from(agents)
			.where(and(eq(agents.id, params.id), eq(agents.userId, locals.user!.id)))
			.limit(1);

		if (!agent) error(404, 'Agent not found');
		if (agent.isAdmin) return fail(400, { error: 'Admin agent cannot be deleted' });

		const upstream = await fetch(`${API_URL}/agents/${params.id}`, { method: 'DELETE' });

		if (!upstream.ok && upstream.status !== 204) {
			const text = await upstream.text();
			return fail(upstream.status, { error: text || 'Failed to delete agent' });
		}

		redirect(302, '/');
	}
};
