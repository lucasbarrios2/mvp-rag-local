"""
MVP RAG Local - Entry point Streamlit
"""

import logging

import streamlit as st

from src.config import settings

# Configurar logging para o worker
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


# ============================================================================
# Inicializacao do Worker de Processamento
# ============================================================================


@st.cache_resource
def init_queue_worker():
    """
    Inicializa o worker de processamento de videos em background.
    Usa cache_resource para garantir que inicia apenas uma vez.
    """
    from src.services.database_service import DatabaseService
    from src.services.embedding_service import EmbeddingService
    from src.services.gemini_service import GeminiService
    from src.services.qdrant_service import QdrantService
    from src.services.queue_service import QueueService
    from src.services.video_processor import create_processor_callback

    # Verificar se API key esta configurada
    if not settings.google_api_key:
        logging.warning(
            "GOOGLE_API_KEY nao configurada - worker nao sera iniciado"
        )
        return None

    try:
        # Inicializar servicos
        db_service = DatabaseService(settings.postgres_url)
        gemini_service = GeminiService(
            settings.google_api_key, settings.gemini_model
        )
        embedding_service = EmbeddingService(
            settings.google_api_key,
            settings.embedding_model,
            settings.embedding_dimensions,
        )
        qdrant_service = QdrantService(
            settings.qdrant_host,
            settings.qdrant_port,
            settings.qdrant_collection,
            settings.embedding_dimensions,
        )

        # Criar callback de processamento
        processor_callback = create_processor_callback(
            db_service=db_service,
            gemini_service=gemini_service,
            embedding_service=embedding_service,
            qdrant_service=qdrant_service,
        )

        # Inicializar e iniciar worker
        queue_service = QueueService(settings.postgres_url)
        queue_service.start_worker(
            processor=processor_callback,
            poll_interval=5.0,  # Verificar fila a cada 5 segundos
        )

        logging.info("Worker de processamento iniciado com sucesso")
        return queue_service

    except Exception as e:
        logging.error(f"Erro ao iniciar worker: {e}")
        return None


# ============================================================================
# Configuracao do App
# ============================================================================

st.set_page_config(
    page_title="MVP RAG Local",
    page_icon="🎬",
    layout="wide",
)

# Iniciar worker (apenas uma vez devido ao cache_resource)
worker = init_queue_worker()

# Status do worker na sidebar (simplificado para evitar conflitos)
with st.sidebar:
    if worker is not None:
        st.success("Worker ativo", icon="🟢")
    elif not settings.google_api_key:
        st.warning("API Key nao configurada", icon="⚠️")
    else:
        st.error("Worker inativo", icon="🔴")

# ============================================================================
# Navegacao
# ============================================================================

pg_upload = st.Page("pages/1_Enriquecimento.py", title="Enriquecimento", icon="📤")
pg_search = st.Page("pages/2_Busca_RAG.py", title="Busca RAG", icon="🔍")
pg_direct = st.Page("pages/3_Analise_Direta.py", title="Analise Direta", icon="💬")

nav = st.navigation([pg_upload, pg_search, pg_direct])
nav.run()
