"""Enforce NOT NULL on workspaces.officeclaw_token

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-24
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE workspaces
        SET officeclaw_token = encode(gen_random_bytes(32), 'hex')
        WHERE officeclaw_token IS NULL;

        ALTER TABLE workspaces ALTER COLUMN officeclaw_token SET NOT NULL;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE workspaces ALTER COLUMN officeclaw_token DROP NOT NULL;")
