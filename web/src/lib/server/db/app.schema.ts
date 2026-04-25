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
	bigint,
	jsonb,
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
	slug: text().notNull().unique(),
	officeclawToken: text('officeclaw_token').notNull().unique(),
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
	skillEvolution: boolean('skill_evolution').default(false).notNull(),
	heartbeatEnabled: boolean('heartbeat_enabled').default(false).notNull(),
	heartbeatIntervalS: integer('heartbeat_interval_s').default(1800).notNull(),
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
	workspaceId: uuid('workspace_id')
		.notNull()
		.references(() => workspaces.id, { onDelete: 'cascade' }),
	name: text().notNull(),
	description: text().default('').notNull(),
	always: boolean().default(false).notNull(),
	emoji: text(),
	homepage: text(),
	requiredBins: text('required_bins').array().default([]).notNull(),
	requiredEnvs: text('required_envs').array().default([]).notNull(),
	metadataExtra: jsonb('metadata_extra').default({}).notNull(),
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

export const workspaceCrons = pgTable(
	'workspace_crons',
	{
		id: uuid().defaultRandom().primaryKey().notNull(),
		workspaceId: uuid('workspace_id')
			.notNull()
			.references(() => workspaces.id, { onDelete: 'cascade' }),
		name: text().notNull(),
		scheduleKind: text('schedule_kind').notNull(), // 'at' | 'every' | 'cron'
		scheduleAtMs: bigint('schedule_at_ms', { mode: 'number' }),
		scheduleEveryMs: bigint('schedule_every_ms', { mode: 'number' }),
		scheduleExpr: text('schedule_expr'),
		scheduleTz: text('schedule_tz'),
		message: text().default('').notNull(),
		deliver: boolean().default(false).notNull(),
		channel: text(),
		recipient: text(),
		deleteAfterRun: boolean('delete_after_run').default(false).notNull(),
		createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
		updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow().notNull()
	},
	(t) => [unique('workspace_crons_workspace_id_name_key').on(t.workspaceId, t.name)]
);

export const agentCrons = pgTable(
	'agent_crons',
	{
		agentId: uuid('agent_id')
			.notNull()
			.references(() => agents.id, { onDelete: 'cascade' }),
		cronId: uuid('cron_id')
			.notNull()
			.references(() => workspaceCrons.id, { onDelete: 'cascade' }),
		enabled: boolean().default(true).notNull(),
		nextRunAtMs: bigint('next_run_at_ms', { mode: 'number' }),
		lastRunAtMs: bigint('last_run_at_ms', { mode: 'number' }),
		lastStatus: text('last_status'), // 'ok' | 'error' | 'skipped' | null
		lastError: text('last_error'),
		runHistory: jsonb('run_history').default([]).notNull()
	},
	(t) => [primaryKey({ columns: [t.agentId, t.cronId] })]
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

// One agent = one chat (matches nanobot's per-session model). Rows hold
// Vercel AI SDK UIMessage snapshots: `parts` is the typed payload
// (text / tool-X / reasoning) rendered by the chat UI.
export const agentChatMessages = pgTable(
	'agent_chat_messages',
	{
		id: uuid().defaultRandom().primaryKey().notNull(),
		agentId: uuid('agent_id')
			.notNull()
			.references(() => agents.id, { onDelete: 'cascade' }),
		messageId: text('message_id').notNull(),
		role: text().notNull(), // 'user' | 'assistant' | 'system' (DB CHECK enforces)
		parts: jsonb().notNull(),
		metadata: jsonb(),
		status: text().default('complete').notNull(), // 'pending' | 'complete' | 'failed'
		model: text(),
		createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
		updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow().notNull()
	},
	(t) => [
		unique('agent_chat_messages_agent_id_message_id_key').on(t.agentId, t.messageId),
		index('agent_chat_messages_agent_id_created_at_idx').on(t.agentId, t.createdAt)
	]
);

// Relations
export const workspacesRelations = relations(workspaces, ({ one, many }) => ({
	user: one(user, { fields: [workspaces.userId], references: [user.id] }),
	agents: many(agents),
	envs: many(workspaceEnvs),
	channels: many(workspaceChannels),
	mcp: many(workspaceMcp),
	templates: many(workspaceTemplates),
	crons: many(workspaceCrons)
}));

export const agentsRelations = relations(agents, ({ one, many }) => ({
	workspace: one(workspaces, { fields: [agents.workspaceId], references: [workspaces.id] }),
	files: many(agentFiles),
	skills: many(agentSkills),
	envs: many(agentEnvs),
	channels: many(agentChannels),
	mcp: many(agentMcp),
	templates: many(agentUserTemplates),
	crons: many(agentCrons),
	chatMessages: many(agentChatMessages)
}));

export const agentChatMessagesRelations = relations(agentChatMessages, ({ one }) => ({
	agent: one(agents, { fields: [agentChatMessages.agentId], references: [agents.id] })
}));

export const workspaceCronsRelations = relations(workspaceCrons, ({ one, many }) => ({
	workspace: one(workspaces, { fields: [workspaceCrons.workspaceId], references: [workspaces.id] }),
	agents: many(agentCrons)
}));

export const agentCronsRelations = relations(agentCrons, ({ one }) => ({
	agent: one(agents, { fields: [agentCrons.agentId], references: [agents.id] }),
	cron: one(workspaceCrons, { fields: [agentCrons.cronId], references: [workspaceCrons.id] })
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
	workspace: one(workspaces, { fields: [skills.workspaceId], references: [workspaces.id] }),
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
