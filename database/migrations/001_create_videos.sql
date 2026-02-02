-- ============================================================================
-- Schema: Tabela videos - MVP RAG Local
-- Executado automaticamente pelo Docker na inicializacao
-- ============================================================================

CREATE TABLE IF NOT EXISTS videos (
    id SERIAL PRIMARY KEY,

    -- Arquivo
    filename VARCHAR(500) NOT NULL,
    file_path TEXT NOT NULL,
    file_size_bytes BIGINT,
    duration_seconds FLOAT,
    mime_type VARCHAR(100),

    -- Status de processamento
    processing_status VARCHAR(50) DEFAULT 'pending'
        CHECK (processing_status IN ('pending', 'analyzing', 'analyzed', 'failed')),
    error_message TEXT,

    -- Analise Gemini
    analysis_description TEXT,
    tags JSONB DEFAULT '[]',
    emotional_tone VARCHAR(100),
    intensity FLOAT CHECK (intensity >= 0 AND intensity <= 10),
    viral_potential FLOAT CHECK (viral_potential >= 0 AND viral_potential <= 10),
    key_moments JSONB DEFAULT '[]',
    themes JSONB DEFAULT '{}',

    -- Embedding
    embedding_id VARCHAR(255),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    analyzed_at TIMESTAMP
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(processing_status);
CREATE INDEX IF NOT EXISTS idx_videos_emotional_tone ON videos(emotional_tone);
CREATE INDEX IF NOT EXISTS idx_videos_tags_gin ON videos USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_videos_themes_gin ON videos USING GIN(themes);

-- Trigger auto-update updated_at
CREATE OR REPLACE FUNCTION update_videos_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_videos_updated_at ON videos;
CREATE TRIGGER trg_videos_updated_at
    BEFORE UPDATE ON videos
    FOR EACH ROW EXECUTE FUNCTION update_videos_updated_at();
