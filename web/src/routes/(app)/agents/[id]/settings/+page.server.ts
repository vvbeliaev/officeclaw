import { error, fail, redirect } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import {
	agents,
	userChannels,
	skills,
	userEnvs,
	userMcp,
	agentChannels,
	agentSkills,
	agentEnvs,
	agentMcp
} from '$lib/server/db/app.schema';
import { and, eq } from 'drizzle-orm';
import type { PageServerLoad, Actions } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const load: PageServerLoad = async ({ params, locals }) => {
	if (!locals.session) redirect(302, '/auth');
	const userId = locals.user!.id;

	const [agent] = await db
		.select()
		.from(agents)
		.where(and(eq(agents.id, params.id), eq(agents.userId, userId)))
		.limit(1);

	if (!agent) error(404, 'Agent not found');

	const [
		allChannels,
		allSkills,
		allEnvs,
		allMcps,
		attachedChannelRows,
		attachedSkillRows,
		attachedEnvRows,
		attachedMcpRows,
		channelAssignments
	] = await Promise.all([
		db
			.select({ id: userChannels.id, type: userChannels.type, createdAt: userChannels.createdAt })
			.from(userChannels)
			.where(eq(userChannels.userId, userId)),
		db.select({ id: skills.id, name: skills.name }).from(skills).where(eq(skills.userId, userId)),
		db
			.select({ id: userEnvs.id, name: userEnvs.name, category: userEnvs.category })
			.from(userEnvs)
			.where(eq(userEnvs.userId, userId)),
		db
			.select({ id: userMcp.id, name: userMcp.name, type: userMcp.type })
			.from(userMcp)
			.where(eq(userMcp.userId, userId)),
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
		// All channel assignments across this user's agents — to detect channels taken by others
		db
			.select({
				channelId: agentChannels.channelId,
				agentId: agentChannels.agentId,
				agentName: agents.name
			})
			.from(agentChannels)
			.innerJoin(agents, eq(agents.id, agentChannels.agentId))
			.where(eq(agents.userId, userId))
	]);

	const attachedChannelIds = new Set(attachedChannelRows.map((r) => r.channelId));
	const attachedSkillIds = new Set(attachedSkillRows.map((r) => r.skillId));
	const attachedEnvIds = new Set(attachedEnvRows.map((r) => r.envId));
	const attachedMcpIds = new Set(attachedMcpRows.map((r) => r.mcpId));

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
		mcps: allMcps.map((m) => ({ ...m, attached: attachedMcpIds.has(m.id) }))
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

	delete: async ({ params, locals }) => {
		if (!locals.session) error(401, 'Unauthorized');

		const [agent] = await db
			.select({ id: agents.id, isAdmin: agents.isAdmin })
			.from(agents)
			.where(and(eq(agents.id, params.id), eq(agents.userId, locals.user!.id)))
			.limit(1);

		if (!agent) error(404, 'Agent not found');
		if (agent.isAdmin) return fail(400, { error: 'Admin agent cannot be deleted' });

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
	}
};
