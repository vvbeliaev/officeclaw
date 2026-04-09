-- api/migrations/versions/002_add_officeclaw_token.sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS officeclaw_token TEXT UNIQUE;
