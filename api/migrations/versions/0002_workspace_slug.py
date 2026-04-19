"""Add slug column to workspaces

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-19
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE workspaces ADD COLUMN slug TEXT;

        UPDATE workspaces
        SET slug = CASE
            WHEN TRIM(BOTH '-' FROM LOWER(REGEXP_REPLACE(name, '[^a-zA-Z0-9]+', '-', 'g'))) = ''
            THEN SUBSTRING(id::text, 1, 8)
            ELSE TRIM(BOTH '-' FROM LOWER(REGEXP_REPLACE(name, '[^a-zA-Z0-9]+', '-', 'g')))
                 || '-' || SUBSTRING(id::text, 1, 6)
        END
        WHERE slug IS NULL;

        ALTER TABLE workspaces ALTER COLUMN slug SET NOT NULL;
        CREATE UNIQUE INDEX workspaces_slug_idx ON workspaces(slug);
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS workspaces_slug_idx;
        ALTER TABLE workspaces DROP COLUMN IF EXISTS slug;
    """)
