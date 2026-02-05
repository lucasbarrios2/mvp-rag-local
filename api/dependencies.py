"""
Dependency injection para FastAPI.
Extrai servicos do app.state inicializado no lifespan.
"""

from typing import Optional

from fastapi import Depends, Header, HTTPException, Request

from src.config import settings
from src.services.context_composer import ContextComposer
from src.services.database_service import DatabaseService
from src.services.embedding_service import EmbeddingService
from src.services.gemini_service import GeminiService
from src.services.qdrant_service import QdrantService
from src.services.queue_service import QueueService


def get_db(request: Request) -> DatabaseService:
    return request.app.state.db


def get_gemini(request: Request) -> GeminiService:
    return request.app.state.gemini


def get_embedding(request: Request) -> EmbeddingService:
    return request.app.state.embedding


def get_qdrant(request: Request) -> QdrantService:
    return request.app.state.qdrant


def get_queue(request: Request) -> QueueService:
    return request.app.state.queue


def get_composer(request: Request) -> ContextComposer:
    return request.app.state.composer


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> Optional[str]:
    """
    Verifica X-API-Key header.
    Se api_key esta configurada no .env, exige que o header corresponda.
    Se nao esta configurada, acesso livre.
    """
    if not settings.api_key:
        return None
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key
