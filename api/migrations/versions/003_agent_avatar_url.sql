-- ============================================================
-- Add avatar_url column to agents
-- Optional URL for a custom avatar image.
-- ============================================================

ALTER TABLE agents ADD COLUMN IF NOT EXISTS avatar_url TEXT;
