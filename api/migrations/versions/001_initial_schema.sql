-- ============================================================
-- OfficeClaw — consolidated initial schema
-- better-auth core tables + app domain tables
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS vector;

-- ── better-auth ─────────────────────────────────────────────

CREATE TABLE "user" (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name             TEXT        NOT NULL DEFAULT '',
    email            TEXT        NOT NULL UNIQUE,
    email_verified   BOOLEAN     NOT NULL DEFAULT FALSE,
    image            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- officeclaw_token removed: lives on workspaces now
);

CREATE TABLE "session" (
    id         TEXT        PRIMARY KEY,
    expires_at TIMESTAMPTZ NOT NULL,
    token      TEXT        NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address TEXT,
    user_agent TEXT,
    user_id    UUID        NOT NULL REFERENCES "user"(id) ON DELETE CASCADE
);

CREATE TABLE "account" (
    id                       TEXT        PRIMARY KEY,
    account_id               TEXT        NOT NULL,
    provider_id              TEXT        NOT NULL,
    user_id                  UUID        NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    access_token             TEXT,
    refresh_token            TEXT,
    id_token                 TEXT,
    access_token_expires_at  TIMESTAMPTZ,
    refresh_token_expires_at TIMESTAMPTZ,
    scope                    TEXT,
    password                 TEXT,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE "verification" (
    id         TEXT        PRIMARY KEY,
    identifier TEXT        NOT NULL,
    value      TEXT        NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX session_user_id_idx         ON "session"(user_id);
CREATE INDEX account_user_id_idx         ON "account"(user_id);
CREATE INDEX verification_identifier_idx ON "verification"(identifier);

-- ── workspaces ──────────────────────────────────────────────

CREATE TABLE workspaces (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID        NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    name             TEXT        NOT NULL,
    officeclaw_token TEXT        UNIQUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX workspaces_user_id_idx ON workspaces(user_id);

-- ── app domain ──────────────────────────────────────────────

CREATE TYPE agent_status AS ENUM ('idle', 'running', 'error');

CREATE TABLE agents (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID         NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name         TEXT         NOT NULL,
    status       agent_status NOT NULL DEFAULT 'idle',
    sandbox_id   TEXT,
    image        TEXT         NOT NULL DEFAULT 'localhost:5005/officeclaw/agent:latest',
    is_admin     BOOLEAN      NOT NULL DEFAULT FALSE,
    gateway_port INTEGER,
    avatar_url   TEXT,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE agent_files (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id   UUID        NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    path       TEXT        NOT NULL,
    content    TEXT        NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(agent_id, path)
);

CREATE TABLE skills (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID       NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name        TEXT        NOT NULL,
    description TEXT        NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE skill_files (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id   UUID        NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    path       TEXT        NOT NULL,
    content    TEXT        NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(skill_id, path)
);

CREATE TABLE workspace_envs (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id     UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name             TEXT        NOT NULL,
    values_encrypted BYTEA       NOT NULL,
    category         TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(workspace_id, name)
);

CREATE TABLE workspace_channels (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id     UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name             TEXT        NOT NULL,
    type             TEXT        NOT NULL,
    config_encrypted BYTEA       NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE workspace_mcp (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id     UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name             TEXT        NOT NULL,
    type             TEXT        NOT NULL DEFAULT 'http',
    config_encrypted BYTEA       NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(workspace_id, name)
);

CREATE TABLE workspace_templates (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id  UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name          TEXT        NOT NULL,
    template_type TEXT        NOT NULL CHECK (template_type IN ('user','soul','agents','heartbeat','tools')),
    content       TEXT        NOT NULL DEFAULT '',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE agent_skills (
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (agent_id, skill_id)
);

CREATE TABLE agent_envs (
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    env_id   UUID NOT NULL REFERENCES workspace_envs(id) ON DELETE CASCADE,
    PRIMARY KEY (agent_id, env_id)
);

CREATE TABLE agent_channels (
    agent_id   UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    channel_id UUID NOT NULL REFERENCES workspace_channels(id) ON DELETE CASCADE,
    PRIMARY KEY (agent_id, channel_id),
    UNIQUE(channel_id)
);

CREATE TABLE agent_mcp (
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    mcp_id   UUID NOT NULL REFERENCES workspace_mcp(id) ON DELETE CASCADE,
    PRIMARY KEY (agent_id, mcp_id)
);

CREATE TABLE agent_user_templates (
    agent_id          UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    user_template_id  UUID NOT NULL REFERENCES workspace_templates(id) ON DELETE CASCADE,
    template_type     TEXT NOT NULL CHECK (template_type IN ('user','soul','agents','heartbeat','tools')),
    PRIMARY KEY (agent_id, user_template_id),
    UNIQUE (agent_id, template_type)
);
