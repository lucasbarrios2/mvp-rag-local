-- ============================================================================
-- Schema: Tabela processing_queue - Fila de processamento de videos
-- MVP RAG Local
-- ============================================================================

CREATE TABLE IF NOT EXISTS processing_queue (
    id SERIAL PRIMARY KEY,

    -- Referencia ao video
    video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,

    -- Status e prioridade
    status VARCHAR(20) DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    priority INTEGER DEFAULT 0,

    -- Controle de tentativas
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    error_message TEXT,

    -- Lock para processamento concorrente
    locked_at TIMESTAMP,
    locked_by VARCHAR(100),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,

    -- Constraint para garantir um item por video
    UNIQUE(video_id)
);

-- Indices para performance
CREATE INDEX IF NOT EXISTS idx_queue_status_priority_created
    ON processing_queue(status, priority DESC, created_at ASC)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_queue_locked_at
    ON processing_queue(locked_at)
    WHERE locked_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_queue_video_id
    ON processing_queue(video_id);

-- Trigger auto-update updated_at
CREATE OR REPLACE FUNCTION update_queue_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_queue_updated_at ON processing_queue;
CREATE TRIGGER trg_queue_updated_at
    BEFORE UPDATE ON processing_queue
    FOR EACH ROW EXECUTE FUNCTION update_queue_updated_at();
