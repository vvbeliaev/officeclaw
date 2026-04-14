import { db } from '$lib/server/db';
import { workspaces } from '$lib/server/db/app.schema';
import { and, eq } from 'drizzle-orm';

/** Returns the officeclaw_token for a workspace the user owns, or null if not found. */
export async function getWorkspaceToken(
	workspaceId: string,
	userId: string
): Promise<string | null> {
	const [ws] = await db
		.select({ token: workspaces.officeclawToken })
		.from(workspaces)
		.where(and(eq(workspaces.id, workspaceId), eq(workspaces.userId, userId)))
		.limit(1);
	return ws?.token ?? null;
}
