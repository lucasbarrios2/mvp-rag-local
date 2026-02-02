"""
Modelos de Dados - MVP RAG Local
SQLAlchemy (PostgreSQL) + Pydantic (validacao)
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
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

    # Analise Gemini
    analysis_description = Column(Text)
    tags = Column(JSONB, default=[])
    emotional_tone = Column(String(100))
    intensity = Column(
        Float, CheckConstraint("intensity >= 0 AND intensity <= 10")
    )
    viral_potential = Column(
        Float, CheckConstraint("viral_potential >= 0 AND viral_potential <= 10")
    )
    key_moments = Column(JSONB, default=[])
    themes = Column(JSONB, default={})

    # Embedding
    embedding_id = Column(String(255))

    # Timestamps
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())
    analyzed_at = Column(TIMESTAMP)

    def __repr__(self):
        return f"<Video(id={self.id}, filename='{self.filename}')>"


# ============================================================================
# PYDANTIC
# ============================================================================


class VideoAnalysis(BaseModel):
    """Resultado da analise Gemini de um video."""

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

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    """Resposta completa de busca RAG."""

    query: str
    results: list[SearchResult] = Field(default_factory=list)
    rag_response: str = ""
