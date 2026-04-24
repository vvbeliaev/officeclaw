import { error, fail } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { skills, skillFiles, agentSkills, agents, workspaces } from '$lib/server/db/app.schema';
import { and, eq, or, sql } from 'drizzle-orm';
import type { PageServerLoad, Actions } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

async function resolveWorkspaceId(param: string, userId: string): Promise<string> {
	const condition = UUID_RE.test(param)
		? or(eq(workspaces.id, param), eq(workspaces.slug, param))
		: eq(workspaces.slug, param);
	const [row] = await db
		.select({ id: workspaces.id })
		.from(workspaces)
		.where(and(condition, eq(workspaces.userId, userId)))
		.limit(1);
	if (!row) error(403, 'Workspace not found');
	return row.id;
}

export const load: PageServerLoad = async ({ parent }) => {
	const { workspace } = await parent();

	const rows = await db
		.select({
			id: skills.id,
			name: skills.name,
			description: skills.description,
			always: skills.always,
			emoji: skills.emoji,
			homepage: skills.homepage,
			createdAt: skills.createdAt,
			fileCount: sql<number>`(
				SELECT COUNT(*)::int FROM ${skillFiles} WHERE ${skillFiles.skillId} = ${skills.id}
			)`,
			agentCount: sql<number>`(
				SELECT COUNT(*)::int FROM ${agentSkills}
				INNER JOIN ${agents} ON ${agents.id} = ${agentSkills.agentId}
				WHERE ${agentSkills.skillId} = ${skills.id}
				  AND ${agents.workspaceId} = ${workspace.id}
			)`
		})
		.from(skills)
		.where(eq(skills.workspaceId, workspace.id))
		.orderBy(skills.name);

	return { skills: rows };
};

export const actions: Actions = {
	create: async ({ request, locals, params }) => {
		if (!locals.session) error(401, 'Unauthorized');
		const workspaceId = await resolveWorkspaceId(params.workspaceId, locals.user!.id);

		const form = await request.formData();
		const name = form.get('name')?.toString().trim();
		const description = form.get('description')?.toString().trim() ?? '';

		if (!name) return fail(400, { error: 'Name is required' });

		const res = await fetch(`${API_URL}/skills`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ workspace_id: workspaceId, name, description })
		});

		if (!res.ok) {
			const text = await res.text();
			return fail(res.status, { error: text || 'Failed to create skill' });
		}

		const created = (await res.json()) as { id: string };
		return { createdId: created.id };
	},

	importClawhub: async ({ request, locals, params }) => {
		if (!locals.session) error(401, 'Unauthorized');
		const workspaceId = await resolveWorkspaceId(params.workspaceId, locals.user!.id);

		const form = await request.formData();
		const url = form.get('url')?.toString().trim();
		if (!url) return fail(400, { importError: 'URL is required' });

		const res = await fetch(`${API_URL}/skills/import-clawhub`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ workspace_id: workspaceId, url })
		});

		if (!res.ok) {
			let msg = 'Import failed';
			try {
				const data = await res.json();
				msg = data.detail ?? msg;
			} catch {
				msg = (await res.text()) || msg;
			}
			return fail(res.status, { importError: msg });
		}

		const created = (await res.json()) as { id: string };
		return { importedId: created.id };
	},

	delete: async ({ request, locals, params }) => {
		if (!locals.session) error(401, 'Unauthorized');
		const workspaceId = await resolveWorkspaceId(params.workspaceId, locals.user!.id);

		const form = await request.formData();
		const skillId = form.get('skill_id')?.toString();
		if (!skillId) return fail(400, { error: 'skill_id required' });

		// Ownership check via workspace
		const [owned] = await db
			.select({ id: skills.id })
			.from(skills)
			.where(and(eq(skills.id, skillId), eq(skills.workspaceId, workspaceId)))
			.limit(1);
		if (!owned) return fail(404, { error: 'Skill not found' });

		const res = await fetch(`${API_URL}/skills/${skillId}`, { method: 'DELETE' });
		if (!res.ok && res.status !== 204) {
			const text = await res.text();
			return fail(res.status, { error: text || 'Failed to delete' });
		}
		return { deletedId: skillId };
	}
};
