import { error } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import {
	agents,
	workspaces,
	skills,
	workspaceEnvs,
	workspaceChannels,
	workspaceMcp,
	workspaceTemplates
} from '$lib/server/db/app.schema';
import { and, eq, ne, desc, count } from 'drizzle-orm';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals, params }) => {
	const workspaceId = params.workspaceId;

	// Validate ownership
	const [workspace] = await db
		.select()
		.from(workspaces)
		.where(and(eq(workspaces.id, workspaceId), eq(workspaces.userId, locals.user!.id)))
		.limit(1);

	if (!workspace) error(403, 'Workspace not found');

	const [userAgents, [skillsCount], [envsCount], [channelsCount], [mcpCount], [promptsCount]] =
		await Promise.all([
			db
				.select()
				.from(agents)
				.where(eq(agents.workspaceId, workspaceId))
				.orderBy(desc(agents.isAdmin), desc(agents.createdAt)),
			db.select({ n: count() }).from(skills).where(eq(skills.workspaceId, workspaceId)),
			db.select({ n: count() }).from(workspaceEnvs).where(eq(workspaceEnvs.workspaceId, workspaceId)),
			db.select({ n: count() }).from(workspaceChannels).where(eq(workspaceChannels.workspaceId, workspaceId)),
			db.select({ n: count() }).from(workspaceMcp).where(eq(workspaceMcp.workspaceId, workspaceId)),
			db
				.select({ n: count() })
				.from(workspaceTemplates)
				.where(
					and(
						eq(workspaceTemplates.workspaceId, workspaceId),
						ne(workspaceTemplates.templateType, 'user')
					)
				)
		]);

	return {
		workspace,
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
