import { redirect } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import {
	agents,
	skills,
	userEnvs,
	userChannels,
	userMcp,
	userTemplates
} from '$lib/server/db/app.schema';
import { and, eq, ne, desc, count } from 'drizzle-orm';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals }) => {
	if (!locals.session) redirect(302, '/auth');

	const userId = locals.user!.id;

	// Fleet: Admin pinned first, then by created_at desc.
	// (Admin-first because it's the entry point of the UX.)
	const userAgents = await db
		.select()
		.from(agents)
		.where(eq(agents.userId, userId))
		.orderBy(desc(agents.isAdmin), desc(agents.createdAt));

	// Workspace counts — shown as badges in the sidebar.
	const [[skillsCount], [envsCount], [channelsCount], [mcpCount], [promptsCount]] =
		await Promise.all([
			db.select({ n: count() }).from(skills).where(eq(skills.userId, userId)),
			db.select({ n: count() }).from(userEnvs).where(eq(userEnvs.userId, userId)),
			db.select({ n: count() }).from(userChannels).where(eq(userChannels.userId, userId)),
			db.select({ n: count() }).from(userMcp).where(eq(userMcp.userId, userId)),
			db
				.select({ n: count() })
				.from(userTemplates)
				.where(and(eq(userTemplates.userId, userId), ne(userTemplates.templateType, 'user')))
		]);

	return {
		user: locals.user!,
		session: locals.session!,
		agents: userAgents,
		workspaceCounts: {
			skills: skillsCount?.n ?? 0,
			envs: envsCount?.n ?? 0,
			channels: channelsCount?.n ?? 0,
			mcp: mcpCount?.n ?? 0,
			knowledge: 0,
			prompts: promptsCount?.n ?? 0
		}
	};
};
