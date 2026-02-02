# Setup Guide - MVP RAG Local para Curadoria de Vídeos
**Sistema Completo com Docker + PostgreSQL + Qdrant + Claude**

## 🎯 O Que Vamos Construir

Sistema RAG multimodal que:
1. ✅ Aproveita seus dados PostgreSQL existentes (descrição, categorias, tags)
2. ✅ Enriquece com análise multimodal (Claude + CLIP)
3. ✅ Indexa embeddings no Qdrant (vector database)
4. ✅ Permite curadoria inteligente por tema
5. ✅ Integra com LangGraph para produção
6. ✅ Roda 100% local (Docker)

## 📊 Arquitetura do MVP

```
┌─────────────────────────────────────────────────────────────────┐
│                    DADOS EXISTENTES                              │
│  PostgreSQL: clips, descrição, categorias, tags, autor           │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                 PIPELINE DE ENRIQUECIMENTO                       │
│                                                                  │
│  1. Ler clip do PostgreSQL                                      │
│  2. Extrair frames (PySceneDetect)                              │
│  3. Analisar com Claude 3.5 Sonnet                              │
│  4. Gerar embeddings (CLIP)                                     │
│  5. Atualizar PostgreSQL + indexar Qdrant                       │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    SISTEMA RAG COMPLETO                          │
│                                                                  │
│  Usuário: "fails épicos de skate"                               │
│      ↓                                                           │
│  Query Expansion (opcional)                                      │
│      ↓                                                           │
│  Busca Vetorial (Qdrant) → Top 100                             │
│      ↓                                                           │
│  Filtros (categorias, tags, intensidade)                        │
│      ↓                                                           │
│  Reranking + Diversidade → Top 30                              │
│      ↓                                                           │
│  Clips selecionados!                                            │
└─────────────────────────────────────────────────────────────────┘
```

## 🗂️ Estrutura de Pastas

```
video-curator-mvp/
├── docker/
│   ├── docker-compose.yml        # Orquestra todos os serviços
│   └── .env.example               # Variáveis de ambiente
│
├── database/
│   ├── migrations/
│   │   ├── 001_extend_schema.sql # Adiciona campos de análise
│   │   └── 002_create_indexes.sql
│   └── seed/
│       └── example_data.sql       # Dados de teste
│
├── src/
│   ├── config.py                  # Configurações centralizadas
│   ├── models.py                  # Modelos de dados (SQLAlchemy)
│   ├── extractors/
│   │   ├── frame_extractor.py    # Extrai frames dos vídeos
│   │   └── metadata_extractor.py # Extrai duração, etc.
│   ├── analyzers/
│   │   ├── claude_analyzer.py    # Análise multimodal com Claude
│   │   └── embedding_generator.py # CLIP embeddings
│   ├── database/
│   │   ├── postgres_client.py    # Client PostgreSQL
│   │   └── qdrant_client.py      # Client Qdrant
│   ├── pipeline/
│   │   ├── enrichment_pipeline.py # Pipeline de enriquecimento
│   │   └── batch_processor.py     # Processar em lote
│   ├── curator/
│   │   ├── intelligent_curator.py # RAG completo
│   │   └── query_expander.py      # Expansão de queries
│   └── cli/
│       ├── enrich.py              # CLI para enriquecer dados
│       ├── search.py              # CLI para buscar clips
│       └── stats.py               # Estatísticas do sistema
│
├── notebooks/
│   ├── 01_explore_data.ipynb      # Explorar dados existentes
│   ├── 02_test_analysis.ipynb     # Testar análise de clips
│   └── 03_test_rag.ipynb          # Testar RAG
│
├── tests/
│   ├── test_extractors.py
│   ├── test_analyzers.py
│   └── test_curator.py
│
├── docs/
│   ├── 01_GETTING_STARTED.md
│   ├── 02_DATABASE_SCHEMA.md
│   ├── 03_ENRICHMENT_PIPELINE.md
│   └── 04_RAG_SYSTEM.md
│
├── scripts/
│   ├── setup.sh                   # Setup inicial
│   ├── migrate.sh                 # Rodar migrações
│   └── start.sh                   # Iniciar sistema
│
├── requirements.txt
└── README.md
```

## 🚀 Quick Start (30 minutos)

### 1. Pré-requisitos

```bash
# Sistema
- Docker + Docker Compose
- Python 3.10+
- Git

# Verificar instalação
docker --version
docker-compose --version
python --version
```

### 2. Clone/Crie o Projeto

```bash
# Criar estrutura
mkdir video-curator-mvp
cd video-curator-mvp

# Criar pastas
mkdir -p docker database/migrations database/seed src/{extractors,analyzers,database,pipeline,curator,cli} notebooks tests docs scripts
```

### 3. Configurar Ambiente

```bash
# Criar .env
cat > docker/.env << EOF
# PostgreSQL (seus dados existentes)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=video_assets
POSTGRES_USER=curator
POSTGRES_PASSWORD=curator_pass_2026

# Qdrant (vector database)
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# Anthropic (Claude)
ANTHROPIC_API_KEY=sk-ant-api03-...

# Paths
VIDEO_STORAGE_PATH=/data/videos
FRAMES_CACHE_PATH=/data/frames_cache

# Processing
MAX_WORKERS=4
BATCH_SIZE=10
EOF
```

### 4. Subir Infraestrutura

```bash
cd docker
docker-compose up -d

# Verificar serviços
docker-compose ps

# Deve mostrar:
# postgres  - Up (porta 5432)
# qdrant    - Up (porta 6333)
```

### 5. Instalar Dependências Python

```bash
cd ..
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 6. Rodar Migração de Schema

```bash
# Adicionar campos de análise ao schema existente
python scripts/migrate.py
```

### 7. Enriquecer Primeiros Clips

```bash
# Enriquecer 10 clips de teste
python -m src.cli.enrich --limit 10

# Acompanhar progresso
# [1/10] Processando clip_001... ✓
# [2/10] Processando clip_002... ✓
```

### 8. Testar Busca RAG

```bash
# Buscar clips
python -m src.cli.search "fails épicos de skate"

# Output:
# 🔍 Buscando: 'fails épicos de skate'
#
# 1. [0.892] Skatista tenta manobra em rampa alta...
#    Intensidade: 8.5/10 | Viral: 9.0/10
#    Tags: skate, fail, rampa, épico
#
# 2. [0.856] Queda espetacular durante competição...
```

---

## 📋 Checklist de Setup Completo

- [ ] Docker Compose rodando (postgres + qdrant)
- [ ] Python venv criado e ativado
- [ ] Dependências instaladas
- [ ] Schema migrado (novos campos adicionados)
- [ ] API key do Claude configurada
- [ ] 10+ clips enriquecidos
- [ ] Busca RAG funcionando
- [ ] Qdrant Web UI acessível (http://localhost:6333/dashboard)

---

## 🔍 Validação

### Verificar PostgreSQL

```bash
# Conectar ao banco
docker exec -it video-curator-postgres psql -U curator -d video_assets

# Verificar novos campos
\d video_clips

# Deve mostrar colunas:
# - scene_description
# - visual_elements
# - emotional_tone
# - intensity
# - viral_potential
# - embedding_id
# ...
```

### Verificar Qdrant

```bash
# Acessar dashboard
open http://localhost:6333/dashboard

# Verificar collection "video_clips" criada
# Verificar vetores indexados
```

### Verificar Análise

```bash
# Ver estatísticas
python -m src.cli.stats

# Output:
# 📊 ESTATÍSTICAS DO SISTEMA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Total de clips: 1,250
# Clips analisados: 45
# Clips pendentes: 1,205
#
# Distribuição de emoções:
#   cômico: 18 (40%)
#   épico: 15 (33%)
#   wholesome: 8 (18%)
#   tenso: 4 (9%)
```

---

## 🐛 Troubleshooting

### Docker não inicia

```bash
# Verificar portas em uso
netstat -an | grep 5432  # PostgreSQL
netstat -an | grep 6333  # Qdrant

# Parar containers conflitantes
docker ps -a
docker stop <container_id>
```

### Erro "Anthropic API key invalid"

```bash
# Verificar .env
cat docker/.env | grep ANTHROPIC

# Testar key
python -c "import anthropic; client = anthropic.Anthropic(api_key='sk-ant-...'); print('OK')"
```

### Qdrant "collection not found"

```bash
# Recriar collection
python -m src.database.qdrant_client --reset
```

### Análise muito lenta

```bash
# Reduzir frames processados
# Em config.py:
MAX_FRAMES_PER_CLIP = 4  # Era 8

# Processar em paralelo
python -m src.cli.enrich --limit 100 --workers 4
```

---

## 📚 Próximos Passos

1. **Enriquecer todos os clips** (rodar batch overnight)
   ```bash
   python -m src.cli.enrich --all --workers 8
   ```

2. **Explorar dados** (Jupyter notebooks)
   ```bash
   jupyter notebook notebooks/01_explore_data.ipynb
   ```

3. **Integrar com LangGraph** (produção automática)
   - Ver `docs/05_LANGGRAPH_INTEGRATION.md`

4. **Otimizar performance**
   - Cache de embeddings
   - Índices PostgreSQL
   - Reranking adaptativo

---

## 💰 Custos Estimados

### Enriquecimento Inicial (1000 clips)
- Claude API (1000 × $0.003): **$3.00**
- Infraestrutura local: **$0**
- Total: **~$3.00**

### Operação Mensal (100 novas clips + 50 produções)
- Análise de clips novos: **$0.30**
- Curadoria (50 vídeos): **$0.65**
- Total: **~$1.00/mês**

**Extremamente viável!**

---

## 🎓 Documentação Adicional

- [Getting Started](docs/01_GETTING_STARTED.md) - Tutorial passo a passo
- [Database Schema](docs/02_DATABASE_SCHEMA.md) - Detalhes do schema
- [Enrichment Pipeline](docs/03_ENRICHMENT_PIPELINE.md) - Como funciona o pipeline
- [RAG System](docs/04_RAG_SYSTEM.md) - Sistema de busca detalhado
- [LangGraph Integration](docs/05_LANGGRAPH_INTEGRATION.md) - Produção automática

---

**Pronto para começar?** Execute os comandos do Quick Start! 🚀
