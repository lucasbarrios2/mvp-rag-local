# 📁 Estrutura do Projeto - MVP RAG Local

## Localização

```
C:\www\mvp_local\
```

---

## Estrutura de Diretórios

```
mvp_local/
│
├── 📄 README.md                    # README principal do projeto
├── 📄 QUICK_START.md               # Guia rápido de início (30 min)
├── 📄 LICENSE                      # Licença MIT
├── 📄 .gitignore                   # Arquivos ignorados pelo Git
├── 📄 requirements.txt             # Dependências Python
│
├── 📂 docker/                      # Infraestrutura Docker
│   ├── docker-compose.yml          # Orquestração de serviços
│   └── .env.example                # Template de configuração
│
├── 📂 database/
│   └── migrations/
│       └── 001_migration_extend_schema.sql  # Migração PostgreSQL
│
├── 📂 src/                         # Código-fonte Python
│   ├── __init__.py
│   ├── config.py                   # Configurações centralizadas
│   ├── models.py                   # Modelos SQLAlchemy + Pydantic
│   │
│   ├── extractors/                 # Extração de frames
│   │   └── __init__.py
│   │
│   ├── analyzers/                  # Análise multimodal (Claude)
│   │   └── __init__.py
│   │
│   ├── database/                   # Clientes DB (PostgreSQL + Qdrant)
│   │   └── __init__.py
│   │
│   ├── pipeline/                   # Pipeline de enriquecimento
│   │   ├── __init__.py
│   │   └── enrichment_pipeline.py  # ⭐ Pipeline principal
│   │
│   ├── curator/                    # Sistema RAG de curadoria
│   │   └── __init__.py
│   │
│   └── cli/                        # Interface de linha de comando
│       └── __init__.py
│
├── 📂 scripts/                     # Scripts utilitários (Windows)
│   ├── setup.bat                   # Setup inicial automatizado
│   ├── start.bat                   # Iniciar serviços Docker
│   ├── stop.bat                    # Parar serviços Docker
│   └── migrate.bat                 # Rodar migração do banco
│
├── 📂 docs/                        # Documentação completa
│   ├── 00_README_GERAL.md          # Índice geral de documentação
│   ├── 00_SETUP_GUIDE.md           # Guia de setup detalhado
│   ├── 01_sistema_base.md          # Sistema multi-agente base
│   ├── 02_analise_melhorias_curacao.md  # ⭐ RAG multimodal detalhado
│   ├── 03_implementacao_rag_multimodal.py  # Código de referência
│   ├── 04_arquitetura_avancada_sistema.md  # Arquitetura de produção
│   ├── 05_guia_quick_start.md      # Tutorial rápido
│   └── INDICE_COMPLETO.md          # Índice completo com resumo
│
├── 📂 notebooks/                   # Jupyter notebooks (criar depois)
│   └── (vazio - criar conforme necessidade)
│
├── 📂 tests/                       # Testes automatizados (criar depois)
│   └── (vazio - criar conforme necessidade)
│
└── 📂 data/                        # Dados locais (criar ao rodar)
    ├── frames_cache/               # Cache de frames extraídos
    └── videos/                     # Links simbólicos para vídeos
```

---

## Arquivos Principais

### 🔥 Arquivos Críticos (Precisa Configurar)

1. **docker/.env**
   - Copiar de `.env.example`
   - Adicionar `ANTHROPIC_API_KEY`
   - Ajustar paths se necessário

2. **docker/docker-compose.yml**
   - Define PostgreSQL, Qdrant, Redis, PgAdmin
   - Pronto para rodar

3. **database/migrations/001_migration_extend_schema.sql**
   - Adiciona 30+ campos ao schema
   - **PRESERVA dados existentes**
   - Rodar via `scripts\migrate.bat`

4. **src/pipeline/enrichment_pipeline.py**
   - Pipeline completo de enriquecimento
   - Extrai frames → Analisa com Claude → Gera embeddings → Indexa
   - Pronto para rodar

### 📖 Documentação Essencial

1. **QUICK_START.md** - Comece aqui (30 min)
2. **README.md** - Visão geral do projeto
3. **docs/00_SETUP_GUIDE.md** - Setup detalhado
4. **docs/02_analise_melhorias_curacao.md** - RAG multimodal (conceitos)
5. **docs/INDICE_COMPLETO.md** - Índice master

### ⚙️ Scripts Utilitários

1. **scripts/setup.bat** - Setup inicial completo
2. **scripts/start.bat** - Inicia Docker (PostgreSQL + Qdrant + etc)
3. **scripts/migrate.bat** - Roda migração SQL
4. **scripts/stop.bat** - Para serviços Docker

---

## Como Usar

### Setup Inicial (Primeira vez)

```cmd
REM 1. Setup automático
scripts\setup.bat

REM 2. Editar .env (adicionar ANTHROPIC_API_KEY)
notepad docker\.env

REM 3. Iniciar serviços
scripts\start.bat

REM 4. Migrar banco de dados
scripts\migrate.bat

REM 5. Ativar ambiente virtual
venv\Scripts\activate

REM 6. Enriquecer clips
python src\pipeline\enrichment_pipeline.py
```

### Uso Diário

```cmd
REM Iniciar serviços
scripts\start.bat

REM Ativar venv
venv\Scripts\activate

REM Processar clips
python src\pipeline\enrichment_pipeline.py

REM Parar serviços ao final
scripts\stop.bat
```

---

## Serviços Docker

Quando rodar `scripts\start.bat`, você terá:

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **PostgreSQL** | localhost:5432 | curator / (veja .env) |
| **Qdrant** | http://localhost:6333 | Sem autenticação |
| **Qdrant Dashboard** | http://localhost:6333/dashboard | - |
| **PgAdmin** | http://localhost:5050 | admin@curator.local / admin |
| **Redis** | localhost:6379 | Sem autenticação |

---

## Fluxo de Trabalho

### 1. Enriquecimento de Clips

```
Clip no PostgreSQL (seus dados existentes)
    ↓
FrameExtractor: Extrai 8 frames-chave
    ↓
ClaudeAnalyzer: Analisa com Claude 3.5 Sonnet
    → scene_description
    → emotional_tone, intensity, viral_potential
    → visual_elements, key_moments
    ↓
EmbeddingGenerator: Gera embedding 768-dim (CLIP)
    ↓
PostgreSQL: Atualiza campos de análise
Qdrant: Indexa embedding
```

### 2. Busca RAG (Futuro)

```
Usuário: "fails épicos de skate"
    ↓
Query Embedding (CLIP)
    ↓
Vector Search (Qdrant) → Top 100
    ↓
Filtros (categorias, intensidade, viral)
    ↓
Reranking + Diversidade → Top 30
    ↓
Clips selecionados!
```

---

## Dependências Principais

**AI & ML:**
- anthropic (Claude)
- transformers (CLIP)
- torch (PyTorch)
- qdrant-client (Vector DB)

**Database:**
- psycopg2-binary (PostgreSQL)
- SQLAlchemy (ORM)

**Vídeo:**
- opencv-python
- scenedetect
- pillow

**Utils:**
- pydantic
- rich
- tqdm

---

## Dados Persistentes

Volumes Docker (não são perdidos ao reiniciar):

```
C:\Users\<USUARIO>\AppData\Local\Docker\wsl\data\
```

Ou visualizar com:
```cmd
docker volume ls
```

---

## Próximos Passos

1. ✅ Setup inicial (`scripts\setup.bat`)
2. ✅ Configurar .env
3. ✅ Iniciar serviços (`scripts\start.bat`)
4. ✅ Migrar banco (`scripts\migrate.bat`)
5. ⬜ Enriquecer clips (`python src\pipeline\enrichment_pipeline.py`)
6. ⬜ Validar no Qdrant dashboard
7. ⬜ Implementar busca RAG
8. ⬜ Integrar LangGraph

---

## Suporte

**Problemas?**
1. Ver logs: `cd docker && docker-compose logs`
2. Status: `cd docker && docker-compose ps`
3. Ler: `docs/00_SETUP_GUIDE.md`
4. Troubleshooting: `QUICK_START.md`

---

**Projeto pronto para uso! 🚀**

**Localização**: `C:\www\mvp_local\`
**Versão**: 1.0.0
**Data**: Janeiro 2026
