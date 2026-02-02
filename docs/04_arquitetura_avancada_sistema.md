# Arquitetura Avançada: Sistema de Produção de Vídeos com IA Multimodal
**Janeiro 2026 - Design de Sistema Escalável**

## 🏗️ Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CAMADA DE APLICAÇÃO                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Web UI     │  │  REST API    │  │  CLI Tool    │              │
│  │  (FastAPI)   │  │  (FastAPI)   │  │  (Typer)     │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      CAMADA DE ORQUESTRAÇÃO                          │
│                         (LangGraph Agent)                            │
│                                                                       │
│  Coordenador → Curador → Editor → QA → Metadados → Renderizador    │
│                   ↑________________________↓ (loop se QA falhar)     │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      CAMADA DE SERVIÇOS DE AI                        │
│                                                                       │
│  ┌───────────────────┐  ┌───────────────────┐  ┌─────────────────┐ │
│  │ LLM Multimodal    │  │ Embedding Service │  │  Audio Analysis │ │
│  │ Claude/GPT-4o     │  │ CLIP/ImageBind    │  │  Whisper        │ │
│  └───────────────────┘  └───────────────────┘  └─────────────────┘ │
│                                                                       │
│  ┌───────────────────┐  ┌───────────────────┐  ┌─────────────────┐ │
│  │ Scene Detection   │  │ Object Detection  │  │  Action Recog   │ │
│  │ PySceneDetect     │  │ YOLO/Detectron    │  │  VideoMAE       │ │
│  └───────────────────┘  └───────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      CAMADA DE DADOS                                 │
│                                                                       │
│  ┌───────────────────┐  ┌───────────────────┐  ┌─────────────────┐ │
│  │ Vector Database   │  │ Relational DB     │  │  Cache          │ │
│  │ Qdrant            │  │ PostgreSQL        │  │  Redis          │ │
│  └───────────────────┘  └───────────────────┘  └─────────────────┘ │
│                                                                       │
│  ┌───────────────────┐  ┌───────────────────┐                       │
│  │ Object Storage    │  │ Message Queue     │                       │
│  │ MinIO/S3          │  │ Celery/RQ         │                       │
│  └───────────────────┘  └───────────────────┘                       │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      CAMADA DE INFRAESTRUTURA                        │
│                                                                       │
│  ┌───────────────────┐  ┌───────────────────┐  ┌─────────────────┐ │
│  │ Video Storage     │  │ GPU Cluster       │  │  Monitoring     │ │
│  │ (NAS/Cloud)       │  │ (NVIDIA T4/A100)  │  │  Prometheus     │ │
│  └───────────────────┘  └───────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Schema de Banco de Dados Completo

### PostgreSQL - Dados Relacionais

```sql
-- ============================================================================
-- TABELA PRINCIPAL DE CLIPS
-- ============================================================================

CREATE TABLE video_clips (
    -- Identificação
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(255) UNIQUE,  -- ID legível (ex: clip_0001)
    file_path TEXT NOT NULL,
    file_hash VARCHAR(64) UNIQUE,  -- SHA-256 do arquivo

    -- Metadata básica
    duration_seconds FLOAT NOT NULL,
    resolution_width INTEGER,
    resolution_height INTEGER,
    fps FLOAT,
    file_size_bytes BIGINT,
    codec VARCHAR(50),

    -- Datas
    created_at TIMESTAMP DEFAULT NOW(),
    uploaded_at TIMESTAMP DEFAULT NOW(),
    last_analyzed_at TIMESTAMP,

    -- Status
    status VARCHAR(50) DEFAULT 'pending',  -- pending, analyzed, failed
    rights_cleared BOOLEAN DEFAULT FALSE,
    source VARCHAR(255),  -- user_upload, purchased, licensed

    -- ========================================================================
    -- ANÁLISE VISUAL (gerada por LLM Multimodal)
    -- ========================================================================

    scene_description TEXT,
    visual_elements JSONB,  -- ["rampa", "skate", "pessoa", "céu"]

    key_moments JSONB,
    -- [
    --   {"timestamp": 0.0, "relative": 0.0, "event": "setup"},
    --   {"timestamp": 2.1, "relative": 0.5, "event": "action"},
    --   {"timestamp": 4.2, "relative": 1.0, "event": "payoff"}
    -- ]

    -- ========================================================================
    -- ANÁLISE EMOCIONAL
    -- ========================================================================

    emotional_tone VARCHAR(50),  -- cômico, épico, wholesome, etc
    intensity FLOAT CHECK (intensity BETWEEN 0 AND 10),
    surprise_factor FLOAT CHECK (surprise_factor BETWEEN 0 AND 10),
    viral_potential FLOAT CHECK (viral_potential BETWEEN 0 AND 10),
    impact_score FLOAT CHECK (impact_score BETWEEN 0 AND 10),

    -- ========================================================================
    -- ANÁLISE NARRATIVA
    -- ========================================================================

    narrative_arc TEXT,  -- "setup -> escalation -> payoff"
    standalone BOOLEAN,  -- Funciona sem contexto?
    pacing VARCHAR(50),  -- slow, medium, fast, frenetic

    -- ========================================================================
    -- ANÁLISE DE ÁUDIO
    -- ========================================================================

    audio_transcript TEXT,
    sound_events TEXT[],  -- {grito, risada, impacto, música}
    has_speech BOOLEAN,
    has_background_music BOOLEAN,
    dominant_frequency_hz FLOAT,

    -- ========================================================================
    -- ANÁLISE DE OBJETOS E AÇÕES
    -- ========================================================================

    detected_objects JSONB,
    -- [
    --   {"object": "person", "confidence": 0.98, "bbox": [x, y, w, h]},
    --   {"object": "skateboard", "confidence": 0.95, "bbox": [...]}
    -- ]

    detected_actions JSONB,
    -- [
    --   {"action": "skateboarding", "confidence": 0.92, "timespan": [0, 5]},
    --   {"action": "falling", "confidence": 0.88, "timespan": [3, 5]}
    -- ]

    -- ========================================================================
    -- ADEQUAÇÃO PARA TEMAS (scores 0-10)
    -- ========================================================================

    theme_fails_accidents FLOAT,
    theme_extreme_sports FLOAT,
    theme_comedy FLOAT,
    theme_wholesome FLOAT,
    theme_instant_regret FLOAT,
    theme_tutorial_fail FLOAT,
    theme_animal_antics FLOAT,
    theme_epic_wins FLOAT,
    theme_custom JSONB,  -- Temas customizados dinâmicos

    -- ========================================================================
    -- MÉTRICAS DE PERFORMANCE
    -- ========================================================================

    times_used INTEGER DEFAULT 0,
    times_shown INTEGER DEFAULT 0,  -- Em thumbnails, previews
    avg_watch_time_seconds FLOAT,
    avg_retention_rate FLOAT,  -- % que assiste até o fim quando aparece
    click_through_rate FLOAT,  -- CTR quando usado em thumbnail

    last_used_at TIMESTAMP,
    avg_user_rating FLOAT,  -- Se houver sistema de feedback

    -- ========================================================================
    -- EMBEDDINGS E REFERÊNCIAS
    -- ========================================================================

    embedding_id VARCHAR(255),  -- ID no Qdrant
    thumbnail_path TEXT,  -- Frame extraído para preview
    frames_cache_path TEXT,  -- Caminho para frames no cache

    -- ========================================================================
    -- METADATA ADICIONAL
    -- ========================================================================

    custom_metadata JSONB,  -- Campos customizáveis
    notes TEXT,

    -- Índices automáticos
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- TAGS SEMÂNTICAS (muitos-para-muitos)
-- ============================================================================

CREATE TABLE semantic_tags (
    id SERIAL PRIMARY KEY,
    clip_id UUID REFERENCES video_clips(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    confidence FLOAT CHECK (confidence BETWEEN 0 AND 1),
    source VARCHAR(50),  -- llm_analysis, manual, user_feedback

    UNIQUE(clip_id, tag)
);

-- ============================================================================
-- HISTÓRICO DE PRODUÇÕES
-- ============================================================================

CREATE TABLE video_productions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    production_id VARCHAR(255) UNIQUE,

    -- Input do usuário
    theme TEXT NOT NULL,
    target_duration INTEGER,
    style VARCHAR(50),  -- energetic, chill, emotional

    -- Status
    status VARCHAR(50) DEFAULT 'curating',
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,

    -- Resultado
    final_video_path TEXT,
    final_duration FLOAT,
    clips_count INTEGER,

    -- Metadata do vídeo
    title TEXT,
    description TEXT,
    tags TEXT[],
    thumbnail_timestamp FLOAT,

    -- Performance (pós-publicação)
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    avg_watch_time FLOAT,
    retention_rate FLOAT,

    -- Estimativas (pré-publicação)
    estimated_views INTEGER,

    -- LangGraph state
    langgraph_thread_id VARCHAR(255),
    langgraph_checkpoint_id VARCHAR(255),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- CLIPS USADOS EM PRODUÇÕES (rastreabilidade)
-- ============================================================================

CREATE TABLE production_clips (
    production_id UUID REFERENCES video_productions(id) ON DELETE CASCADE,
    clip_id UUID REFERENCES video_clips(id) ON DELETE CASCADE,

    -- Posição na timeline
    position_index INTEGER NOT NULL,  -- 0, 1, 2, ...
    start_time_in_video FLOAT,
    end_time_in_video FLOAT,

    -- Edição aplicada
    transition_before VARCHAR(50),  -- fade, cut, zoom
    audio_level FLOAT DEFAULT 1.0,
    applied_effects JSONB,

    PRIMARY KEY (production_id, clip_id)
);

-- ============================================================================
-- ÍNDICES PARA PERFORMANCE
-- ============================================================================

-- Busca por metadata
CREATE INDEX idx_clips_status ON video_clips(status);
CREATE INDEX idx_clips_emotional_tone ON video_clips(emotional_tone);
CREATE INDEX idx_clips_intensity ON video_clips(intensity);
CREATE INDEX idx_clips_viral_potential ON video_clips(viral_potential);
CREATE INDEX idx_clips_rights_cleared ON video_clips(rights_cleared);

-- Busca temporal
CREATE INDEX idx_clips_created_at ON video_clips(created_at DESC);
CREATE INDEX idx_clips_last_used_at ON video_clips(last_used_at DESC NULLS LAST);

-- Busca por performance
CREATE INDEX idx_clips_times_used ON video_clips(times_used);
CREATE INDEX idx_clips_retention_rate ON video_clips(avg_retention_rate DESC NULLS LAST);

-- JSONB (GIN para busca eficiente)
CREATE INDEX idx_clips_visual_elements ON video_clips USING gin(visual_elements);
CREATE INDEX idx_clips_key_moments ON video_clips USING gin(key_moments);
CREATE INDEX idx_clips_detected_objects ON video_clips USING gin(detected_objects);

-- Tags semânticas
CREATE INDEX idx_tags_tag ON semantic_tags(tag);
CREATE INDEX idx_tags_clip_id ON semantic_tags(clip_id);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-atualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_clips_updated_at BEFORE UPDATE ON video_clips
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_productions_updated_at BEFORE UPDATE ON video_productions
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS ÚTEIS
-- ============================================================================

-- Clips prontos para uso (analisados e com direitos)
CREATE VIEW usable_clips AS
SELECT *
FROM video_clips
WHERE status = 'analyzed'
  AND rights_cleared = TRUE
  AND intensity > 5.0;

-- Clips sub-utilizados (alta qualidade, pouco usados)
CREATE VIEW underutilized_clips AS
SELECT *
FROM video_clips
WHERE status = 'analyzed'
  AND rights_cleared = TRUE
  AND viral_potential >= 7.0
  AND times_used < 3
ORDER BY viral_potential DESC, times_used ASC;

-- Performance de produções
CREATE VIEW production_performance AS
SELECT
    p.id,
    p.production_id,
    p.theme,
    p.title,
    p.views,
    p.retention_rate,
    p.clips_count,
    COALESCE(AVG(c.viral_potential), 0) as avg_clip_viral_potential,
    COALESCE(AVG(c.intensity), 0) as avg_clip_intensity
FROM video_productions p
LEFT JOIN production_clips pc ON p.id = pc.production_id
LEFT JOIN video_clips c ON pc.clip_id = c.id
WHERE p.status = 'done'
GROUP BY p.id;
```

---

## 🔄 Pipeline de Processamento Assíncrono

### Celery Tasks (Workers)

```python
# tasks.py

from celery import Celery
from curator import IntelligentCurator

app = Celery('video_production', broker='redis://localhost:6379/0')

curator = IntelligentCurator()

@app.task(bind=True, max_retries=3)
def index_video_clip_task(self, video_path: str, clip_id: str):
    """
    Task assíncrona para indexação de clip
    Executada em background worker
    """
    try:
        clip = curator.index_video_clip(video_path, clip_id)
        return {
            "status": "success",
            "clip_id": clip.id,
            "intensity": clip.intensity
        }
    except Exception as exc:
        # Retry com backoff exponencial
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@app.task
def batch_index_clips(video_paths: list):
    """Indexa múltiplos clips em paralelo"""
    from celery import group

    job = group([
        index_video_clip_task.s(path, f"clip_{i:04d}")
        for i, path in enumerate(video_paths)
    ])

    result = job.apply_async()
    return result.id


@app.task(bind=True)
def produce_video_task(self, theme: str, target_duration: int, style: str):
    """
    Task completa de produção de vídeo
    Pode levar minutos - executa em background
    """
    from langgraph_production import create_video_production_graph

    app = create_video_production_graph()

    config = {"configurable": {"thread_id": f"prod_{self.request.id}"}}

    result = app.invoke({
        "theme": theme,
        "target_duration": target_duration,
        "style": style,
        "status": "curating"
    }, config=config)

    return {
        "video_path": result["final_video_path"],
        "title": result["title"],
        "estimated_views": result["estimated_views"]
    }
```

### Arquitetura de Workers

```
┌─────────────────────────────────────────────────────────────────┐
│                         CELERY WORKERS                           │
└─────────────────────────────────────────────────────────────────┘

[Worker Pool: Indexação]  (CPU-bound)
  - 4 workers
  - Tasks: extract_frames, analyze_clip, generate_embeddings
  - Prioridade: Normal

[Worker Pool: LLM Analysis]  (I/O-bound)
  - 8 workers
  - Tasks: llm_analyze_clip, query_expansion, reranking
  - Prioridade: Alta
  - Rate limit: 100 req/min (API limits)

[Worker Pool: Renderização]  (GPU-bound)
  - 2 workers com GPU
  - Tasks: render_video
  - Prioridade: Alta
  - Timeout: 30 min

[Worker Pool: Manutenção]  (Background)
  - 1 worker
  - Tasks: cleanup_cache, update_metrics, reindex_old_clips
  - Prioridade: Baixa
  - Agendamento: Cron
```

---

## 🚀 API REST (FastAPI)

```python
# api.py

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid

app = FastAPI(title="Video Production API")

class ProductionRequest(BaseModel):
    theme: str
    target_duration: int = 600
    style: str = "energetic"

class ProductionResponse(BaseModel):
    production_id: str
    status: str
    message: str

class ClipIndexRequest(BaseModel):
    video_url: str  # URL do clip ou path local

@app.post("/api/productions", response_model=ProductionResponse)
async def create_production(request: ProductionRequest, background_tasks: BackgroundTasks):
    """
    Inicia produção de vídeo em background
    Retorna imediatamente com ID de rastreamento
    """
    production_id = str(uuid.uuid4())

    # Disparar task assíncrona
    from tasks import produce_video_task
    task = produce_video_task.apply_async(
        args=[request.theme, request.target_duration, request.style],
        task_id=production_id
    )

    # Salvar no banco
    # db.save_production(production_id, request.theme, ...)

    return ProductionResponse(
        production_id=production_id,
        status="queued",
        message="Produção iniciada. Use /api/productions/{id} para acompanhar."
    )


@app.get("/api/productions/{production_id}")
async def get_production_status(production_id: str):
    """Consulta status de uma produção"""
    from celery.result import AsyncResult

    task = AsyncResult(production_id)

    if task.state == "PENDING":
        return {"status": "pending", "progress": 0}
    elif task.state == "STARTED":
        return {"status": "processing", "progress": 30}
    elif task.state == "SUCCESS":
        result = task.result
        return {
            "status": "completed",
            "progress": 100,
            "video_path": result["video_path"],
            "title": result["title"]
        }
    else:
        return {"status": "failed", "error": str(task.info)}


@app.post("/api/clips/index")
async def index_clip(request: ClipIndexRequest):
    """Indexa um novo clip no sistema"""
    from tasks import index_video_clip_task

    clip_id = str(uuid.uuid4())
    task = index_video_clip_task.apply_async(args=[request.video_url, clip_id])

    return {
        "clip_id": clip_id,
        "task_id": task.id,
        "status": "indexing"
    }


@app.get("/api/clips/search")
async def search_clips(query: str, limit: int = 10):
    """Busca semântica de clips"""
    from curator import IntelligentCurator

    curator = IntelligentCurator()
    query_embedding = curator.embedder.embed_text(query)

    results = curator.vector_db.search(
        query_vector=query_embedding,
        limit=limit
    )

    return {"results": results}
```

---

## 📈 Monitoramento e Observabilidade

### Métricas (Prometheus)

```python
from prometheus_client import Counter, Histogram, Gauge

# Contadores
clips_indexed_total = Counter('clips_indexed_total', 'Total de clips indexados')
productions_created_total = Counter('productions_created_total', 'Total de produções')
productions_failed_total = Counter('productions_failed_total', 'Produções falhadas')

# Histogramas (latência)
indexing_duration = Histogram('indexing_duration_seconds', 'Tempo de indexação')
production_duration = Histogram('production_duration_seconds', 'Tempo de produção')
llm_request_duration = Histogram('llm_request_duration_seconds', 'Latência LLM')

# Gauges (estado atual)
active_workers = Gauge('active_workers', 'Workers ativos')
queue_size = Gauge('queue_size', 'Tamanho da fila', ['queue_name'])
clips_in_database = Gauge('clips_in_database', 'Total clips indexados')
```

### Dashboard (Grafana)

```
┌─────────────────────────────────────────────────────────────────┐
│  VIDEO PRODUCTION SYSTEM - DASHBOARD                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📊 MÉTRICAS GERAIS                                              │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │ Clips Total   │  │  Produções    │  │  Taxa Sucesso │       │
│  │    12,543     │  │  Hoje: 47     │  │     98.2%     │       │
│  └───────────────┘  └───────────────┘  └───────────────┘       │
│                                                                  │
│  📈 PERFORMANCE                                                  │
│  - Tempo médio de indexação: 45s                                │
│  - Tempo médio de produção: 8m 32s                              │
│  - Latência LLM (p95): 2.3s                                     │
│                                                                  │
│  🔥 FILA DE PROCESSAMENTO                                        │
│  - Indexação: 12 clips aguardando                               │
│  - Produção: 3 vídeos em andamento                              │
│  - Renderização: 1 vídeo renderizando                           │
│                                                                  │
│  💰 CUSTOS (Hoje)                                                │
│  - LLM API: $12.50                                               │
│  - Compute: $8.30                                                │
│  - Storage: $2.10                                                │
│  Total: $22.90                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔐 Segurança e Compliance

### Validação de Direitos Autorais

```python
class CopyrightValidator:
    """Valida direitos autorais de clips"""

    def validate_clip(self, clip_path: str) -> dict:
        """
        Valida se clip pode ser usado

        Checks:
        1. Metadata EXIF (fonte, licença)
        2. Watermarks (detecção visual)
        3. Audio fingerprinting (música com copyright)
        4. Face recognition (consentimento)
        """
        results = {
            "approved": False,
            "issues": [],
            "confidence": 0.0
        }

        # 1. Verificar metadata
        metadata = self.extract_metadata(clip_path)
        if not metadata.get("license") in ["CC0", "CC-BY", "proprietary-cleared"]:
            results["issues"].append("Licença não clara")

        # 2. Detectar watermarks
        if self.has_watermark(clip_path):
            results["issues"].append("Watermark detectado")

        # 3. Audio fingerprinting
        if self.has_copyrighted_music(clip_path):
            results["issues"].append("Música com copyright")

        # Decisão final
        results["approved"] = len(results["issues"]) == 0
        results["confidence"] = 1.0 - (len(results["issues"]) * 0.25)

        return results
```

---

## 💡 Features Avançadas

### 1. Feedback Loop Automático

```python
def update_clip_performance(clip_id: str, production_id: str, metrics: dict):
    """
    Atualiza métricas de performance do clip baseado em resultado real

    Melhora recomendações futuras via reinforcement learning
    """
    # Obter métricas do vídeo publicado
    retention_rate = metrics["retention_rate"]
    watch_time = metrics["avg_watch_time"]

    # Atualizar no banco
    db.execute("""
        UPDATE video_clips
        SET times_used = times_used + 1,
            avg_retention_rate = (
                COALESCE(avg_retention_rate, 0) * times_used + :new_retention
            ) / (times_used + 1),
            last_used_at = NOW()
        WHERE id = :clip_id
    """, {"clip_id": clip_id, "new_retention": retention_rate})

    # Se performance foi ruim, diminuir viral_potential
    if retention_rate < 0.5:
        db.execute("""
            UPDATE video_clips
            SET viral_potential = viral_potential * 0.9
            WHERE id = :clip_id
        """, {"clip_id": clip_id})
```

### 2. A/B Testing de Thumbnails

```python
class ThumbnailOptimizer:
    """Testa múltiplas thumbnails e escolhe a melhor"""

    def generate_thumbnail_variants(self, production: dict) -> list:
        """Gera 3 variantes de thumbnail"""
        clips = production["selected_clips"]

        candidates = []

        # Variante 1: Momento de maior viral_potential
        best_viral_clip = max(clips, key=lambda c: c["viral_potential"])
        candidates.append({
            "type": "high_viral",
            "clip_id": best_viral_clip["id"],
            "timestamp": best_viral_clip["duration"] * 0.5
        })

        # Variante 2: Momento de maior surprise_factor
        best_surprise_clip = max(clips, key=lambda c: c["surprise_factor"])
        candidates.append({
            "type": "high_surprise",
            "clip_id": best_surprise_clip["id"],
            "timestamp": best_surprise_clip["duration"] * 0.7
        })

        # Variante 3: LLM escolhe
        llm_choice = self.ask_llm_best_thumbnail(clips)
        candidates.append(llm_choice)

        return candidates

    def run_ab_test(self, production_id: str, variants: list):
        """
        Testa thumbnails em audiência pequena
        Escolhe vencedor baseado em CTR
        """
        # Implementar com YouTube API ou analytics
        pass
```

---

## 🎓 Conclusão e Próximos Passos

### Implementação Recomendada (Fases)

**Fase 0: Setup (1 semana)**
- [ ] Infraestrutura: PostgreSQL, Qdrant, Redis, Celery
- [ ] API Keys: Claude, OpenAI
- [ ] Storage: MinIO local ou S3

**Fase 1: MVP Indexação (2 semanas)**
- [ ] Pipeline de extração de frames
- [ ] Integração Claude 3.5 Sonnet
- [ ] Schema PostgreSQL básico
- [ ] Script CLI para indexar clips

**Fase 2: RAG Básico (3 semanas)**
- [ ] Setup Qdrant
- [ ] Embeddings com CLIP
- [ ] Busca vetorial híbrida
- [ ] Interface de curadoria manual

**Fase 3: Automação Produção (4 semanas)**
- [ ] LangGraph pipeline completo
- [ ] Renderização com MoviePy
- [ ] API REST (FastAPI)
- [ ] Celery workers

**Fase 4: Otimização (contínuo)**
- [ ] Feedback loop
- [ ] A/B testing
- [ ] Monitoring (Prometheus + Grafana)
- [ ] Fine-tuning de algoritmos

---

**Estimativa Total**: 10-12 semanas para sistema em produção
**Custo Mensal Estimado**: $200-500 (dependendo de volume)
**ROI**: Automação de 90% do processo de curadoria manual
