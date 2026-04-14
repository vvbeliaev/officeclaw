import { redirect } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { workspaces } from '$lib/server/db/app.schema';
import { eq } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => {
	const [first] = await db
		.select({ id: workspaces.id })
		.from(workspaces)
		.where(eq(workspaces.userId, locals.user!.id))
		.orderBy(workspaces.createdAt)
		.limit(1);

	if (first) redirect(302, `/w/${first.id}`);

	return {};
};
