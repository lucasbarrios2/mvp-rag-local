-- Migration 004: Add source metadata, audio context, and unified embedding
-- Purpose: Enable MENTOR integration with Newsflare metadata + unified embedding strategy

-- Source metadata (Newsflare, via MENTOR)
ALTER TABLE videos ADD COLUMN IF NOT EXISTS newsflare_id VARCHAR(255) UNIQUE;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS event_date TIMESTAMP;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS filming_location TEXT;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS uploader VARCHAR(500);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS category VARCHAR(200);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS is_exclusive BOOLEAN DEFAULT FALSE;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS license_type VARCHAR(100);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS source_description TEXT;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS source_tags JSONB DEFAULT '[]';
ALTER TABLE videos ADD COLUMN IF NOT EXISTS newsflare_metadata JSONB DEFAULT '{}';

-- Audio context
ALTER TABLE videos ADD COLUMN IF NOT EXISTS audio_transcript TEXT;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS audio_language VARCHAR(50);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS has_speech BOOLEAN;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS audio_description TEXT;

-- Tracking
ALTER TABLE videos ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'local';

-- Unified embedding
ALTER TABLE videos ADD COLUMN IF NOT EXISTS unified_embedding_id VARCHAR(255);

-- Indices
CREATE INDEX IF NOT EXISTS idx_videos_newsflare_id ON videos(newsflare_id);
CREATE INDEX IF NOT EXISTS idx_videos_category ON videos(category);
CREATE INDEX IF NOT EXISTS idx_videos_event_date ON videos(event_date);
CREATE INDEX IF NOT EXISTS idx_videos_source ON videos(source);
