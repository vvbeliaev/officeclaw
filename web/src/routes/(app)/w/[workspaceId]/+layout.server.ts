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
import { and, eq, ne, or, desc, count } from 'drizzle-orm';
import type { LayoutServerLoad } from './$types';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export const load: LayoutServerLoad = async ({ locals, params }) => {
	const workspaceId = params.workspaceId;

	// Accept both UUID (legacy) and slug in the URL param
	const idCondition = UUID_RE.test(workspaceId)
		? or(eq(workspaces.id, workspaceId), eq(workspaces.slug, workspaceId))
		: eq(workspaces.slug, workspaceId);

	// Validate ownership
	const [workspace] = await db
		.select()
		.from(workspaces)
		.where(and(idCondition, eq(workspaces.userId, locals.user!.id)))
		.limit(1);

	if (!workspace) error(403, 'Workspace not found');

	// Use the real UUID for all subsequent queries (params.workspaceId may be a slug)
	const wsId = workspace.id;

	const [userAgents, [skillsCount], [envsCount], [channelsCount], [mcpCount], [promptsCount]] =
		await Promise.all([
			db
				.select()
				.from(agents)
				.where(eq(agents.workspaceId, wsId))
				.orderBy(desc(agents.isAdmin), desc(agents.createdAt)),
			db.select({ n: count() }).from(skills).where(eq(skills.workspaceId, wsId)),
			db.select({ n: count() }).from(workspaceEnvs).where(eq(workspaceEnvs.workspaceId, wsId)),
			db
				.select({ n: count() })
				.from(workspaceChannels)
				.where(eq(workspaceChannels.workspaceId, wsId)),
			db.select({ n: count() }).from(workspaceMcp).where(eq(workspaceMcp.workspaceId, wsId)),
			db
				.select({ n: count() })
				.from(workspaceTemplates)
				.where(
					and(eq(workspaceTemplates.workspaceId, wsId), ne(workspaceTemplates.templateType, 'user'))
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
