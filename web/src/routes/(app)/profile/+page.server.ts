import { fail, redirect } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { userTemplates } from '$lib/server/db/app.schema';
import { and, eq } from 'drizzle-orm';
import type { PageServerLoad, Actions } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const load: PageServerLoad = async ({ locals }) => {
	if (!locals.session) redirect(302, '/auth');
	const userId = locals.user!.id;

	const [userTemplate] = await db
		.select()
		.from(userTemplates)
		.where(and(eq(userTemplates.userId, userId), eq(userTemplates.templateType, 'user')))
		.limit(1);

	return {
		userTemplate: userTemplate ?? null
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
	}
};
