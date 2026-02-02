# 🚀 Quick Start - MVP RAG Local

## Setup Rápido (30 minutos)

### 1. Executar Setup Automático

```cmd
scripts\setup.bat
```

Este script irá:
- ✅ Verificar Docker e Python
- ✅ Criar ambiente virtual Python
- ✅ Instalar dependências
- ✅ Criar arquivo .env (você precisa editar!)

### 2. Configurar API Key

Edite `docker\.env` e adicione sua chave do Claude:

```bash
ANTHROPIC_API_KEY=sk-ant-api03-SUA_CHAVE_AQUI
```

Obtenha sua chave em: https://console.anthropic.com

### 3. Iniciar Serviços Docker

```cmd
scripts\start.bat
```

Serviços disponíveis:
- **PostgreSQL**: localhost:5432
- **Qdrant**: http://localhost:6333 (Dashboard: http://localhost:6333/dashboard)
- **PgAdmin**: http://localhost:5050 (admin@curator.local / admin)
- **Redis**: localhost:6379

### 4. Migrar Banco de Dados

```cmd
scripts\migrate.bat
```

Isso adiciona os campos de análise multimodal ao seu PostgreSQL **sem perder dados existentes**.

### 5. Enriquecer Clips

```cmd
REM Ativar ambiente virtual
venv\Scripts\activate

REM Rodar pipeline
python src\pipeline\enrichment_pipeline.py
```

### 6. Validar

**PostgreSQL:**
```cmd
docker exec -it video-curator-postgres psql -U curator -d video_assets
```

```sql
-- Ver clips analisados
SELECT id, id_origem, emotional_tone, intensity, viral_potential
FROM video_clips
WHERE processing_status = 'analyzed'
LIMIT 5;
```

**Qdrant Dashboard:**
Abra http://localhost:6333/dashboard e veja a collection "video_clips"

---

## Estrutura do Projeto

```
C:\www\mvp_local\
├── docker/                      # Docker Compose e configs
│   ├── docker-compose.yml       # Orquestração de serviços
│   └── .env.example            # Template de configuração
│
├── database/
│   └── migrations/
│       └── 001_migration_extend_schema.sql  # Migração SQL
│
├── src/                        # Código Python
│   ├── config.py               # Configurações
│   ├── models.py               # Modelos de dados
│   └── pipeline/
│       └── enrichment_pipeline.py  # Pipeline principal
│
├── scripts/                    # Scripts utilitários
│   ├── setup.bat              # Setup inicial
│   ├── start.bat              # Iniciar serviços
│   ├── stop.bat               # Parar serviços
│   └── migrate.bat            # Migrar banco
│
├── docs/                       # Documentação completa
│   ├── 00_SETUP_GUIDE.md      # Guia de setup detalhado
│   └── 02_analise_melhorias_curacao.md  # RAG multimodal
│
├── requirements.txt            # Dependências Python
└── README.md                   # README principal
```

---

## Troubleshooting Rápido

### "Docker não encontrado"
```cmd
REM Instale Docker Desktop:
REM https://www.docker.com/products/docker-desktop
```

### "Python não encontrado"
```cmd
REM Instale Python 3.10+:
REM https://www.python.org/downloads/
```

### "ANTHROPIC_API_KEY não configurada"
```cmd
REM Edite docker\.env e adicione sua chave
notepad docker\.env
```

### Containers não iniciam
```cmd
REM Ver logs
cd docker
docker-compose logs

REM Resetar tudo
docker-compose down -v
docker-compose up -d
```

---

## Próximos Passos

1. **Enriquecer todos os clips**
   ```cmd
   REM Processar em lote
   python src\pipeline\enrichment_pipeline.py --all
   ```

2. **Explorar dados**
   ```cmd
   jupyter notebook notebooks/
   ```

3. **Implementar busca RAG**
   - Ver: `docs/02_analise_melhorias_curacao.md`

4. **Integrar LangGraph**
   - Produção automática de vídeos

---

## Documentação Completa

- **Setup**: `docs/00_SETUP_GUIDE.md`
- **README**: `README.md`
- **RAG Multimodal**: `docs/02_analise_melhorias_curacao.md`
- **Arquitetura**: `docs/04_arquitetura_avancada_sistema.md`

---

## Suporte

Problemas? Verifique:
1. Logs: `cd docker && docker-compose logs`
2. Status: `cd docker && docker-compose ps`
3. Documentação: `docs/00_SETUP_GUIDE.md`

---

**Pronto para começar! 🎬**
