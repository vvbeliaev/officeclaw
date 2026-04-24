"""Promote SKILL.md frontmatter fields to first-class columns on `skills`.

`skills.{always,emoji,homepage,required_bins,required_envs}` hold the
well-known fields consumed by nanobot's SkillsLoader. `metadata_extra`
preserves any unknown keys (e.g. publisher-specific metadata) so that
round-trip through DB is lossless. SKILL.md body is stored in
`skill_files` without a frontmatter block; the block is synthesized when
assembling the sandbox workspace payload.

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-24
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE skills
            ADD COLUMN always          BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN emoji           TEXT,
            ADD COLUMN homepage        TEXT,
            ADD COLUMN required_bins   TEXT[] NOT NULL DEFAULT '{}',
            ADD COLUMN required_envs   TEXT[] NOT NULL DEFAULT '{}',
            ADD COLUMN metadata_extra  JSONB  NOT NULL DEFAULT '{}'::jsonb;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE skills
            DROP COLUMN metadata_extra,
            DROP COLUMN required_envs,
            DROP COLUMN required_bins,
            DROP COLUMN homepage,
            DROP COLUMN emoji,
            DROP COLUMN always;
    """)
