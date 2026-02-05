"""
Modelos de Dados - MVP RAG Local
SQLAlchemy (PostgreSQL) + Pydantic (validacao)
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    BigInteger,
    TIMESTAMP,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func


# ============================================================================
# SQLALCHEMY
# ============================================================================

Base = declarative_base()


class Video(Base):
    """Tabela videos - mapeamento do schema SQL."""

    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Arquivo
    filename = Column(String(500), nullable=False)
    file_path = Column(Text, nullable=False)
    file_size_bytes = Column(BigInteger)
    duration_seconds = Column(Float)
    mime_type = Column(String(100))

    # Status
    processing_status = Column(String(50), default="pending", index=True)
    error_message = Column(Text)

    # Analise Gemini - VISUAL (frame a frame)
    visual_description = Column(Text)
    visual_tags = Column(JSONB, default=[])
    objects_detected = Column(JSONB, default=[])
    scenes = Column(JSONB, default=[])
    visual_style = Column(String(100))
    color_palette = Column(JSONB, default=[])
    movement_intensity = Column(Float)

    # Analise Gemini - NARRATIVA (contexto e significado)
    narrative_description = Column(Text)
    narrative_tags = Column(JSONB, default=[])
    emotional_tone = Column(String(100))
    intensity = Column(
        Float, CheckConstraint("intensity >= 0 AND intensity <= 10")
    )
    viral_potential = Column(
        Float, CheckConstraint("viral_potential >= 0 AND viral_potential <= 10")
    )
    key_moments = Column(JSONB, default=[])
    themes = Column(JSONB, default={})
    storytelling_elements = Column(JSONB, default={})
    target_audience = Column(Text)

    # Campos legados (mantidos para compatibilidade)
    analysis_description = Column(Text)
    tags = Column(JSONB, default=[])

    # Embeddings (dois vetores)
    visual_embedding_id = Column(String(255))
    narrative_embedding_id = Column(String(255))
    embedding_id = Column(String(255))  # Legado

    # Timestamps
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())
    analyzed_at = Column(TIMESTAMP)

    def __repr__(self):
        return f"<Video(id={self.id}, filename='{self.filename}')>"


# ============================================================================
# PYDANTIC
# ============================================================================


class VisualAnalysis(BaseModel):
    """Resultado da analise VISUAL do video (frame a frame)."""

    visual_description: str = Field(..., description="Descricao dos elementos visuais")
    visual_tags: list[str] = Field(default_factory=list, description="Tags visuais")
    objects_detected: list[str] = Field(default_factory=list, description="Objetos detectados")
    scenes: list[dict] = Field(default_factory=list, description="Cenas com timestamps")
    visual_style: str = Field(default="", description="Estilo visual predominante")
    color_palette: list[str] = Field(default_factory=list, description="Paleta de cores")
    movement_intensity: float = Field(default=5.0, ge=0.0, le=10.0)
    duration_estimate: Optional[float] = Field(None, description="Duracao estimada")


class NarrativeAnalysis(BaseModel):
    """Resultado da analise NARRATIVA do video (contexto e significado)."""

    narrative_description: str = Field(..., description="Descricao narrativa/contextual")
    narrative_tags: list[str] = Field(default_factory=list, description="Tags narrativas")
    emotional_tone: str = Field(..., description="Tom emocional predominante")
    themes: dict[str, float] = Field(default_factory=dict, description="Scores por tema")
    storytelling_elements: dict = Field(default_factory=dict, description="Elementos narrativos")
    target_audience: str = Field(default="", description="Publico-alvo")
    viral_potential: float = Field(..., ge=0.0, le=10.0)
    intensity: float = Field(..., ge=0.0, le=10.0)
    key_moments: list[dict] = Field(default_factory=list, description="Momentos-chave")


class DualVideoAnalysis(BaseModel):
    """Resultado completo com ambas as analises (visual + narrativa)."""

    visual: VisualAnalysis
    narrative: NarrativeAnalysis

    @property
    def duration_estimate(self) -> Optional[float]:
        return self.visual.duration_estimate


class VideoAnalysis(BaseModel):
    """Resultado da analise Gemini de um video (modelo legado para compatibilidade)."""

    description: str = Field(..., description="Descricao rica do video")
    tags: list[str] = Field(default_factory=list, description="Tags extraidas")
    emotional_tone: str = Field(..., description="Tom emocional predominante")
    intensity: float = Field(..., ge=0.0, le=10.0)
    viral_potential: float = Field(..., ge=0.0, le=10.0)
    key_moments: list[dict] = Field(
        default_factory=list, description="Momentos-chave com timestamps"
    )
    themes: dict[str, float] = Field(
        default_factory=dict, description="Scores por tema (0-10)"
    )
    duration_estimate: Optional[float] = Field(
        None, description="Duracao estimada pelo Gemini em segundos"
    )


class SearchResult(BaseModel):
    """Resultado individual de busca."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    score: float
    analysis_description: Optional[str] = None
    emotional_tone: Optional[str] = None
    intensity: Optional[float] = None
    viral_potential: Optional[float] = None
    tags: list[str] = Field(default_factory=list)
    themes: dict[str, float] = Field(default_factory=dict)
    duration_seconds: Optional[float] = None
    file_path: Optional[str] = None


class SearchResponse(BaseModel):
    """Resposta completa de busca RAG."""

    query: str
    results: list[SearchResult] = Field(default_factory=list)
    rag_response: str = ""
