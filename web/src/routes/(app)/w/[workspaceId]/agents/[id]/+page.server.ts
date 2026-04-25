import { error } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { agents, agentChatMessages } from '$lib/server/db/app.schema';
import { and, asc, eq } from 'drizzle-orm';
import type { UIMessage } from 'ai';
import { resolveWorkspaceId } from '$lib/server/workspace-token';
import type { PageServerLoad } from './$types';

// NOTE: do NOT `await parent()` here. The parent layout is tagged with
// `depends('app:agents-list')` and the chat page invalidates that key
// after admin streaming completes — pulling from parent would cascade
// the invalidation into this load, return a new `agent` reference, and
// recreate the `$derived(new Chat(...))` instance, wiping the stream.
export const load: PageServerLoad = async ({ params, locals }) => {
	const wsId = await resolveWorkspaceId(params.workspaceId, locals.user!.id);
	if (!wsId) error(403, 'Workspace not found');

	const [agent] = await db
		.select()
		.from(agents)
		.where(and(eq(agents.id, params.id), eq(agents.workspaceId, wsId)))
		.limit(1);

	if (!agent) {
		error(404, 'Agent not found');
	}

	const rows = await db
		.select({
			messageId: agentChatMessages.messageId,
			role: agentChatMessages.role,
			parts: agentChatMessages.parts,
			metadata: agentChatMessages.metadata
		})
		.from(agentChatMessages)
		.where(eq(agentChatMessages.agentId, agent.id))
		.orderBy(asc(agentChatMessages.createdAt));

	const initialMessages: UIMessage[] = rows.map((r) => ({
		id: r.messageId,
		role: r.role as UIMessage['role'],
		parts: (r.parts ?? []) as UIMessage['parts'],
		metadata: r.metadata ?? undefined
	}));

	return { agent, initialMessages };
};
