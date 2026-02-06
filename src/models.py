"""
Modelos de Dados - MVP RAG Local
SQLAlchemy (PostgreSQL) + Pydantic (validacao)
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    Boolean,
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

    # Analise Gemini - COMPILATION (uso editorial para compilados)
    event_headline = Column(Text)
    trim_in_ms = Column(Integer)
    trim_out_ms = Column(Integer)
    money_shot_ms = Column(Integer)
    camera_type = Column(String(50))
    audio_usability = Column(String(20))
    audio_usability_reason = Column(Text)
    compilation_themes = Column(JSONB, default=[])
    narration_suggestion = Column(Text)
    location_country = Column(String(200))
    location_environment = Column(String(50))
    standalone_score = Column(
        Float, CheckConstraint("standalone_score >= 0 AND standalone_score <= 10")
    )
    visual_quality_score = Column(
        Float, CheckConstraint("visual_quality_score >= 0 AND visual_quality_score <= 10")
    )

    # Campos legados (mantidos para compatibilidade)
    analysis_description = Column(Text)
    tags = Column(JSONB, default=[])

    # Embeddings (dois vetores)
    visual_embedding_id = Column(String(255))
    narrative_embedding_id = Column(String(255))
    embedding_id = Column(String(255))  # Legado

    # Source metadata (Newsflare, via MENTOR)
    newsflare_id = Column(String(255), unique=True)
    event_date = Column(TIMESTAMP)
    filming_location = Column(Text)
    uploader = Column(String(500))
    category = Column(String(200))
    is_exclusive = Column(Boolean, default=False)
    license_type = Column(String(100))
    source_description = Column(Text)
    source_tags = Column(JSONB, default=[])
    newsflare_metadata = Column(JSONB, default={})

    # Audio context
    audio_transcript = Column(Text)
    audio_language = Column(String(50))
    has_speech = Column(Boolean)
    audio_description = Column(Text)

    # Tracking
    source = Column(String(50), default="local")

    # Unified embedding
    unified_embedding_id = Column(String(255))

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


class CompilationAnalysis(BaseModel):
    """Resultado da analise COMPILATION do video (uso editorial para compilados)."""

    event_headline: str = Field(..., description="Frase curta para legenda")
    trim_in_ms: int = Field(0, ge=0, description="Inicio da acao util em ms")
    trim_out_ms: int = Field(0, ge=0, description="Fim da acao util em ms")
    money_shot_ms: int = Field(0, ge=0, description="Frame de maximo impacto em ms")
    camera_type: str = Field(
        default="other",
        description="Tipo de camera: cctv, dashcam, cellphone, drone, bodycam, gopro, professional, other",
    )
    audio_usability: str = Field(
        default="mixed",
        description="Usabilidade do audio: usable, replace, silent, mixed",
    )
    audio_usability_reason: str = Field(
        default="", description="Razao da classificacao de audio"
    )
    compilation_themes: list[str] = Field(
        default_factory=list, description="Temas da taxonomia de compilados"
    )
    narration_suggestion: str = Field(
        default="", description="Frase sugerida para narrador"
    )
    location_country: str = Field(default="", description="Pais/regiao")
    location_environment: str = Field(
        default="other",
        description="Ambiente: urban, rural, highway, forest, ocean, indoor, suburban, mountain, desert, river, farm, stadium, other",
    )
    standalone_score: float = Field(
        5.0, ge=0.0, le=10.0, description="Score de autonomia do clip"
    )
    visual_quality_score: float = Field(
        5.0, ge=0.0, le=10.0, description="Score de qualidade visual"
    )


class FullVideoAnalysis(BaseModel):
    """Resultado completo com 3 analises (visual + narrativa + compilation)."""

    visual: VisualAnalysis
    narrative: NarrativeAnalysis
    compilation: CompilationAnalysis

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
