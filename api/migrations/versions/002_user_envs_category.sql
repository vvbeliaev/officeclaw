-- ============================================================
-- Add category column to user_envs
-- Possible values: NULL (generic), 'system', 'llm-provider'
-- ============================================================

ALTER TABLE user_envs ADD COLUMN IF NOT EXISTS category TEXT;
