-- Persona support schema update
-- Run in Supabase SQL editor or psql.

ALTER TABLE IF EXISTS scripts
ADD COLUMN IF NOT EXISTS persona VARCHAR(32) NOT NULL DEFAULT 'arthur',
ADD COLUMN IF NOT EXISTS voice_id VARCHAR(128),
ADD COLUMN IF NOT EXISTS avatar_id VARCHAR(128);

ALTER TABLE IF EXISTS videos
ADD COLUMN IF NOT EXISTS persona VARCHAR(32) NOT NULL DEFAULT 'arthur',
ADD COLUMN IF NOT EXISTS voice_id VARCHAR(128),
ADD COLUMN IF NOT EXISTS avatar_id VARCHAR(128);

CREATE INDEX IF NOT EXISTS idx_scripts_persona ON scripts(persona);
CREATE INDEX IF NOT EXISTS idx_videos_persona ON videos(persona);
