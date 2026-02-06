"""
Response schemas para a API FastAPI.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class VideoContext(BaseModel):
    """Contexto completo de um video."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    duration_seconds: Optional[float] = None
    mime_type: Optional[str] = None
    processing_status: Optional[str] = None
    error_message: Optional[str] = None

    # Visual
    visual_description: Optional[str] = None
    visual_tags: Optional[list] = None
    objects_detected: Optional[list] = None
    visual_style: Optional[str] = None

    # Narrative
    narrative_description: Optional[str] = None
    narrative_tags: Optional[list] = None
    emotional_tone: Optional[str] = None
    intensity: Optional[float] = None
    viral_potential: Optional[float] = None
    themes: Optional[dict] = None
    key_moments: Optional[list] = None
    target_audience: Optional[str] = None

    # Compilation
    event_headline: Optional[str] = None
    trim_in_ms: Optional[int] = None
    trim_out_ms: Optional[int] = None
    money_shot_ms: Optional[int] = None
    camera_type: Optional[str] = None
    audio_usability: Optional[str] = None
    audio_usability_reason: Optional[str] = None
    compilation_themes: Optional[list] = None
    narration_suggestion: Optional[str] = None
    location_country: Optional[str] = None
    location_environment: Optional[str] = None
    standalone_score: Optional[float] = None
    visual_quality_score: Optional[float] = None

    # Source metadata
    newsflare_id: Optional[str] = None
    category: Optional[str] = None
    filming_location: Optional[str] = None
    uploader: Optional[str] = None
    is_exclusive: Optional[bool] = None
    source_description: Optional[str] = None
    source_tags: Optional[list] = None
    source: Optional[str] = None

    # Audio
    audio_transcript: Optional[str] = None
    audio_description: Optional[str] = None

    # Legacy
    analysis_description: Optional[str] = None
    tags: Optional[list] = None

    # Embedding IDs
    unified_embedding_id: Optional[str] = None

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    analyzed_at: Optional[datetime] = None


class VideoSummary(BaseModel):
    """Resumo de um video para listagem."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    processing_status: Optional[str] = None
    error_message: Optional[str] = None
    emotional_tone: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None
    created_at: Optional[datetime] = None


class VideoListResponse(BaseModel):
    """Resposta de listagem de videos."""

    total: int
    videos: list[VideoSummary] = Field(default_factory=list)


class SearchHit(BaseModel):
    """Resultado individual de busca."""

    id: int
    filename: Optional[str] = None
    score: float
    category: Optional[str] = None
    emotional_tone: Optional[str] = None
    intensity: Optional[float] = None
    viral_potential: Optional[float] = None
    is_exclusive: Optional[bool] = None
    source: Optional[str] = None
    # Compilation fields
    event_headline: Optional[str] = None
    camera_type: Optional[str] = None
    standalone_score: Optional[float] = None
    visual_quality_score: Optional[float] = None
    compilation_themes: Optional[list] = None


class SearchResponse(BaseModel):
    """Resposta de busca semantica."""

    query: str
    total_results: int
    results: list[SearchHit] = Field(default_factory=list)


class RAGSource(BaseModel):
    """Fonte usada na resposta RAG."""

    video_id: int
    filename: Optional[str] = None
    score: float
    category: Optional[str] = None
    emotional_tone: Optional[str] = None


class RAGResponse(BaseModel):
    """Resposta RAG completa."""

    query: str
    answer: str
    sources: list[RAGSource] = Field(default_factory=list)
    model_used: str = ""


class StatsResponse(BaseModel):
    """Estatisticas do sistema."""

    videos_total: int = 0
    videos_analyzed: int = 0
    videos_pending: int = 0
    videos_failed: int = 0
    videos_with_metadata: int = 0
    videos_with_unified_embedding: int = 0
    queue_pending: int = 0
    queue_processing: int = 0
    queue_completed: int = 0
    queue_failed: int = 0
    qdrant_collections: Optional[dict] = None


class IngestResponse(BaseModel):
    """Resposta de ingestao de video."""

    video_id: int
    filename: str
    status: str
    queued: bool
    message: str


class MetadataUpdateResponse(BaseModel):
    """Resposta de atualizacao de metadata."""

    video_id: int
    updated: bool
    unified_embedding_regenerated: bool = False
    message: str


class DeleteResponse(BaseModel):
    """Resposta de delecao de video."""

    video_id: int
    deleted: bool
    message: str
