import { relations } from "drizzle-orm/relations";
import { user, session, account, agents, agentFiles, skills, skillFiles, userEnvs, userChannels, agentMcp, agentSkills, agentEnvs, agentChannels } from "./schema";

export const sessionRelations = relations(session, ({one}) => ({
	user: one(user, {
		fields: [session.userId],
		references: [user.id]
	}),
}));

export const userRelations = relations(user, ({many}) => ({
	sessions: many(session),
	accounts: many(account),
	agents: many(agents),
	skills: many(skills),
	userEnvs: many(userEnvs),
	userChannels: many(userChannels),
}));

export const accountRelations = relations(account, ({one}) => ({
	user: one(user, {
		fields: [account.userId],
		references: [user.id]
	}),
}));

export const agentsRelations = relations(agents, ({one, many}) => ({
	user: one(user, {
		fields: [agents.userId],
		references: [user.id]
	}),
	agentFiles: many(agentFiles),
	agentMcps: many(agentMcp),
	agentSkills: many(agentSkills),
	agentEnvs: many(agentEnvs),
	agentChannels: many(agentChannels),
}));

export const agentFilesRelations = relations(agentFiles, ({one}) => ({
	agent: one(agents, {
		fields: [agentFiles.agentId],
		references: [agents.id]
	}),
}));

export const skillsRelations = relations(skills, ({one, many}) => ({
	user: one(user, {
		fields: [skills.userId],
		references: [user.id]
	}),
	skillFiles: many(skillFiles),
	agentSkills: many(agentSkills),
}));

export const skillFilesRelations = relations(skillFiles, ({one}) => ({
	skill: one(skills, {
		fields: [skillFiles.skillId],
		references: [skills.id]
	}),
}));

export const userEnvsRelations = relations(userEnvs, ({one, many}) => ({
	user: one(user, {
		fields: [userEnvs.userId],
		references: [user.id]
	}),
	agentEnvs: many(agentEnvs),
}));

export const userChannelsRelations = relations(userChannels, ({one, many}) => ({
	user: one(user, {
		fields: [userChannels.userId],
		references: [user.id]
	}),
	agentChannels: many(agentChannels),
}));

export const agentMcpRelations = relations(agentMcp, ({one}) => ({
	agent: one(agents, {
		fields: [agentMcp.agentId],
		references: [agents.id]
	}),
}));

export const agentSkillsRelations = relations(agentSkills, ({one}) => ({
	agent: one(agents, {
		fields: [agentSkills.agentId],
		references: [agents.id]
	}),
	skill: one(skills, {
		fields: [agentSkills.skillId],
		references: [skills.id]
	}),
}));

export const agentEnvsRelations = relations(agentEnvs, ({one}) => ({
	agent: one(agents, {
		fields: [agentEnvs.agentId],
		references: [agents.id]
	}),
	userEnv: one(userEnvs, {
		fields: [agentEnvs.envId],
		references: [userEnvs.id]
	}),
}));

export const agentChannelsRelations = relations(agentChannels, ({one}) => ({
	agent: one(agents, {
		fields: [agentChannels.agentId],
		references: [agents.id]
	}),
	userChannel: one(userChannels, {
		fields: [agentChannels.channelId],
		references: [userChannels.id]
	}),
}));