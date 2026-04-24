"""Add heartbeat toggle on agents and workspace/agent cron catalog

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-24
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE agents
            ADD COLUMN heartbeat_enabled     BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN heartbeat_interval_s  INTEGER NOT NULL DEFAULT 1800;

        CREATE TABLE workspace_crons (
            id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id       UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            name               TEXT        NOT NULL,
            schedule_kind      TEXT        NOT NULL CHECK (schedule_kind IN ('at','every','cron')),
            schedule_at_ms     BIGINT,
            schedule_every_ms  BIGINT,
            schedule_expr      TEXT,
            schedule_tz        TEXT,
            message            TEXT        NOT NULL DEFAULT '',
            deliver            BOOLEAN     NOT NULL DEFAULT FALSE,
            channel            TEXT,
            recipient          TEXT,
            delete_after_run   BOOLEAN     NOT NULL DEFAULT FALSE,
            created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(workspace_id, name)
        );

        CREATE INDEX workspace_crons_workspace_id_idx ON workspace_crons(workspace_id);

        CREATE TABLE agent_crons (
            agent_id            UUID     NOT NULL REFERENCES agents(id)           ON DELETE CASCADE,
            cron_id             UUID     NOT NULL REFERENCES workspace_crons(id)  ON DELETE CASCADE,
            enabled             BOOLEAN  NOT NULL DEFAULT TRUE,
            next_run_at_ms      BIGINT,
            last_run_at_ms      BIGINT,
            last_status         TEXT    CHECK (last_status IN ('ok','error','skipped')),
            last_error          TEXT,
            run_history         JSONB   NOT NULL DEFAULT '[]'::jsonb,
            PRIMARY KEY (agent_id, cron_id)
        );

        CREATE INDEX agent_crons_agent_id_idx ON agent_crons(agent_id);
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS agent_crons;
        DROP TABLE IF EXISTS workspace_crons;
        ALTER TABLE agents
            DROP COLUMN IF EXISTS heartbeat_interval_s,
            DROP COLUMN IF EXISTS heartbeat_enabled;
    """)
