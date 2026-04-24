import { fail, redirect } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { workspaceTemplates, workspaces } from '$lib/server/db/app.schema';
import { user } from '$lib/server/db/auth.schema';
import { and, eq } from 'drizzle-orm';
import type { PageServerLoad, Actions } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const load: PageServerLoad = async ({ locals }) => {
	if (!locals.session) redirect(302, '/auth');
	const userId = locals.user!.id;

	const [[userTemplate], [userRow]] = await Promise.all([
		db
			.select({
				id: workspaceTemplates.id,
				name: workspaceTemplates.name,
				templateType: workspaceTemplates.templateType,
				content: workspaceTemplates.content,
				createdAt: workspaceTemplates.createdAt,
				updatedAt: workspaceTemplates.updatedAt,
				workspaceId: workspaceTemplates.workspaceId
			})
			.from(workspaceTemplates)
			.innerJoin(workspaces, eq(workspaces.id, workspaceTemplates.workspaceId))
			.where(and(eq(workspaces.userId, userId), eq(workspaceTemplates.templateType, 'user')))
			.limit(1),
		db.select({ timezone: user.timezone }).from(user).where(eq(user.id, userId)).limit(1)
	]);

	return {
		userTemplate: userTemplate ?? null,
		timezone: userRow?.timezone ?? 'UTC'
	};
};

export const actions: Actions = {
	saveUserTemplate: async ({ locals, request }) => {
		if (!locals.session) return fail(401, { error: 'Unauthorized' });
		const userId = locals.user!.id;

		const form = await request.formData();
		const name = form.get('name')?.toString().trim() || 'About me';
		const content = form.get('content')?.toString() ?? '';
		const existingId = form.get('id')?.toString();

		if (existingId) {
			const res = await fetch(`${API_URL}/templates/${existingId}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ name, content })
			});
			if (!res.ok) return fail(res.status, { error: await res.text() });
		} else {
			const res = await fetch(`${API_URL}/templates`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ user_id: userId, name, template_type: 'user', content })
			});
			if (!res.ok) return fail(res.status, { error: await res.text() });
		}

		return { success: true };
	},

	saveTimezone: async ({ locals, request }) => {
		if (!locals.session) return fail(401, { tzError: 'Unauthorized' });
		const userId = locals.user!.id;

		const form = await request.formData();
		const timezone = form.get('timezone')?.toString().trim();
		if (!timezone) return fail(400, { tzError: 'Timezone is required' });

		try {
			// Reject anything Intl doesn't recognise — prevents junk strings from
			// landing in the column the Python API reads at sandbox start.
			new Intl.DateTimeFormat('en', { timeZone: timezone });
		} catch {
			return fail(400, { tzError: 'Unknown IANA timezone' });
		}

		await db.update(user).set({ timezone }).where(eq(user.id, userId));

		return { tzSuccess: true };
	}
};
