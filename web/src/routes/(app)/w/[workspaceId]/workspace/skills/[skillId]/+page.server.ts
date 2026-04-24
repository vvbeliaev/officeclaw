import { error, fail, redirect } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { agents, agentSkills, skillFiles, skills, workspaces } from '$lib/server/db/app.schema';
import { and, eq, or } from 'drizzle-orm';
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

async function assertSkillOwnership(skillId: string, workspaceId: string): Promise<void> {
	const [owned] = await db
		.select({ id: skills.id })
		.from(skills)
		.where(and(eq(skills.id, skillId), eq(skills.workspaceId, workspaceId)))
		.limit(1);
	if (!owned) error(404, 'Skill not found');
}

export const load: PageServerLoad = async ({ params, parent }) => {
	const { workspace } = await parent();

	const [skill] = await db
		.select()
		.from(skills)
		.where(and(eq(skills.id, params.skillId), eq(skills.workspaceId, workspace.id)))
		.limit(1);

	if (!skill) error(404, 'Skill not found');

	const [files, attached] = await Promise.all([
		db
			.select({
				path: skillFiles.path,
				content: skillFiles.content,
				updatedAt: skillFiles.updatedAt
			})
			.from(skillFiles)
			.where(eq(skillFiles.skillId, params.skillId))
			.orderBy(skillFiles.path),
		db
			.select({ id: agents.id, name: agents.name })
			.from(agentSkills)
			.innerJoin(agents, eq(agents.id, agentSkills.agentId))
			.where(and(eq(agentSkills.skillId, params.skillId), eq(agents.workspaceId, workspace.id)))
			.orderBy(agents.name)
	]);

	return { skill, files, attachedAgents: attached };
};

export const actions: Actions = {
	save: async ({ params, request, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');
		const workspaceId = await resolveWorkspaceId(params.workspaceId, locals.user!.id);
		await assertSkillOwnership(params.skillId, workspaceId);

		const form = await request.formData();
		const path = form.get('path')?.toString();
		const content = form.get('content')?.toString() ?? '';
		if (!path) return fail(400, { error: 'path required' });

		const res = await fetch(`${API_URL}/skills/${params.skillId}/files`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ path, content })
		});

		if (!res.ok) {
			let msg = 'Failed to save';
			try {
				const data = await res.json();
				msg = data.detail ?? msg;
			} catch {
				msg = (await res.text()) || msg;
			}
			return fail(res.status, { error: msg });
		}
		return { saved: path };
	},

	deleteFile: async ({ params, request, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');
		const workspaceId = await resolveWorkspaceId(params.workspaceId, locals.user!.id);
		await assertSkillOwnership(params.skillId, workspaceId);

		const form = await request.formData();
		const path = form.get('path')?.toString();
		if (!path) return fail(400, { error: 'path required' });
		if (path === 'SKILL.md') return fail(400, { error: 'SKILL.md cannot be deleted' });

		const res = await fetch(`${API_URL}/skills/${params.skillId}/files`, {
			method: 'DELETE',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ path })
		});

		if (!res.ok && res.status !== 204) {
			const text = await res.text();
			return fail(res.status, { error: text || 'Failed to delete file' });
		}
		return { deletedPath: path };
	},

	updateMeta: async ({ params, request, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');
		const workspaceId = await resolveWorkspaceId(params.workspaceId, locals.user!.id);
		await assertSkillOwnership(params.skillId, workspaceId);

		const form = await request.formData();
		const body: Record<string, unknown> = {};

		const name = form.get('name')?.toString().trim();
		if (name) body.name = name;

		const description = form.get('description');
		if (description !== null) body.description = description.toString();

		// emoji / homepage: empty string → clear (null), otherwise set the value.
		const emoji = form.get('emoji');
		if (emoji !== null) {
			const v = emoji.toString().trim();
			body.emoji = v === '' ? null : v;
		}
		const homepage = form.get('homepage');
		if (homepage !== null) {
			const v = homepage.toString().trim();
			body.homepage = v === '' ? null : v;
		}

		const always = form.get('always');
		if (always !== null) body.always = always.toString() === 'true';

		const bins = form.get('required_bins');
		if (bins !== null) {
			try {
				body.required_bins = JSON.parse(bins.toString());
			} catch {
				return fail(400, { metaError: 'Invalid required_bins' });
			}
		}
		const envs = form.get('required_envs');
		if (envs !== null) {
			try {
				body.required_envs = JSON.parse(envs.toString());
			} catch {
				return fail(400, { metaError: 'Invalid required_envs' });
			}
		}

		if (Object.keys(body).length === 0) return fail(400, { metaError: 'Nothing to update' });

		const res = await fetch(`${API_URL}/skills/${params.skillId}`, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		});
		if (!res.ok) {
			const text = await res.text();
			return fail(res.status, { metaError: text || 'Failed to update' });
		}
		return { metaSaved: true };
	},

	deleteSkill: async ({ params, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');
		const workspaceId = await resolveWorkspaceId(params.workspaceId, locals.user!.id);
		await assertSkillOwnership(params.skillId, workspaceId);

		const res = await fetch(`${API_URL}/skills/${params.skillId}`, { method: 'DELETE' });
		if (!res.ok && res.status !== 204) {
			const text = await res.text();
			return fail(res.status, { error: text || 'Failed to delete skill' });
		}
		redirect(302, `/w/${params.workspaceId}/workspace/skills`);
	}
};
