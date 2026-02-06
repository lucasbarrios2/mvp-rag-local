-- Migration 005: Add compilation analysis fields
-- Purpose: Support editorial analysis for video compilations (Refugio Mental style)

-- Compilation analysis fields
ALTER TABLE videos ADD COLUMN IF NOT EXISTS event_headline TEXT;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS trim_in_ms INTEGER;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS trim_out_ms INTEGER;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS money_shot_ms INTEGER;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS camera_type VARCHAR(50);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS audio_usability VARCHAR(20);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS audio_usability_reason TEXT;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS compilation_themes JSONB DEFAULT '[]';
ALTER TABLE videos ADD COLUMN IF NOT EXISTS narration_suggestion TEXT;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS location_country VARCHAR(200);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS location_environment VARCHAR(50);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS standalone_score FLOAT;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS visual_quality_score FLOAT;

-- Indices
CREATE INDEX IF NOT EXISTS idx_videos_camera_type ON videos(camera_type);
CREATE INDEX IF NOT EXISTS idx_videos_standalone_score ON videos(standalone_score);
CREATE INDEX IF NOT EXISTS idx_videos_visual_quality_score ON videos(visual_quality_score);
CREATE INDEX IF NOT EXISTS idx_videos_location_environment ON videos(location_environment);
CREATE INDEX IF NOT EXISTS idx_videos_compilation_themes ON videos USING GIN (compilation_themes);
