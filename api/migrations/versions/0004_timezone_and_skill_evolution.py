"""Add user.timezone and agents.skill_evolution

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-24
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE "user"
            ADD COLUMN timezone TEXT NOT NULL DEFAULT 'UTC';

        ALTER TABLE agents
            ADD COLUMN skill_evolution BOOLEAN NOT NULL DEFAULT FALSE;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE agents DROP COLUMN skill_evolution;
        ALTER TABLE "user" DROP COLUMN timezone;
    """)
