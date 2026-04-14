import { db } from '$lib/server/db';
import { workspaces } from '$lib/server/db/app.schema';
import { and, eq, or } from 'drizzle-orm';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Returns the officeclaw_token for a workspace the user owns, or null if not found.
 *  Accepts either a UUID or a slug as workspaceId. */
export async function getWorkspaceToken(
	workspaceId: string,
	userId: string
): Promise<string | null> {
	const idCondition = UUID_RE.test(workspaceId)
		? or(eq(workspaces.id, workspaceId), eq(workspaces.slug, workspaceId))
		: eq(workspaces.slug, workspaceId);

	const [ws] = await db
		.select({ token: workspaces.officeclawToken })
		.from(workspaces)
		.where(and(idCondition, eq(workspaces.userId, userId)))
		.limit(1);
	return ws?.token ?? null;
}
