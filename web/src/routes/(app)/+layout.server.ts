import { redirect } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import {
	agents,
	skills,
	workspaceEnvs,
	workspaceChannels,
	workspaceMcp,
	workspaceTemplates,
	workspaces
} from '$lib/server/db/app.schema';
import { and, eq, ne, desc, count } from 'drizzle-orm';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals }) => {
	if (!locals.session) redirect(302, '/auth');

	const userId = locals.user!.id;

	// Fleet: Admin pinned first, then by created_at desc.
	// (Admin-first because it's the entry point of the UX.)
	const userAgents = await db
		.select({ agents })
		.from(agents)
		.innerJoin(workspaces, eq(workspaces.id, agents.workspaceId))
		.where(eq(workspaces.userId, userId))
		.orderBy(desc(agents.isAdmin), desc(agents.createdAt));

	// Workspace counts — shown as badges in the sidebar.
	const [[skillsCount], [envsCount], [channelsCount], [mcpCount], [promptsCount]] =
		await Promise.all([
			db
				.select({ n: count() })
				.from(skills)
				.innerJoin(workspaces, eq(workspaces.id, skills.workspaceId))
				.where(eq(workspaces.userId, userId)),
			db
				.select({ n: count() })
				.from(workspaceEnvs)
				.innerJoin(workspaces, eq(workspaces.id, workspaceEnvs.workspaceId))
				.where(eq(workspaces.userId, userId)),
			db
				.select({ n: count() })
				.from(workspaceChannels)
				.innerJoin(workspaces, eq(workspaces.id, workspaceChannels.workspaceId))
				.where(eq(workspaces.userId, userId)),
			db
				.select({ n: count() })
				.from(workspaceMcp)
				.innerJoin(workspaces, eq(workspaces.id, workspaceMcp.workspaceId))
				.where(eq(workspaces.userId, userId)),
			db
				.select({ n: count() })
				.from(workspaceTemplates)
				.innerJoin(workspaces, eq(workspaces.id, workspaceTemplates.workspaceId))
				.where(and(eq(workspaces.userId, userId), ne(workspaceTemplates.templateType, 'user')))
		]);

	return {
		user: locals.user!,
		session: locals.session!,
		agents: userAgents.map((r) => r.agents),
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
