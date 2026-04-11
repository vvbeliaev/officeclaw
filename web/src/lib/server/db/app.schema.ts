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

export const agents = pgTable('agents', {
	id: uuid().defaultRandom().primaryKey().notNull(),
	userId: uuid('user_id')
		.notNull()
		.references(() => user.id, { onDelete: 'cascade' }),
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

export const userEnvs = pgTable(
	'user_envs',
	{
		id: uuid().defaultRandom().primaryKey().notNull(),
		userId: uuid('user_id')
			.notNull()
			.references(() => user.id, { onDelete: 'cascade' }),
		name: text().notNull(),
		category: text(), // null | 'system' | 'llm-provider'
		// values_encrypted (bytea) excluded — encrypted by Python, never read in web
		createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull()
	},
	(t) => [unique('user_envs_user_id_name_key').on(t.userId, t.name)]
);

export const userChannels = pgTable('user_channels', {
	id: uuid().defaultRandom().primaryKey().notNull(),
	userId: uuid('user_id')
		.notNull()
		.references(() => user.id, { onDelete: 'cascade' }),
	type: text().notNull(),
	// config_encrypted (bytea) excluded — encrypted by Python, never read in web
	createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull()
});

export const userMcp = pgTable(
	'user_mcp',
	{
		id: uuid().defaultRandom().primaryKey().notNull(),
		userId: uuid('user_id')
			.notNull()
			.references(() => user.id, { onDelete: 'cascade' }),
		name: text().notNull(),
		type: text().notNull(), // 'stdio' | 'http'
		// config_encrypted (bytea) excluded — encrypted by Python, never read in web
		createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull()
	},
	(t) => [unique('user_mcp_user_id_name_key').on(t.userId, t.name)]
);

export const agentMcp = pgTable(
	'agent_mcp',
	{
		agentId: uuid('agent_id')
			.notNull()
			.references(() => agents.id, { onDelete: 'cascade' }),
		mcpId: uuid('mcp_id')
			.notNull()
			.references(() => userMcp.id, { onDelete: 'cascade' })
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
			.references(() => userEnvs.id, { onDelete: 'cascade' })
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
			.references(() => userChannels.id, { onDelete: 'cascade' })
	},
	(t) => [
		primaryKey({ columns: [t.agentId, t.channelId] }),
		unique('agent_channels_channel_id_key').on(t.channelId)
	]
);

// Relations
export const agentsRelations = relations(agents, ({ one, many }) => ({
	user: one(user, { fields: [agents.userId], references: [user.id] }),
	files: many(agentFiles),
	skills: many(agentSkills),
	envs: many(agentEnvs),
	channels: many(agentChannels),
	mcp: many(agentMcp)
}));

export const agentFilesRelations = relations(agentFiles, ({ one }) => ({
	agent: one(agents, { fields: [agentFiles.agentId], references: [agents.id] })
}));
export const agentMcpRelations = relations(agentMcp, ({ one }) => ({
	agent: one(agents, { fields: [agentMcp.agentId], references: [agents.id] }),
	mcp: one(userMcp, { fields: [agentMcp.mcpId], references: [userMcp.id] })
}));
export const agentSkillsRelations = relations(agentSkills, ({ one }) => ({
	agent: one(agents, { fields: [agentSkills.agentId], references: [agents.id] }),
	skill: one(skills, { fields: [agentSkills.skillId], references: [skills.id] })
}));
export const agentEnvsRelations = relations(agentEnvs, ({ one }) => ({
	agent: one(agents, { fields: [agentEnvs.agentId], references: [agents.id] }),
	env: one(userEnvs, { fields: [agentEnvs.envId], references: [userEnvs.id] })
}));
export const agentChannelsRelations = relations(agentChannels, ({ one }) => ({
	agent: one(agents, { fields: [agentChannels.agentId], references: [agents.id] }),
	channel: one(userChannels, { fields: [agentChannels.channelId], references: [userChannels.id] })
}));

export const skillsRelations = relations(skills, ({ one, many }) => ({
	user: one(user, { fields: [skills.userId], references: [user.id] }),
	files: many(skillFiles),
	agents: many(agentSkills)
}));
export const skillFilesRelations = relations(skillFiles, ({ one }) => ({
	skill: one(skills, { fields: [skillFiles.skillId], references: [skills.id] })
}));
export const userEnvsRelations = relations(userEnvs, ({ one }) => ({
	user: one(user, { fields: [userEnvs.userId], references: [user.id] })
}));
export const userChannelsRelations = relations(userChannels, ({ one }) => ({
	user: one(user, { fields: [userChannels.userId], references: [user.id] })
}));
export const userMcpRelations = relations(userMcp, ({ one, many }) => ({
	user: one(user, { fields: [userMcp.userId], references: [user.id] }),
	agents: many(agentMcp)
}));
