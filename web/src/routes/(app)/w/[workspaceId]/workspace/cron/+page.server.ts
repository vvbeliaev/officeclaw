import { db } from '$lib/server/db';
import { workspaceCrons } from '$lib/server/db/app.schema';
import { eq, desc } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ parent }) => {
	const { workspace } = await parent();
	const crons = await db
		.select({
			id: workspaceCrons.id,
			name: workspaceCrons.name,
			scheduleKind: workspaceCrons.scheduleKind,
			scheduleAtMs: workspaceCrons.scheduleAtMs,
			scheduleEveryMs: workspaceCrons.scheduleEveryMs,
			scheduleExpr: workspaceCrons.scheduleExpr,
			scheduleTz: workspaceCrons.scheduleTz,
			message: workspaceCrons.message,
			deliver: workspaceCrons.deliver,
			channel: workspaceCrons.channel,
			recipient: workspaceCrons.recipient,
			deleteAfterRun: workspaceCrons.deleteAfterRun,
			createdAt: workspaceCrons.createdAt,
			updatedAt: workspaceCrons.updatedAt
		})
		.from(workspaceCrons)
		.where(eq(workspaceCrons.workspaceId, workspace.id))
		.orderBy(desc(workspaceCrons.createdAt));
	return { crons };
};
