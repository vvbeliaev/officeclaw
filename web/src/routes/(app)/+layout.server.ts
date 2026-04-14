import { redirect } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { workspaces } from '$lib/server/db/app.schema';
import { eq } from 'drizzle-orm';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals }) => {
	if (!locals.session) redirect(302, '/auth');

	const userId = locals.user!.id;

	const userWorkspaces = await db
		.select()
		.from(workspaces)
		.where(eq(workspaces.userId, userId))
		.orderBy(workspaces.createdAt);

	return {
		user: locals.user!,
		session: locals.session!,
		workspaces: userWorkspaces
	};
};
