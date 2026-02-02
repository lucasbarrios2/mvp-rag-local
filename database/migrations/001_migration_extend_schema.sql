-- ============================================================================
-- MIGRAÇÃO: Adiciona campos de análise multimodal ao schema existente
-- ============================================================================
--
-- IMPORTANTE: Esta migração PRESERVA seus dados existentes!
-- Apenas adiciona novas colunas para o sistema de RAG.
--
-- Dados existentes assumidos:
--   - id (PK)
--   - descricao_breve (texto)
--   - local (caminho do arquivo)
--   - id_origem (identificador externo)
--   - categorias (array ou texto)
--   - tags (array ou texto)
--   - autor
--
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. VERIFICAR/CRIAR TABELA BASE
-- ============================================================================

-- Se a tabela ainda não existe, criar versão básica
-- (se já existe, este bloco é ignorado)

CREATE TABLE IF NOT EXISTS video_clips (
    id SERIAL PRIMARY KEY,
    id_origem VARCHAR(255) UNIQUE,
    descricao_breve TEXT,
    local TEXT NOT NULL,
    categorias TEXT[],
    tags TEXT[],
    autor VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- 2. ADICIONAR CAMPOS DE METADATA BÁSICA (se não existirem)
-- ============================================================================

-- Duração do vídeo
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='video_clips' AND column_name='duration_seconds'
    ) THEN
        ALTER TABLE video_clips ADD COLUMN duration_seconds FLOAT;
    END IF;
END $$;

-- Hash do arquivo (para detectar duplicatas)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='video_clips' AND column_name='file_hash'
    ) THEN
        ALTER TABLE video_clips ADD COLUMN file_hash VARCHAR(64);
    END IF;
END $$;

-- Status de processamento
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='video_clips' AND column_name='processing_status'
    ) THEN
        ALTER TABLE video_clips ADD COLUMN processing_status VARCHAR(50) DEFAULT 'pending';
        COMMENT ON COLUMN video_clips.processing_status IS 'pending, analyzing, analyzed, failed';
    END IF;
END $$;

-- Data da última análise
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='video_clips' AND column_name='last_analyzed_at'
    ) THEN
        ALTER TABLE video_clips ADD COLUMN last_analyzed_at TIMESTAMP;
    END IF;
END $$;

-- ============================================================================
-- 3. ADICIONAR CAMPOS DE ANÁLISE VISUAL (Claude)
-- ============================================================================

-- Descrição rica gerada por LLM
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='video_clips' AND column_name='scene_description'
    ) THEN
        ALTER TABLE video_clips ADD COLUMN scene_description TEXT;
        COMMENT ON COLUMN video_clips.scene_description IS 'Descrição detalhada gerada por Claude';
    END IF;
END $$;

-- Elementos visuais detectados
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='video_clips' AND column_name='visual_elements'
    ) THEN
        ALTER TABLE video_clips ADD COLUMN visual_elements JSONB;
        COMMENT ON COLUMN video_clips.visual_elements IS '["rampa", "skate", "pessoa"]';
    END IF;
END $$;

-- Momentos-chave no vídeo
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='video_clips' AND column_name='key_moments'
    ) THEN
        ALTER TABLE video_clips ADD COLUMN key_moments JSONB;
        COMMENT ON COLUMN video_clips.key_moments IS '[{"timestamp": 2.1, "event": "queda"}]';
    END IF;
END $$;

-- ============================================================================
-- 4. ADICIONAR CAMPOS DE ANÁLISE EMOCIONAL
-- ============================================================================

-- Tom emocional
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='video_clips' AND column_name='emotional_tone'
    ) THEN
        ALTER TABLE video_clips ADD COLUMN emotional_tone VARCHAR(50);
        COMMENT ON COLUMN video_clips.emotional_tone IS 'cômico, épico, wholesome, tenso, absurdo';
    END IF;
END $$;

-- Intensidade (0-10)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='video_clips' AND column_name='intensity'
    ) THEN
        ALTER TABLE video_clips ADD COLUMN intensity FLOAT CHECK (intensity BETWEEN 0 AND 10);
        COMMENT ON COLUMN video_clips.intensity IS 'Quão intensa/energética é a cena (0-10)';
    END IF;
END $$;

-- Fator surpresa (0-10)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='video_clips' AND column_name='surprise_factor'
    ) THEN
        ALTER TABLE video_clips ADD COLUMN surprise_factor FLOAT CHECK (surprise_factor BETWEEN 0 AND 10);
        COMMENT ON COLUMN video_clips.surprise_factor IS 'Elemento de surpresa/inesperado (0-10)';
    END IF;
END $$;

-- Potencial viral (0-10)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='video_clips' AND column_name='viral_potential'
    ) THEN
        ALTER TABLE video_clips ADD COLUMN viral_potential FLOAT CHECK (viral_potential BETWEEN 0 AND 10);
        COMMENT ON COLUMN video_clips.viral_potential IS 'Potencial de viralização (0-10)';
    END IF;
END $$;

-- ============================================================================
-- 5. ADICIONAR CAMPOS DE ANÁLISE NARRATIVA
-- ============================================================================

-- Arco narrativo
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='video_clips' AND column_name='narrative_arc'
    ) THEN
        ALTER TABLE video_clips ADD COLUMN narrative_arc TEXT;
        COMMENT ON COLUMN video_clips.narrative_arc IS 'Ex: setup -> escalation -> payoff';
    END IF;
END $$;

-- Funciona sozinho?
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='video_clips' AND column_name='standalone'
    ) THEN
        ALTER TABLE video_clips ADD COLUMN standalone BOOLEAN;
        COMMENT ON COLUMN video_clips.standalone IS 'Clip faz sentido sem contexto adicional?';
    END IF;
END $$;

-- ============================================================================
-- 6. ADICIONAR CAMPOS DE SCORES TEMÁTICOS
-- ============================================================================

-- Scores para temas comuns (0-10)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='video_clips' AND column_name='theme_scores'
    ) THEN
        ALTER TABLE video_clips ADD COLUMN theme_scores JSONB;
        COMMENT ON COLUMN video_clips.theme_scores IS '{"fails": 9.0, "sports": 7.5, "comedy": 8.0}';
    END IF;
END $$;

-- ============================================================================
-- 7. ADICIONAR CAMPOS DE EMBEDDINGS
-- ============================================================================

-- ID no Qdrant
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='video_clips' AND column_name='embedding_id'
    ) THEN
        ALTER TABLE video_clips ADD COLUMN embedding_id VARCHAR(255);
        COMMENT ON COLUMN video_clips.embedding_id IS 'ID do vetor no Qdrant';
    END IF;
END $$;

-- Caminho dos frames cacheados
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='video_clips' AND column_name='frames_cache_path'
    ) THEN
        ALTER TABLE video_clips ADD COLUMN frames_cache_path TEXT;
        COMMENT ON COLUMN video_clips.frames_cache_path IS 'Caminho para frames extraídos';
    END IF;
END $$;

-- ============================================================================
-- 8. ADICIONAR CAMPOS DE PERFORMANCE/MÉTRICAS
-- ============================================================================

-- Vezes que o clip foi usado em produções
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='video_clips' AND column_name='times_used'
    ) THEN
        ALTER TABLE video_clips ADD COLUMN times_used INTEGER DEFAULT 0;
    END IF;
END $$;

-- Última vez usado
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='video_clips' AND column_name='last_used_at'
    ) THEN
        ALTER TABLE video_clips ADD COLUMN last_used_at TIMESTAMP;
    END IF;
END $$;

-- Taxa de retenção média quando usado
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='video_clips' AND column_name='avg_retention_rate'
    ) THEN
        ALTER TABLE video_clips ADD COLUMN avg_retention_rate FLOAT;
        COMMENT ON COLUMN video_clips.avg_retention_rate IS 'Performance média em vídeos publicados';
    END IF;
END $$;

-- ============================================================================
-- 9. CRIAR ÍNDICES PARA PERFORMANCE
-- ============================================================================

-- Status de processamento (para filtrar clips pendentes)
CREATE INDEX IF NOT EXISTS idx_processing_status
ON video_clips(processing_status);

-- Análise emocional (buscas frequentes)
CREATE INDEX IF NOT EXISTS idx_emotional_tone
ON video_clips(emotional_tone);

CREATE INDEX IF NOT EXISTS idx_intensity
ON video_clips(intensity)
WHERE intensity IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_viral_potential
ON video_clips(viral_potential)
WHERE viral_potential IS NOT NULL;

-- Standalone (clips que funcionam sozinhos)
CREATE INDEX IF NOT EXISTS idx_standalone
ON video_clips(standalone)
WHERE standalone = TRUE;

-- Categorias e tags (se existirem como arrays)
CREATE INDEX IF NOT EXISTS idx_categorias_gin
ON video_clips USING GIN(categorias);

CREATE INDEX IF NOT EXISTS idx_tags_gin
ON video_clips USING GIN(tags);

-- JSONB fields (para buscas eficientes)
CREATE INDEX IF NOT EXISTS idx_visual_elements_gin
ON video_clips USING GIN(visual_elements);

CREATE INDEX IF NOT EXISTS idx_theme_scores_gin
ON video_clips USING GIN(theme_scores);

-- Embedding ID (join com Qdrant)
CREATE INDEX IF NOT EXISTS idx_embedding_id
ON video_clips(embedding_id)
WHERE embedding_id IS NOT NULL;

-- Performance (ordenar por uso)
CREATE INDEX IF NOT EXISTS idx_times_used
ON video_clips(times_used);

CREATE INDEX IF NOT EXISTS idx_last_used_at
ON video_clips(last_used_at DESC NULLS LAST);

-- ============================================================================
-- 10. CRIAR VIEWS ÚTEIS
-- ============================================================================

-- Clips prontos para uso (analisados e de qualidade)
CREATE OR REPLACE VIEW clips_ready AS
SELECT
    id,
    id_origem,
    descricao_breve,
    scene_description,
    emotional_tone,
    intensity,
    viral_potential,
    categorias,
    tags
FROM video_clips
WHERE processing_status = 'analyzed'
  AND intensity >= 5.0
  AND standalone = TRUE
ORDER BY viral_potential DESC NULLS LAST;

-- Clips pendentes de análise
CREATE OR REPLACE VIEW clips_pending AS
SELECT
    id,
    id_origem,
    local,
    descricao_breve,
    created_at
FROM video_clips
WHERE processing_status = 'pending'
ORDER BY created_at ASC;

-- Estatísticas gerais
CREATE OR REPLACE VIEW stats_overview AS
SELECT
    COUNT(*) as total_clips,
    COUNT(*) FILTER (WHERE processing_status = 'analyzed') as analyzed,
    COUNT(*) FILTER (WHERE processing_status = 'pending') as pending,
    COUNT(*) FILTER (WHERE processing_status = 'failed') as failed,
    ROUND(AVG(intensity), 2) as avg_intensity,
    ROUND(AVG(viral_potential), 2) as avg_viral_potential
FROM video_clips;

-- ============================================================================
-- 11. CRIAR TRIGGER PARA UPDATED_AT
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_clips_updated_at ON video_clips;

CREATE TRIGGER update_clips_updated_at
    BEFORE UPDATE ON video_clips
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 12. COMENTÁRIOS NA TABELA
-- ============================================================================

COMMENT ON TABLE video_clips IS 'Clips de vídeo com dados originais + análise multimodal';

COMMIT;

-- ============================================================================
-- VALIDAÇÃO
-- ============================================================================

-- Exibir estrutura da tabela
\d video_clips

-- Contar clips
SELECT
    'Total de clips: ' || COUNT(*) as info
FROM video_clips
UNION ALL
SELECT
    'Clips analisados: ' || COUNT(*)
FROM video_clips
WHERE processing_status = 'analyzed'
UNION ALL
SELECT
    'Clips pendentes: ' || COUNT(*)
FROM video_clips
WHERE processing_status = 'pending';

-- Sucesso!
SELECT '✅ Migração concluída com sucesso!' as status;
