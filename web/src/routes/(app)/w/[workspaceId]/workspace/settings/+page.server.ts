import { error, fail, redirect } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { workspaces } from '$lib/server/db/app.schema';
import { and, eq } from 'drizzle-orm';
import type { PageServerLoad, Actions } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';
const SLUG_RE = /^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$/;

export const load: PageServerLoad = async ({ parent }) => {
	const { workspace } = await parent();
	return { workspace };
};

export const actions: Actions = {
	update: async ({ params, request, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');

		const form = await request.formData();
		const name = form.get('name')?.toString().trim();
		const slug = form.get('slug')?.toString().trim().toLowerCase();

		if (!name) return fail(400, { error: 'Name is required' });
		if (!slug) return fail(400, { error: 'Slug is required' });
		if (slug.length < 3 || slug.length > 64 || !SLUG_RE.test(slug)) {
			return fail(400, {
				error: 'Slug must be 3–64 chars: lowercase letters, digits, and hyphens only (no leading/trailing hyphens)'
			});
		}

		// Re-validate ownership and get real UUID
		const [ws] = await db
			.select()
			.from(workspaces)
			.where(and(eq(workspaces.slug, params.workspaceId), eq(workspaces.userId, locals.user!.id)))
			.limit(1);

		// Fallback: try by UUID (legacy URL)
		const workspace =
			ws ??
			(
				await db
					.select()
					.from(workspaces)
					.where(
						and(eq(workspaces.id, params.workspaceId), eq(workspaces.userId, locals.user!.id))
					)
					.limit(1)
			)[0];

		if (!workspace) error(403, 'Forbidden');

		const upstream = await fetch(`${API_URL}/workspaces/${workspace.id}`, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ name, slug })
		});

		if (!upstream.ok) {
			const text = await upstream.text();
			return fail(upstream.status, { error: text || 'Failed to update workspace' });
		}

		const updated = await upstream.json();

		// If slug changed, redirect to the new URL
		if (updated.slug !== params.workspaceId) {
			redirect(302, `/w/${updated.slug}/workspace/settings`);
		}

		return { success: true };
	},

	delete: async ({ params, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');

		// Re-validate ownership and get real UUID
		const [ws] = await db
			.select()
			.from(workspaces)
			.where(and(eq(workspaces.slug, params.workspaceId), eq(workspaces.userId, locals.user!.id)))
			.limit(1);

		const workspace =
			ws ??
			(
				await db
					.select()
					.from(workspaces)
					.where(
						and(eq(workspaces.id, params.workspaceId), eq(workspaces.userId, locals.user!.id))
					)
					.limit(1)
			)[0];

		if (!workspace) error(403, 'Forbidden');

		const upstream = await fetch(`${API_URL}/workspaces/${workspace.id}`, {
			method: 'DELETE'
		});

		if (!upstream.ok && upstream.status !== 204) {
			const text = await upstream.text();
			return fail(upstream.status, { error: text || 'Failed to delete workspace' });
		}

		redirect(302, '/');
	}
};
