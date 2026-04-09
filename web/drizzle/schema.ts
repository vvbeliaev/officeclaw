import { pgTable, unique, uuid, text, boolean, timestamp, index, foreignKey, integer, primaryKey, pgEnum } from "drizzle-orm/pg-core"
import { sql } from "drizzle-orm"

export const agentStatus = pgEnum("agent_status", ['idle', 'running', 'error'])


export const user = pgTable("user", {
	id: uuid().defaultRandom().primaryKey().notNull(),
	name: text().default(').notNull(),
	email: text().notNull(),
	emailVerified: boolean("email_verified").default(false).notNull(),
	image: text(),
	createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
	updatedAt: timestamp("updated_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
	officeclawToken: text("officeclaw_token"),
}, (table) => [
	unique("user_email_key").on(table.email),
	unique("user_officeclaw_token_key").on(table.officeclawToken),
]);

export const session = pgTable("session", {
	id: text().primaryKey().notNull(),
	expiresAt: timestamp("expires_at", { withTimezone: true, mode: 'string' }).notNull(),
	token: text().notNull(),
	createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
	updatedAt: timestamp("updated_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
	ipAddress: text("ip_address"),
	userAgent: text("user_agent"),
	userId: uuid("user_id").notNull(),
}, (table) => [
	index("session_user_id_idx").using("btree", table.userId.asc().nullsLast().op("uuid_ops")),
	foreignKey({
			columns: [table.userId],
			foreignColumns: [user.id],
			name: "session_user_id_fkey"
		}).onDelete("cascade"),
	unique("session_token_key").on(table.token),
]);

export const account = pgTable("account", {
	id: text().primaryKey().notNull(),
	accountId: text("account_id").notNull(),
	providerId: text("provider_id").notNull(),
	userId: uuid("user_id").notNull(),
	accessToken: text("access_token"),
	refreshToken: text("refresh_token"),
	idToken: text("id_token"),
	accessTokenExpiresAt: timestamp("access_token_expires_at", { withTimezone: true, mode: 'string' }),
	refreshTokenExpiresAt: timestamp("refresh_token_expires_at", { withTimezone: true, mode: 'string' }),
	scope: text(),
	password: text(),
	createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
	updatedAt: timestamp("updated_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
}, (table) => [
	index("account_user_id_idx").using("btree", table.userId.asc().nullsLast().op("uuid_ops")),
	foreignKey({
			columns: [table.userId],
			foreignColumns: [user.id],
			name: "account_user_id_fkey"
		}).onDelete("cascade"),
]);

export const verification = pgTable("verification", {
	id: text().primaryKey().notNull(),
	identifier: text().notNull(),
	value: text().notNull(),
	expiresAt: timestamp("expires_at", { withTimezone: true, mode: 'string' }).notNull(),
	createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
	updatedAt: timestamp("updated_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
}, (table) => [
	index("verification_identifier_idx").using("btree", table.identifier.asc().nullsLast().op("text_ops")),
]);

export const agents = pgTable("agents", {
	id: uuid().defaultRandom().primaryKey().notNull(),
	userId: uuid("user_id").notNull(),
	name: text().notNull(),
	status: agentStatus().default('idle').notNull(),
	sandboxId: text("sandbox_id"),
	image: text().default('localhost:5005/officeclaw/agent:latest').notNull(),
	isAdmin: boolean("is_admin").default(false).notNull(),
	gatewayPort: integer("gateway_port"),
	createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
	updatedAt: timestamp("updated_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
}, (table) => [
	foreignKey({
			columns: [table.userId],
			foreignColumns: [user.id],
			name: "agents_user_id_fkey"
		}).onDelete("cascade"),
]);

export const agentFiles = pgTable("agent_files", {
	id: uuid().defaultRandom().primaryKey().notNull(),
	agentId: uuid("agent_id").notNull(),
	path: text().notNull(),
	content: text().default(').notNull(),
	updatedAt: timestamp("updated_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
}, (table) => [
	foreignKey({
			columns: [table.agentId],
			foreignColumns: [agents.id],
			name: "agent_files_agent_id_fkey"
		}).onDelete("cascade"),
	unique("agent_files_agent_id_path_key").on(table.path, table.agentId),
]);

export const skills = pgTable("skills", {
	id: uuid().defaultRandom().primaryKey().notNull(),
	userId: uuid("user_id").notNull(),
	name: text().notNull(),
	description: text().default(').notNull(),
	createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
}, (table) => [
	foreignKey({
			columns: [table.userId],
			foreignColumns: [user.id],
			name: "skills_user_id_fkey"
		}).onDelete("cascade"),
]);

export const skillFiles = pgTable("skill_files", {
	id: uuid().defaultRandom().primaryKey().notNull(),
	skillId: uuid("skill_id").notNull(),
	path: text().notNull(),
	content: text().default(').notNull(),
	updatedAt: timestamp("updated_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
}, (table) => [
	foreignKey({
			columns: [table.skillId],
			foreignColumns: [skills.id],
			name: "skill_files_skill_id_fkey"
		}).onDelete("cascade"),
	unique("skill_files_skill_id_path_key").on(table.skillId, table.path),
]);

export const userEnvs = pgTable("user_envs", {
	id: uuid().defaultRandom().primaryKey().notNull(),
	userId: uuid("user_id").notNull(),
	name: text().notNull(),
	// TODO: failed to parse database type 'bytea'
	valuesEncrypted: unknown("values_encrypted").notNull(),
	createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
}, (table) => [
	foreignKey({
			columns: [table.userId],
			foreignColumns: [user.id],
			name: "user_envs_user_id_fkey"
		}).onDelete("cascade"),
	unique("user_envs_user_id_name_key").on(table.userId, table.name),
]);

export const userChannels = pgTable("user_channels", {
	id: uuid().defaultRandom().primaryKey().notNull(),
	userId: uuid("user_id").notNull(),
	type: text().notNull(),
	// TODO: failed to parse database type 'bytea'
	configEncrypted: unknown("config_encrypted").notNull(),
	createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
}, (table) => [
	foreignKey({
			columns: [table.userId],
			foreignColumns: [user.id],
			name: "user_channels_user_id_fkey"
		}).onDelete("cascade"),
]);

export const agentMcp = pgTable("agent_mcp", {
	id: uuid().defaultRandom().primaryKey().notNull(),
	agentId: uuid("agent_id").notNull(),
	name: text().notNull(),
	// TODO: failed to parse database type 'bytea'
	configEncrypted: unknown("config_encrypted").notNull(),
}, (table) => [
	foreignKey({
			columns: [table.agentId],
			foreignColumns: [agents.id],
			name: "agent_mcp_agent_id_fkey"
		}).onDelete("cascade"),
	unique("agent_mcp_agent_id_name_key").on(table.name, table.agentId),
]);

export const agentSkills = pgTable("agent_skills", {
	agentId: uuid("agent_id").notNull(),
	skillId: uuid("skill_id").notNull(),
}, (table) => [
	foreignKey({
			columns: [table.agentId],
			foreignColumns: [agents.id],
			name: "agent_skills_agent_id_fkey"
		}).onDelete("cascade"),
	foreignKey({
			columns: [table.skillId],
			foreignColumns: [skills.id],
			name: "agent_skills_skill_id_fkey"
		}).onDelete("cascade"),
	primaryKey({ columns: [table.skillId, table.agentId], name: "agent_skills_pkey"}),
]);

export const agentEnvs = pgTable("agent_envs", {
	agentId: uuid("agent_id").notNull(),
	envId: uuid("env_id").notNull(),
}, (table) => [
	foreignKey({
			columns: [table.agentId],
			foreignColumns: [agents.id],
			name: "agent_envs_agent_id_fkey"
		}).onDelete("cascade"),
	foreignKey({
			columns: [table.envId],
			foreignColumns: [userEnvs.id],
			name: "agent_envs_env_id_fkey"
		}).onDelete("cascade"),
	primaryKey({ columns: [table.envId, table.agentId], name: "agent_envs_pkey"}),
]);

export const agentChannels = pgTable("agent_channels", {
	agentId: uuid("agent_id").notNull(),
	channelId: uuid("channel_id").notNull(),
}, (table) => [
	foreignKey({
			columns: [table.agentId],
			foreignColumns: [agents.id],
			name: "agent_channels_agent_id_fkey"
		}).onDelete("cascade"),
	foreignKey({
			columns: [table.channelId],
			foreignColumns: [userChannels.id],
			name: "agent_channels_channel_id_fkey"
		}).onDelete("cascade"),
	primaryKey({ columns: [table.channelId, table.agentId], name: "agent_channels_pkey"}),
]);
