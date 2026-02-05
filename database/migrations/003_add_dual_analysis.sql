-- ============================================================================
-- Migration: Adiciona campos para analise DUAL (visual + narrativa)
-- MVP RAG Local
-- ============================================================================

-- Analise VISUAL (frame a frame)
ALTER TABLE videos ADD COLUMN IF NOT EXISTS visual_description TEXT;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS visual_tags JSONB DEFAULT '[]';
ALTER TABLE videos ADD COLUMN IF NOT EXISTS objects_detected JSONB DEFAULT '[]';
ALTER TABLE videos ADD COLUMN IF NOT EXISTS scenes JSONB DEFAULT '[]';
ALTER TABLE videos ADD COLUMN IF NOT EXISTS visual_style VARCHAR(100);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS color_palette JSONB DEFAULT '[]';
ALTER TABLE videos ADD COLUMN IF NOT EXISTS movement_intensity FLOAT;

-- Analise NARRATIVA (contexto e significado)
ALTER TABLE videos ADD COLUMN IF NOT EXISTS narrative_description TEXT;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS narrative_tags JSONB DEFAULT '[]';
ALTER TABLE videos ADD COLUMN IF NOT EXISTS storytelling_elements JSONB DEFAULT '{}';
ALTER TABLE videos ADD COLUMN IF NOT EXISTS target_audience TEXT;

-- Embeddings duplos
ALTER TABLE videos ADD COLUMN IF NOT EXISTS visual_embedding_id VARCHAR(255);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS narrative_embedding_id VARCHAR(255);

-- Indices para busca
CREATE INDEX IF NOT EXISTS idx_videos_visual_tags_gin ON videos USING GIN(visual_tags);
CREATE INDEX IF NOT EXISTS idx_videos_narrative_tags_gin ON videos USING GIN(narrative_tags);
CREATE INDEX IF NOT EXISTS idx_videos_objects_detected_gin ON videos USING GIN(objects_detected);
