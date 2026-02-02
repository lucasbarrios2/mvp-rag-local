# CLAUDE.md - MVP RAG Local

## O que e este projeto

Sistema RAG (Retrieval-Augmented Generation) para curadoria inteligente de videos. Upload de videos via interface web, analise automatica com Google Gemini (video nativo), indexacao de embeddings em banco vetorial (Qdrant) e busca semantica com respostas RAG.

## Stack principal

- **Linguagem:** Python 3.10+
- **LLM:** Google Gemini 2.5 Flash Preview (google-genai >= 1.0.0)
- **Embeddings:** Google text-embedding-004 (768-dim)
- **Banco relacional:** PostgreSQL 15 (SQLAlchemy 2.0 + psycopg2)
- **Banco vetorial:** Qdrant v1.7.4
- **Interface:** Streamlit
- **Infra:** Docker Compose (PostgreSQL + Qdrant)
- **Validacao:** Pydantic v2 + pydantic-settings

## Estrutura do projeto

```
app.py                          # Entry point Streamlit
pages/
  1_Enriquecimento.py           # Upload + analise Gemini
  2_Busca_RAG.py                # Busca semantica + chat RAG
src/
  __init__.py
  config.py                     # Configuracao (Pydantic Settings, .env)
  models.py                     # SQLAlchemy (Video) + Pydantic (VideoAnalysis, SearchResult, SearchResponse)
  services/
    __init__.py
    gemini_service.py           # Analise de video + RAG via Gemini
    embedding_service.py        # Google text embeddings
    qdrant_service.py           # Indexacao + busca vetorial
    database_service.py         # CRUD PostgreSQL
database/migrations/
  001_create_videos.sql         # Schema da tabela videos
docker/
  docker-compose.yml            # PostgreSQL + Qdrant
  .env.example                  # Variaveis Docker
scripts/
  setup.bat                     # Setup inicial (venv, deps, .env)
  start.bat                     # Subir Docker
  stop.bat                      # Parar Docker
uploads/                        # Videos enviados (gitignored)
.env.example                    # Config na raiz para Streamlit
```

## Fluxo de dados

1. Usuario faz upload de video via Streamlit
2. Video salvo em `uploads/`
3. Upload para Gemini File API, analise completa do video
4. Gemini retorna: descricao, tags, tom emocional, intensidade, potencial viral, momentos-chave, temas
5. Texto da analise transformado em embedding via text-embedding-004
6. Embedding indexado no Qdrant com metadados
7. PostgreSQL atualizado com resultados
8. Busca semantica: query do usuario -> embedding -> Qdrant -> contexto -> Gemini RAG -> resposta

## Comandos essenciais

```bash
# Setup inicial
scripts/setup.bat

# Subir servicos Docker
scripts/start.bat

# Parar servicos
scripts/stop.bat

# Rodar interface
streamlit run app.py
```

## Servicos Docker e portas

| Servico    | Porta | Finalidade           |
|------------|-------|----------------------|
| PostgreSQL | 5432  | Dados + metadados    |
| Qdrant     | 6333  | Embeddings vetoriais |

## Configuracao

- Arquivo `.env` na raiz (copiar de `.env.example`)
- Chave obrigatoria: `GOOGLE_API_KEY`
- Embedding model: text-embedding-004 (768 dimensoes)
- Configuracoes via `src/config.py` (Pydantic Settings)

## Convencoes de codigo

- Modelos de banco: SQLAlchemy declarative
- Modelos de validacao: Pydantic v2 BaseModel
- Configuracao: Pydantic BaseSettings com `.env`
- Tipagem: type hints em todas as funcoes
- Formatacao: black + ruff
- Testes: pytest
- Idioma do codigo: ingles (variaveis, classes, funcoes)
- Idioma da documentacao: portugues (BR)

## Campos da tabela videos

- `filename`, `file_path`, `file_size_bytes`, `duration_seconds`, `mime_type`
- `processing_status`: pending | analyzing | analyzed | failed
- `analysis_description`: descricao rica gerada pelo Gemini
- `tags`: JSONB array de tags
- `emotional_tone`: tom emocional predominante
- `intensity`: 0-10
- `viral_potential`: 0-10
- `key_moments`: JSONB com timestamps e eventos
- `themes`: JSONB com scores por tema
- `embedding_id`: ID no Qdrant
