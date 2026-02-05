# MVP RAG Local - Sistema de Curadoria Inteligente de Vídeos
**Produção Automatizada de Vídeos Compilados com IA Multimodal**

---

## 🎯 O Que É Este Sistema?

Sistema completo de **RAG (Retrieval-Augmented Generation) multimodal** que:

1. ✅ **Enriquece** seus clips existentes com análise de IA (Claude 3.5 Sonnet)
2. ✅ **Indexa** embeddings multimodais (CLIP) em vector database (Qdrant)
3. ✅ **Permite busca semântica** por tema/conceito (não apenas keywords)
4. ✅ **Seleciona clips** de forma inteligente para produção de vídeos
5. ✅ **Roda 100% local** via Docker

---

## 📁 Arquivos Criados

```
MVP_LOCAL/
├── 00_SETUP_GUIDE.md              # Guia de setup completo
├── docker-compose.yml              # Orquestração Docker
├── 001_migration_extend_schema.sql # Migração PostgreSQL
├── requirements.txt                # Dependências Python
├── config.py                       # Configurações centralizadas
├── models.py                       # Modelos SQLAlchemy + Pydantic
├── enrichment_pipeline.py          # Pipeline de enriquecimento
└── README_MVP.md                   # Este arquivo
```

---

## 🚀 Quick Start (30 min)

### 1. Pré-requisitos

```bash
# Ter instalado:
- Docker + Docker Compose
- Python 3.10+
- API Key do Anthropic (Claude)
```

### 2. Subir Infraestrutura

```bash
# Navegar para pasta MVP_LOCAL
cd MVP_LOCAL

# Criar .env
cp .env.example .env
# Editar .env e adicionar ANTHROPIC_API_KEY

# Subir serviços
docker-compose up -d

# Verificar
docker-compose ps
# Deve mostrar: postgres (Up), qdrant (Up), redis (Up)
```

### 3. Instalar Python

```bash
# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
```

### 4. Migrar Banco de Dados

```bash
# Conectar ao PostgreSQL existente e rodar migração
docker exec -i video-curator-postgres psql -U curator -d video_assets < 001_migration_extend_schema.sql

# OU se já tiver clips no banco:
psql -h localhost -U curator -d video_assets -f 001_migration_extend_schema.sql
```

### 5. Enriquecer Clips

```bash
# Testar com 10 clips
python enrichment_pipeline.py

# Ou via CLI (quando implementado):
# python -m src.cli.enrich --limit 10
```

### 6. Validar

```bash
# Acessar PostgreSQL
docker exec -it video-curator-postgres psql -U curator -d video_assets

# Verificar clips analisados
SELECT id, id_origem, emotional_tone, intensity, viral_potential
FROM video_clips
WHERE processing_status = 'analyzed'
LIMIT 5;

# Acessar Qdrant Web UI
open http://localhost:6333/dashboard
# Verificar collection "video_clips"
```

---

## 📊 Arquitetura do Sistema

### Fluxo de Dados

```
┌──────────────────────────────────────────────────────────────┐
│  DADOS EXISTENTES (PostgreSQL)                               │
│  - Clips (milhares)                                          │
│  - Descrição breve, categorias, tags, autor                  │
└──────────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────┐
│  PIPELINE DE ENRIQUECIMENTO                                  │
│                                                              │
│  1. Frame Extraction (PySceneDetect/OpenCV)                 │
│     └─> Extrai 8 frames-chave por clip                     │
│                                                              │
│  2. Análise Multimodal (Claude 3.5 Sonnet)                  │
│     └─> Descrição, emoção, intensidade, viral potential    │
│                                                              │
│  3. Embedding Generation (CLIP ViT-L/14)                    │
│     └─> Vector 768-dim (visual + semântico)                │
│                                                              │
│  4. Storage                                                  │
│     ├─> PostgreSQL (metadata enriquecida)                   │
│     └─> Qdrant (embeddings para busca)                     │
└──────────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────┐
│  SISTEMA RAG (Busca + Curadoria)                            │
│                                                              │
│  Usuário: "fails épicos de skate"                           │
│     ↓                                                        │
│  1. Embedding da query (CLIP)                               │
│  2. Vector search (Qdrant) → top 100                        │
│  3. Filtros (categorias, intensidade, viral)                │
│  4. Reranking + Diversidade → top 30                        │
│     ↓                                                        │
│  Clips selecionados!                                         │
└──────────────────────────────────────────────────────────────┘
```

### Componentes

| Componente | Tecnologia | Função |
|------------|------------|--------|
| **PostgreSQL** | postgres:15-alpine | Dados originais + análise |
| **Qdrant** | qdrant:latest | Vector database (embeddings) |
| **Redis** | redis:7-alpine | Cache e fila (futuro) |
| **Claude 3.5** | API Anthropic | Análise multimodal |
| **CLIP** | OpenAI ViT-L/14 | Embeddings visuais |
| **Python** | 3.10+ | Processamento |

---

## 💾 Schema do Banco de Dados

### Campos Adicionados (Migração)

A migração `001_migration_extend_schema.sql` **preserva todos os dados existentes** e adiciona:

**Metadata Básica:**
- `duration_seconds` - Duração do vídeo
- `file_hash` - Hash para detectar duplicatas
- `processing_status` - pending | analyzing | analyzed | failed
- `last_analyzed_at` - Timestamp da última análise

**Análise Visual (Claude):**
- `scene_description` - Descrição detalhada (TEXT)
- `visual_elements` - Lista de elementos (JSONB)
- `key_moments` - Momentos-chave com timestamps (JSONB)

**Análise Emocional:**
- `emotional_tone` - cômico | épico | wholesome | tenso | absurdo
- `intensity` - 0-10 (quão intensa é a cena)
- `surprise_factor` - 0-10 (fator surpresa)
- `viral_potential` - 0-10 (potencial de viralizar)

**Análise Narrativa:**
- `narrative_arc` - Ex: "setup -> escalation -> payoff"
- `standalone` - BOOLEAN (funciona sem contexto?)

**Scores Temáticos:**
- `theme_scores` - JSONB com scores para cada tema

**Embeddings:**
- `embedding_id` - ID no Qdrant
- `frames_cache_path` - Caminho dos frames extraídos

**Métricas:**
- `times_used` - Quantas vezes foi usado
- `last_used_at` - Última vez usado
- `avg_retention_rate` - Performance média

---

## 🔧 Configuração

### Variáveis de Ambiente (.env)

```bash
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=video_assets
POSTGRES_USER=curator
POSTGRES_PASSWORD=sua_senha_aqui

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Anthropic (OBRIGATÓRIO)
ANTHROPIC_API_KEY=sk-ant-api03-...

# Paths (ajustar conforme seu ambiente)
VIDEO_STORAGE_PATH=/path/to/your/videos
FRAMES_CACHE_PATH=/data/frames_cache

# Performance
MAX_WORKERS=4
BATCH_SIZE=10
MAX_FRAMES_PER_CLIP=8
```

### Configurações Avançadas (config.py)

```python
from config import settings

# Alterar modelo CLIP (trade-off velocidade vs qualidade)
settings.clip_model_name = "openai/clip-vit-base-patch32"  # Mais rápido

# Alterar número de frames
settings.max_frames_per_clip = 4  # Processar mais rápido

# Desabilitar reranking (mais rápido)
settings.enable_llm_reranking = False
```

---

## 📖 Como Usar

### 1. Enriquecer Clips

```python
from enrichment_pipeline import EnrichmentPipeline

pipeline = EnrichmentPipeline()

# Enriquecer 10 clips
results = pipeline.enrich_batch(limit=10)

# Enriquecer clip específico
result = pipeline.enrich_clip(clip_id=123)

# Re-analisar clip (force=True)
result = pipeline.enrich_clip(clip_id=123, force=True)
```

### 2. Buscar Clips (RAG)

```python
# TODO: Implementar search_engine.py

from search_engine import RAGSearchEngine

searcher = RAGSearchEngine()

# Busca simples
results = searcher.search("fails épicos de skate", limit=10)

# Busca com filtros
results = searcher.search(
    query="momentos engraçados",
    categorias=["esportes", "comédia"],
    min_intensity=7.0,
    min_viral_potential=8.0
)

# Exibir resultados
for r in results:
    print(f"{r.score:.3f} - {r.scene_description}")
```

### 3. Produzir Vídeo (LangGraph - futuro)

```python
# TODO: Integrar com LangGraph

from langgraph_production import VideoProductionGraph

graph = VideoProductionGraph()

result = graph.produce(
    theme="fails épicos de skate",
    target_duration=600,  # 10 minutos
    style="energetic"
)

print(f"Vídeo produzido: {result.video_path}")
print(f"Título: {result.title}")
```

---

## 📊 Monitoramento

### Estatísticas do Sistema

```sql
-- Total de clips por status
SELECT processing_status, COUNT(*) as total
FROM video_clips
GROUP BY processing_status;

-- Distribuição de emoções
SELECT emotional_tone, COUNT(*) as total
FROM video_clips
WHERE processing_status = 'analyzed'
GROUP BY emotional_tone
ORDER BY total DESC;

-- Top 10 clips mais virais
SELECT id_origem, scene_description, viral_potential
FROM video_clips
WHERE processing_status = 'analyzed'
ORDER BY viral_potential DESC
LIMIT 10;

-- Clips sub-utilizados (alta qualidade, pouco usados)
SELECT id_origem, viral_potential, times_used
FROM video_clips
WHERE viral_potential >= 8.0
  AND times_used < 3
ORDER BY viral_potential DESC;
```

### Qdrant Dashboard

```bash
# Acessar Web UI
open http://localhost:6333/dashboard

# Ver estatísticas
# - Total de vetores indexados
# - Distribuição de clusters
# - Performance de queries
```

---

## 💰 Custos Estimados

### Enriquecimento Inicial (1000 clips)

- **Claude API**: 1000 clips × $0.003 = **$3.00**
- **Infraestrutura local**: **$0**
- **Total**: **~$3.00** (one-time)

### Operação Mensal (100 novos clips + 50 produções)

- **Análise de clips**: 100 × $0.003 = **$0.30**
- **Curadoria (busca RAG)**: 50 × $0.013 = **$0.65**
- **Total**: **~$1.00/mês**

**ROI**: Economiza 40-80h/mês de curadoria manual = **10.000%+ ROI**

---

## 🐛 Troubleshooting

### "ANTHROPIC_API_KEY não encontrada"

```bash
# Verificar .env
cat .env | grep ANTHROPIC

# Testar key
python -c "import anthropic; client = anthropic.Anthropic(api_key='sk-ant-...'); print('OK')"
```

### "Erro ao conectar PostgreSQL"

```bash
# Verificar se container está rodando
docker ps | grep postgres

# Ver logs
docker logs video-curator-postgres

# Testar conexão
docker exec -it video-curator-postgres psql -U curator -d video_assets -c "SELECT 1"
```

### "Qdrant collection not found"

```bash
# Recriar collection
python -c "from enrichment_pipeline import QdrantIndexer; QdrantIndexer()"
```

### Processamento muito lento

```bash
# Reduzir frames
# Em config.py ou .env:
MAX_FRAMES_PER_CLIP=4

# Usar GPU se disponível
CLIP_DEVICE=cuda

# Processar em paralelo (futuro: Celery)
```

---

## 🎓 Próximos Passos

### Curto Prazo (1-2 semanas)

1. **Implementar CLI completo**
   ```bash
   python -m cli.enrich --all
   python -m cli.search "tema"
   python -m cli.stats
   ```

2. **Criar notebooks Jupyter**
   - Explorar dados enriquecidos
   - Visualizar distribuições
   - Testar queries

3. **Otimizar performance**
   - Cache de frames
   - Batch processing com Celery
   - Índices PostgreSQL adicionais

### Médio Prazo (1 mês)

1. **Search Engine completo**
   - Query expansion com LLM
   - Reranking adaptativo
   - MMR para diversidade

2. **Interface Web (Streamlit/Gradio)**
   - Upload de clips
   - Busca interativa
   - Visualização de resultados

3. **Integração LangGraph**
   - Pipeline completo de produção
   - Multi-agentes coordenados
   - Renderização automática

### Longo Prazo (3 meses)

1. **Feedback Loop**
   - Tracking de performance de clips
   - Aprendizado contínuo
   - Re-ranqueamento automático

2. **API REST (FastAPI)**
   - Endpoints para integração
   - Webhooks
   - Dashboard de monitoramento

3. **Deployment em Produção**
   - CI/CD com GitHub Actions
   - Kubernetes (opcional)
   - Monitoring com Prometheus/Grafana

---

## 📚 Documentação Adicional

- [Setup Guide](00_SETUP_GUIDE.md) - Guia completo de instalação
- [Database Schema](001_migration_extend_schema.sql) - Schema detalhado
- [Config Reference](config.py) - Todas as configurações
- [Models Reference](models.py) - Modelos de dados

---

## 🤝 Suporte

**Problemas?** Verifique:
1. Logs do Docker: `docker-compose logs`
2. Conexão com PostgreSQL: `psql -h localhost -U curator -d video_assets`
3. Qdrant dashboard: http://localhost:6333/dashboard
4. API key do Claude está correta

---

## ✅ Checklist de Sucesso

Você tem um MVP funcional quando conseguir:

- [ ] Docker Compose rodando (postgres + qdrant)
- [ ] Migração aplicada (novos campos no schema)
- [ ] 10+ clips enriquecidos com análise
- [ ] Embeddings indexados no Qdrant
- [ ] Busca RAG retornando resultados relevantes
- [ ] Qdrant Web UI acessível e mostrando vetores

**Parabéns! Seu sistema está operacional! 🎉**

---

**Versão**: 1.0.0
**Data**: Janeiro 2026
**Licença**: MIT
