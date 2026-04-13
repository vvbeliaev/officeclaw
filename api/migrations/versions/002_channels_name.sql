ALTER TABLE user_channels ADD COLUMN name TEXT NOT NULL DEFAULT '';
UPDATE user_channels SET name = type WHERE name = '';
ALTER TABLE user_channels ALTER COLUMN name DROP DEFAULT;
