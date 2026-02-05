"""
Request schemas para a API FastAPI.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NewsflareMetadata(BaseModel):
    """Metadata de video vinda do Newsflare/MENTOR."""

    newsflare_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    uploader: Optional[str] = None
    filming_date: Optional[datetime] = None
    filming_location: Optional[str] = None
    is_exclusive: Optional[bool] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    license_type: Optional[str] = None
    extra: Optional[dict] = None


class SearchFilters(BaseModel):
    """Filtros para busca vetorial."""

    category: Optional[str] = None
    is_exclusive: Optional[bool] = None
    emotional_tone: Optional[str] = None
    intensity_min: Optional[float] = Field(None, ge=0.0, le=10.0)
    intensity_max: Optional[float] = Field(None, ge=0.0, le=10.0)
    viral_potential_min: Optional[float] = Field(None, ge=0.0, le=10.0)
    viral_potential_max: Optional[float] = Field(None, ge=0.0, le=10.0)
    source: Optional[str] = None


class SearchRequest(BaseModel):
    """Request de busca semantica."""

    query: str = Field(..., min_length=1, description="Texto da busca")
    filters: Optional[SearchFilters] = None
    limit: int = Field(default=10, ge=1, le=100)


class RAGQueryRequest(BaseModel):
    """Request de query RAG (busca + geracao de resposta)."""

    query: str = Field(..., min_length=1, description="Pergunta do usuario")
    filters: Optional[SearchFilters] = None
    limit: int = Field(default=5, ge=1, le=20)
    include_video_analysis: bool = Field(
        default=False, description="Se True, envia videos para Gemini analisar diretamente"
    )
    max_videos_for_analysis: int = Field(default=3, ge=1, le=5)


class SimilarRequest(BaseModel):
    """Request de busca por videos similares."""

    limit: int = Field(default=10, ge=1, le=50)
