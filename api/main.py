"""
FastAPI application - RAG Microservice.
Expoe o RAG como servico REST para integracao com MENTOR (React/Node).
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import rag, search, stats, videos
from src.config import settings
from src.services.context_composer import ContextComposer
from src.services.database_service import DatabaseService
from src.services.embedding_service import EmbeddingService
from src.services.gemini_service import GeminiService
from src.services.qdrant_service import QdrantService
from src.services.queue_service import QueueService
from src.services.video_processor import create_processor_callback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa e finaliza servicos."""
    logger.info("Starting RAG Microservice...")

    # Inicializar servicos
    app.state.db = DatabaseService(settings.postgres_url)
    app.state.gemini = GeminiService(
        api_key=settings.google_api_key,
        model=settings.gemini_model,
    )
    app.state.embedding = EmbeddingService(
        api_key=settings.google_api_key,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )
    app.state.qdrant = QdrantService(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        collection=settings.qdrant_collection,
        vector_size=settings.embedding_dimensions,
    )
    app.state.queue = QueueService(settings.postgres_url)
    app.state.queue._ensure_table()
    app.state.composer = ContextComposer()

    # Iniciar worker se RUN_WORKER=1
    if os.environ.get("RUN_WORKER", "0") == "1":
        callback = create_processor_callback(
            db_service=app.state.db,
            gemini_service=app.state.gemini,
            embedding_service=app.state.embedding,
            qdrant_service=app.state.qdrant,
        )
        app.state.queue.start_worker(callback)
        logger.info("Queue worker started")

    logger.info("RAG Microservice ready")
    yield

    # Cleanup
    if app.state.queue.is_worker_running():
        app.state.queue.stop_worker()
        logger.info("Queue worker stopped")
    logger.info("RAG Microservice shutdown complete")


app = FastAPI(
    title="RAG Microservice",
    description="REST API for video RAG - MENTOR integration",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(videos.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(rag.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok"}
