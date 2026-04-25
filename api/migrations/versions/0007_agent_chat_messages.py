"""Add agent_chat_messages — UI chat history per agent.

One agent = one chat (matches nanobot's per-session model). Each row holds
a Vercel AI SDK ``UIMessage`` snapshot: ``parts`` is the typed payload
(text / tool-X / reasoning) the client renders. Persisted by SvelteKit
``onFinish`` after each turn; nanobot's JSONL session file stays the
authoritative working memory for the LLM.

``status`` lets a sweeper job mark stale ``pending`` rows as ``failed``
when a turn drops mid-stream.

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-25
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE agent_chat_messages (
            id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_id        UUID        NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
            message_id      TEXT        NOT NULL,
            role            TEXT        NOT NULL
                CHECK (role IN ('user', 'assistant', 'system')),
            parts           JSONB       NOT NULL,
            metadata        JSONB,
            status          TEXT        NOT NULL DEFAULT 'complete'
                CHECK (status IN ('pending', 'complete', 'failed')),
            model           TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (agent_id, message_id)
        );

        CREATE INDEX agent_chat_messages_agent_id_created_at_idx
            ON agent_chat_messages (agent_id, created_at);

        CREATE INDEX agent_chat_messages_pending_idx
            ON agent_chat_messages (agent_id)
            WHERE status = 'pending';
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS agent_chat_messages_pending_idx;
        DROP INDEX IF EXISTS agent_chat_messages_agent_id_created_at_idx;
        DROP TABLE IF EXISTS agent_chat_messages;
    """)
