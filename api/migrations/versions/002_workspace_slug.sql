-- ============================================================
-- 002: Add slug column to workspaces
-- ============================================================

ALTER TABLE workspaces ADD COLUMN slug TEXT;

-- Backfill existing rows: lowercase alphanumeric slug from name + first 6 chars of UUID
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
