import { error, fail, redirect } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import {
	agents,
	workspaceChannels,
	skills,
	workspaceEnvs,
	workspaceMcp,
	workspaceTemplates,
	workspaces,
	agentChannels,
	agentSkills,
	agentEnvs,
	agentMcp,
	agentUserTemplates
} from '$lib/server/db/app.schema';
import { and, eq, ne } from 'drizzle-orm';
import type { PageServerLoad, Actions } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const load: PageServerLoad = async ({ params, locals }) => {
	if (!locals.session) redirect(302, '/auth');
	const userId = locals.user!.id;

	const [agentRow] = await db
		.select()
		.from(agents)
		.innerJoin(workspaces, eq(workspaces.id, agents.workspaceId))
		.where(and(eq(agents.id, params.id), eq(workspaces.userId, userId)))
		.limit(1);

	if (!agentRow) error(404, 'Agent not found');

	const agent = agentRow.agents;
	const workspaceId = agentRow.workspaces.id;

	const [
		allChannels,
		allSkills,
		allEnvs,
		allMcps,
		allTemplates,
		attachedChannelRows,
		attachedSkillRows,
		attachedEnvRows,
		attachedMcpRows,
		attachedTemplateRows,
		channelAssignments
	] = await Promise.all([
		db
			.select({
				id: workspaceChannels.id,
				type: workspaceChannels.type,
				createdAt: workspaceChannels.createdAt
			})
			.from(workspaceChannels)
			.where(eq(workspaceChannels.workspaceId, workspaceId)),
		db
			.select({ id: skills.id, name: skills.name })
			.from(skills)
			.where(eq(skills.workspaceId, workspaceId)),
		db
			.select({ id: workspaceEnvs.id, name: workspaceEnvs.name, category: workspaceEnvs.category })
			.from(workspaceEnvs)
			.where(eq(workspaceEnvs.workspaceId, workspaceId)),
		db
			.select({ id: workspaceMcp.id, name: workspaceMcp.name, type: workspaceMcp.type })
			.from(workspaceMcp)
			.where(eq(workspaceMcp.workspaceId, workspaceId)),
		db
			.select({
				id: workspaceTemplates.id,
				name: workspaceTemplates.name,
				templateType: workspaceTemplates.templateType
			})
			.from(workspaceTemplates)
			.where(eq(workspaceTemplates.workspaceId, workspaceId))
			.orderBy(workspaceTemplates.templateType, workspaceTemplates.createdAt),
		db
			.select({ channelId: agentChannels.channelId })
			.from(agentChannels)
			.where(eq(agentChannels.agentId, params.id)),
		db
			.select({ skillId: agentSkills.skillId })
			.from(agentSkills)
			.where(eq(agentSkills.agentId, params.id)),
		db.select({ envId: agentEnvs.envId }).from(agentEnvs).where(eq(agentEnvs.agentId, params.id)),
		db.select({ mcpId: agentMcp.mcpId }).from(agentMcp).where(eq(agentMcp.agentId, params.id)),
		db
			.select({
				templateId: agentUserTemplates.templateId,
				templateType: agentUserTemplates.templateType
			})
			.from(agentUserTemplates)
			.where(eq(agentUserTemplates.agentId, params.id)),
		// All channel assignments across this workspace's agents — to detect channels taken by others
		db
			.select({
				channelId: agentChannels.channelId,
				agentId: agentChannels.agentId,
				agentName: agents.name
			})
			.from(agentChannels)
			.innerJoin(agents, eq(agents.id, agentChannels.agentId))
			.where(eq(agents.workspaceId, workspaceId))
	]);

	const attachedChannelIds = new Set(attachedChannelRows.map((r) => r.channelId));
	const attachedSkillIds = new Set(attachedSkillRows.map((r) => r.skillId));
	const attachedEnvIds = new Set(attachedEnvRows.map((r) => r.envId));
	const attachedMcpIds = new Set(attachedMcpRows.map((r) => r.mcpId));
	const attachedTemplateIds = new Set(attachedTemplateRows.map((r) => r.templateId));

	return {
		agent,
		channels: allChannels.map((c) => {
			const assignment = channelAssignments.find((a) => a.channelId === c.id);
			return {
				...c,
				attached: attachedChannelIds.has(c.id),
				takenBy: assignment && assignment.agentId !== params.id ? assignment.agentName : null
			};
		}),
		skills: allSkills.map((s) => ({ ...s, attached: attachedSkillIds.has(s.id) })),
		envs: allEnvs
			.filter((e) => e.category !== 'llm-provider')
			.map((e) => ({ ...e, attached: attachedEnvIds.has(e.id) })),
		llmProviders: allEnvs
			.filter((e) => e.category === 'llm-provider')
			.map((e) => ({ ...e, attached: attachedEnvIds.has(e.id) })),
		mcps: allMcps.map((m) => ({ ...m, attached: attachedMcpIds.has(m.id) })),
		templates: allTemplates.map((t) => ({ ...t, attached: attachedTemplateIds.has(t.id) }))
	};
};

export const actions: Actions = {
	update: async ({ params, request, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');

		const form = await request.formData();
		const name = form.get('name')?.toString().trim();

		if (!name) return fail(400, { error: 'Name is required' });

		const upstream = await fetch(`${API_URL}/agents/${params.id}`, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ name })
		});

		if (!upstream.ok) {
			const text = await upstream.text();
			return fail(upstream.status, { error: text || 'Failed to update agent' });
		}

		return { success: true };
	},

	uploadAvatar: async ({ params, request, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');

		const form = await request.formData();
		const file = form.get('avatar');
		if (!file || !(file instanceof File) || !file.size) {
			return fail(400, { avatarError: 'No file selected' });
		}

		const body = new FormData();
		body.append('file', file);

		const upstream = await fetch(`${API_URL}/agents/${params.id}/avatar`, {
			method: 'POST',
			body
		});

		if (!upstream.ok) {
			const text = await upstream.text();
			return fail(upstream.status, { avatarError: text || 'Upload failed' });
		}

		return { avatarSuccess: true };
	},

	delete: async ({ params, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');

		const [row] = await db
			.select({ id: agents.id, isAdmin: agents.isAdmin })
			.from(agents)
			.innerJoin(workspaces, eq(workspaces.id, agents.workspaceId))
			.where(and(eq(agents.id, params.id), eq(workspaces.userId, locals.user!.id)))
			.limit(1);

		if (!row) error(404, 'Agent not found');
		if (row.isAdmin) return fail(400, { error: 'Admin agent cannot be deleted' });

		const upstream = await fetch(`${API_URL}/agents/${params.id}`, { method: 'DELETE' });

		if (!upstream.ok && upstream.status !== 204) {
			const text = await upstream.text();
			return fail(upstream.status, { error: text || 'Failed to delete agent' });
		}

		redirect(302, '/');
	},

	attachChannel: async ({ params, request, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');
		const form = await request.formData();
		const channelId = form.get('channel_id')?.toString();
		if (!channelId) return fail(400, { error: 'channel_id required' });
		const res = await fetch(`${API_URL}/agents/${params.id}/channels/${channelId}`, {
			method: 'POST'
		});
		if (!res.ok) {
			return fail(res.status, {
				error: res.status === 409 ? 'Channel already assigned to another agent' : 'Failed to attach'
			});
		}
		return {};
	},

	detachChannel: async ({ params, request, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');
		const form = await request.formData();
		const channelId = form.get('channel_id')?.toString();
		if (!channelId) return fail(400, { error: 'channel_id required' });
		await fetch(`${API_URL}/agents/${params.id}/channels/${channelId}`, { method: 'DELETE' });
		return {};
	},

	attachSkill: async ({ params, request, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');
		const form = await request.formData();
		const skillId = form.get('skill_id')?.toString();
		if (!skillId) return fail(400, { error: 'skill_id required' });
		await fetch(`${API_URL}/agents/${params.id}/skills/${skillId}`, { method: 'POST' });
		return {};
	},

	detachSkill: async ({ params, request, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');
		const form = await request.formData();
		const skillId = form.get('skill_id')?.toString();
		if (!skillId) return fail(400, { error: 'skill_id required' });
		await fetch(`${API_URL}/agents/${params.id}/skills/${skillId}`, { method: 'DELETE' });
		return {};
	},

	attachEnv: async ({ params, request, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');
		const form = await request.formData();
		const envId = form.get('env_id')?.toString();
		if (!envId) return fail(400, { error: 'env_id required' });
		await fetch(`${API_URL}/agents/${params.id}/envs/${envId}`, { method: 'POST' });
		return {};
	},

	detachEnv: async ({ params, request, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');
		const form = await request.formData();
		const envId = form.get('env_id')?.toString();
		if (!envId) return fail(400, { error: 'env_id required' });
		await fetch(`${API_URL}/agents/${params.id}/envs/${envId}`, { method: 'DELETE' });
		return {};
	},

	// Swap active LLM provider: detach old (if any), attach new
	switchLlm: async ({ params, request, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');
		const form = await request.formData();
		const newEnvId = form.get('env_id')?.toString();
		const oldEnvId = form.get('old_env_id')?.toString();
		if (!newEnvId) return fail(400, { error: 'env_id required' });
		if (oldEnvId && oldEnvId !== newEnvId) {
			await fetch(`${API_URL}/agents/${params.id}/envs/${oldEnvId}`, { method: 'DELETE' });
		}
		await fetch(`${API_URL}/agents/${params.id}/envs/${newEnvId}`, { method: 'POST' });
		return {};
	},

	attachMcp: async ({ params, request, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');
		const form = await request.formData();
		const mcpId = form.get('mcp_id')?.toString();
		if (!mcpId) return fail(400, { error: 'mcp_id required' });
		await fetch(`${API_URL}/agents/${params.id}/mcp/${mcpId}`, { method: 'POST' });
		return {};
	},

	detachMcp: async ({ params, request, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');
		const form = await request.formData();
		const mcpId = form.get('mcp_id')?.toString();
		if (!mcpId) return fail(400, { error: 'mcp_id required' });
		await fetch(`${API_URL}/agents/${params.id}/mcp/${mcpId}`, { method: 'DELETE' });
		return {};
	},

	attachTemplate: async ({ params, request, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');
		const form = await request.formData();
		const templateId = form.get('template_id')?.toString();
		if (!templateId) return fail(400, { error: 'template_id required' });
		await fetch(`${API_URL}/agents/${params.id}/templates/${templateId}`, { method: 'POST' });
		return {};
	},

	detachTemplate: async ({ params, request, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');
		const form = await request.formData();
		const templateId = form.get('template_id')?.toString();
		if (!templateId) return fail(400, { error: 'template_id required' });
		await fetch(`${API_URL}/agents/${params.id}/templates/${templateId}`, { method: 'DELETE' });
		return {};
	}
};
