// AUTO-GENERATED from Postgres via `pnpm db:introspect`
// Do not edit manually — run `pnpm db:introspect` after Python migrations.
// Note: bytea (encrypted) columns are excluded — web never reads raw encrypted data.

import {
	pgTable,
	pgEnum,
	uuid,
	text,
	boolean,
	timestamp,
	integer,
	primaryKey,
	foreignKey,
	unique,
	index
} from 'drizzle-orm/pg-core';
import { relations } from 'drizzle-orm';
import { user } from './auth.schema';

export const agentStatus = pgEnum('agent_status', ['idle', 'running', 'error']);

export const workspaces = pgTable('workspaces', {
	id: uuid().defaultRandom().primaryKey().notNull(),
	userId: uuid('user_id')
		.notNull()
		.references(() => user.id, { onDelete: 'cascade' }),
	name: text().notNull(),
	officeclawToken: text('officeclaw_token').unique(),
	createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull()
});

export const agents = pgTable('agents', {
	id: uuid().defaultRandom().primaryKey().notNull(),
	workspaceId: uuid('workspace_id')
		.notNull()
		.references(() => workspaces.id, { onDelete: 'cascade' }),
	name: text().notNull(),
	status: agentStatus().default('idle').notNull(),
	sandboxId: text('sandbox_id'),
	image: text().notNull(),
	isAdmin: boolean('is_admin').default(false).notNull(),
	avatarUrl: text('avatar_url'),
	gatewayPort: integer('gateway_port'),
	createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
	updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow().notNull()
});

export const agentFiles = pgTable(
	'agent_files',
	{
		id: uuid().defaultRandom().primaryKey().notNull(),
		agentId: uuid('agent_id')
			.notNull()
			.references(() => agents.id, { onDelete: 'cascade' }),
		path: text().notNull(),
		content: text().default('').notNull(),
		updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow().notNull()
	},
	(t) => [unique('agent_files_agent_id_path_key').on(t.agentId, t.path)]
);

export const skills = pgTable('skills', {
	id: uuid().defaultRandom().primaryKey().notNull(),
	userId: uuid('user_id')
		.notNull()
		.references(() => user.id, { onDelete: 'cascade' }),
	name: text().notNull(),
	description: text().default('').notNull(),
	createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull()
});

export const skillFiles = pgTable(
	'skill_files',
	{
		id: uuid().defaultRandom().primaryKey().notNull(),
		skillId: uuid('skill_id')
			.notNull()
			.references(() => skills.id, { onDelete: 'cascade' }),
		path: text().notNull(),
		content: text().default('').notNull(),
		updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow().notNull()
	},
	(t) => [unique('skill_files_skill_id_path_key').on(t.skillId, t.path)]
);

export const workspaceEnvs = pgTable(
	'workspace_envs',
	{
		id: uuid().defaultRandom().primaryKey().notNull(),
		workspaceId: uuid('workspace_id')
			.notNull()
			.references(() => workspaces.id, { onDelete: 'cascade' }),
		name: text().notNull(),
		category: text(), // null | 'system' | 'llm-provider'
		// values_encrypted (bytea) excluded — encrypted by Python, never read in web
		createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull()
	},
	(t) => [unique('workspace_envs_workspace_id_name_key').on(t.workspaceId, t.name)]
);

export const workspaceChannels = pgTable('workspace_channels', {
	id: uuid().defaultRandom().primaryKey().notNull(),
	workspaceId: uuid('workspace_id')
		.notNull()
		.references(() => workspaces.id, { onDelete: 'cascade' }),
	name: text().notNull(),
	type: text().notNull(),
	// config_encrypted (bytea) excluded — encrypted by Python, never read in web
	createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull()
});

export const workspaceMcp = pgTable(
	'workspace_mcp',
	{
		id: uuid().defaultRandom().primaryKey().notNull(),
		workspaceId: uuid('workspace_id')
			.notNull()
			.references(() => workspaces.id, { onDelete: 'cascade' }),
		name: text().notNull(),
		type: text().notNull(), // 'stdio' | 'http'
		// config_encrypted (bytea) excluded — encrypted by Python, never read in web
		createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull()
	},
	(t) => [unique('workspace_mcp_workspace_id_name_key').on(t.workspaceId, t.name)]
);

export const workspaceTemplates = pgTable('workspace_templates', {
	id: uuid().defaultRandom().primaryKey().notNull(),
	workspaceId: uuid('workspace_id')
		.notNull()
		.references(() => workspaces.id, { onDelete: 'cascade' }),
	name: text().notNull(),
	templateType: text('template_type').notNull(), // 'user'|'soul'|'agents'|'heartbeat'|'tools'
	content: text().default('').notNull(),
	createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
	updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow().notNull()
});

export const agentUserTemplates = pgTable(
	'agent_user_templates',
	{
		agentId: uuid('agent_id')
			.notNull()
			.references(() => agents.id, { onDelete: 'cascade' }),
		templateId: uuid('template_id')
			.notNull()
			.references(() => workspaceTemplates.id, { onDelete: 'cascade' }),
		templateType: text('template_type').notNull()
	},
	(t) => [
		primaryKey({ columns: [t.agentId, t.templateId] }),
		unique('agent_user_templates_agent_id_template_type_key').on(t.agentId, t.templateType)
	]
);

export const agentMcp = pgTable(
	'agent_mcp',
	{
		agentId: uuid('agent_id')
			.notNull()
			.references(() => agents.id, { onDelete: 'cascade' }),
		mcpId: uuid('mcp_id')
			.notNull()
			.references(() => workspaceMcp.id, { onDelete: 'cascade' })
	},
	(t) => [primaryKey({ columns: [t.agentId, t.mcpId] })]
);

export const agentSkills = pgTable(
	'agent_skills',
	{
		agentId: uuid('agent_id')
			.notNull()
			.references(() => agents.id, { onDelete: 'cascade' }),
		skillId: uuid('skill_id')
			.notNull()
			.references(() => skills.id, { onDelete: 'cascade' })
	},
	(t) => [primaryKey({ columns: [t.agentId, t.skillId] })]
);

export const agentEnvs = pgTable(
	'agent_envs',
	{
		agentId: uuid('agent_id')
			.notNull()
			.references(() => agents.id, { onDelete: 'cascade' }),
		envId: uuid('env_id')
			.notNull()
			.references(() => workspaceEnvs.id, { onDelete: 'cascade' })
	},
	(t) => [primaryKey({ columns: [t.agentId, t.envId] })]
);

export const agentChannels = pgTable(
	'agent_channels',
	{
		agentId: uuid('agent_id')
			.notNull()
			.references(() => agents.id, { onDelete: 'cascade' }),
		channelId: uuid('channel_id')
			.notNull()
			.references(() => workspaceChannels.id, { onDelete: 'cascade' })
	},
	(t) => [
		primaryKey({ columns: [t.agentId, t.channelId] }),
		unique('agent_channels_channel_id_key').on(t.channelId)
	]
);

// Relations
export const workspacesRelations = relations(workspaces, ({ one, many }) => ({
	user: one(user, { fields: [workspaces.userId], references: [user.id] }),
	agents: many(agents),
	envs: many(workspaceEnvs),
	channels: many(workspaceChannels),
	mcp: many(workspaceMcp),
	templates: many(workspaceTemplates)
}));

export const agentsRelations = relations(agents, ({ one, many }) => ({
	workspace: one(workspaces, { fields: [agents.workspaceId], references: [workspaces.id] }),
	files: many(agentFiles),
	skills: many(agentSkills),
	envs: many(agentEnvs),
	channels: many(agentChannels),
	mcp: many(agentMcp),
	templates: many(agentUserTemplates)
}));

export const agentFilesRelations = relations(agentFiles, ({ one }) => ({
	agent: one(agents, { fields: [agentFiles.agentId], references: [agents.id] })
}));
export const agentMcpRelations = relations(agentMcp, ({ one }) => ({
	agent: one(agents, { fields: [agentMcp.agentId], references: [agents.id] }),
	mcp: one(workspaceMcp, { fields: [agentMcp.mcpId], references: [workspaceMcp.id] })
}));
export const agentSkillsRelations = relations(agentSkills, ({ one }) => ({
	agent: one(agents, { fields: [agentSkills.agentId], references: [agents.id] }),
	skill: one(skills, { fields: [agentSkills.skillId], references: [skills.id] })
}));
export const agentEnvsRelations = relations(agentEnvs, ({ one }) => ({
	agent: one(agents, { fields: [agentEnvs.agentId], references: [agents.id] }),
	env: one(workspaceEnvs, { fields: [agentEnvs.envId], references: [workspaceEnvs.id] })
}));
export const agentChannelsRelations = relations(agentChannels, ({ one }) => ({
	agent: one(agents, { fields: [agentChannels.agentId], references: [agents.id] }),
	channel: one(workspaceChannels, {
		fields: [agentChannels.channelId],
		references: [workspaceChannels.id]
	})
}));

export const skillsRelations = relations(skills, ({ one, many }) => ({
	user: one(user, { fields: [skills.userId], references: [user.id] }),
	files: many(skillFiles),
	agents: many(agentSkills)
}));
export const skillFilesRelations = relations(skillFiles, ({ one }) => ({
	skill: one(skills, { fields: [skillFiles.skillId], references: [skills.id] })
}));
export const workspaceEnvsRelations = relations(workspaceEnvs, ({ one }) => ({
	workspace: one(workspaces, { fields: [workspaceEnvs.workspaceId], references: [workspaces.id] })
}));
export const workspaceChannelsRelations = relations(workspaceChannels, ({ one }) => ({
	workspace: one(workspaces, {
		fields: [workspaceChannels.workspaceId],
		references: [workspaces.id]
	})
}));
export const workspaceMcpRelations = relations(workspaceMcp, ({ one, many }) => ({
	workspace: one(workspaces, { fields: [workspaceMcp.workspaceId], references: [workspaces.id] }),
	agents: many(agentMcp)
}));

export const workspaceTemplatesRelations = relations(workspaceTemplates, ({ one, many }) => ({
	workspace: one(workspaces, {
		fields: [workspaceTemplates.workspaceId],
		references: [workspaces.id]
	}),
	agents: many(agentUserTemplates)
}));

export const agentUserTemplatesRelations = relations(agentUserTemplates, ({ one }) => ({
	agent: one(agents, { fields: [agentUserTemplates.agentId], references: [agents.id] }),
	template: one(workspaceTemplates, {
		fields: [agentUserTemplates.templateId],
		references: [workspaceTemplates.id]
	})
}));
