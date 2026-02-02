"""
Modelos de Dados - MVP RAG Local
SQLAlchemy para PostgreSQL + Pydantic para validação
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, TIMESTAMP,
    ARRAY, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# SQLALCHEMY BASE
# ============================================================================

Base = declarative_base()


# ============================================================================
# SQLALCHEMY MODELS (Database Tables)
# ============================================================================

class VideoClip(Base):
    """
    Tabela de clips de vídeo
    Combina dados originais + análise multimodal
    """

    __tablename__ = "video_clips"

    # ========================================================================
    # DADOS ORIGINAIS (já existentes)
    # ========================================================================

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_origem = Column(String(255), unique=True, index=True)
    descricao_breve = Column(Text)
    local = Column(Text, nullable=False)  # Caminho do arquivo
    categorias = Column(ARRAY(Text))
    tags = Column(ARRAY(Text))
    autor = Column(String(255))

    # ========================================================================
    # METADATA BÁSICA
    # ========================================================================

    duration_seconds = Column(Float)
    file_hash = Column(String(64), unique=True)
    processing_status = Column(
        String(50),
        default="pending",
        index=True
    )  # pending, analyzing, analyzed, failed

    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())
    last_analyzed_at = Column(TIMESTAMP)

    # ========================================================================
    # ANÁLISE VISUAL (gerada por Claude)
    # ========================================================================

    scene_description = Column(Text)  # Descrição rica por LLM
    visual_elements = Column(JSONB)   # ["rampa", "skate", "pessoa"]
    key_moments = Column(JSONB)       # [{"timestamp": 2.1, "event": "queda"}]

    # ========================================================================
    # ANÁLISE EMOCIONAL
    # ========================================================================

    emotional_tone = Column(String(50), index=True)  # cômico, épico, etc
    intensity = Column(Float, CheckConstraint("intensity BETWEEN 0 AND 10"))
    surprise_factor = Column(Float, CheckConstraint("surprise_factor BETWEEN 0 AND 10"))
    viral_potential = Column(Float, CheckConstraint("viral_potential BETWEEN 0 AND 10"))

    # ========================================================================
    # ANÁLISE NARRATIVA
    # ========================================================================

    narrative_arc = Column(Text)  # "setup -> escalation -> payoff"
    standalone = Column(Boolean, index=True)  # Funciona sem contexto?

    # ========================================================================
    # SCORES TEMÁTICOS
    # ========================================================================

    theme_scores = Column(JSONB)  # {"fails": 9.0, "sports": 7.5}

    # ========================================================================
    # EMBEDDINGS
    # ========================================================================

    embedding_id = Column(String(255), index=True)  # ID no Qdrant
    frames_cache_path = Column(Text)  # Caminho dos frames

    # ========================================================================
    # MÉTRICAS DE PERFORMANCE
    # ========================================================================

    times_used = Column(Integer, default=0)
    last_used_at = Column(TIMESTAMP)
    avg_retention_rate = Column(Float)  # Performance em vídeos

    def __repr__(self):
        return f"<VideoClip(id={self.id}, id_origem='{self.id_origem}')>"


# ============================================================================
# PYDANTIC MODELS (Validation & API)
# ============================================================================

class AnalysisResult(BaseModel):
    """
    Resultado da análise multimodal de um clip
    Retornado pelo Claude Analyzer
    """

    scene_description: str = Field(..., description="Descrição detalhada da cena")

    visual_elements: List[str] = Field(
        default_factory=list,
        description="Elementos visuais detectados"
    )

    key_moments: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Momentos-chave no vídeo"
    )

    emotional_tone: str = Field(
        ...,
        description="Tom emocional: cômico, épico, wholesome, tenso, absurdo"
    )

    intensity: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Intensidade da cena (0-10)"
    )

    surprise_factor: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Fator surpresa (0-10)"
    )

    viral_potential: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Potencial viral (0-10)"
    )

    narrative_arc: str = Field(
        ...,
        description="Arco narrativo do clip"
    )

    standalone: bool = Field(
        ...,
        description="Clip funciona sem contexto adicional?"
    )

    theme_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Scores de adequação para temas"
    )

    @field_validator("emotional_tone")
    @classmethod
    def validate_emotional_tone(cls, v: str) -> str:
        """Valida tom emocional"""
        valid_tones = {
            "cômico", "épico", "wholesome", "tenso",
            "absurdo", "emocionante", "calmo"
        }
        if v.lower() not in valid_tones:
            # Aceitar, mas avisar
            pass
        return v.lower()


class ClipSearchResult(BaseModel):
    """
    Resultado de busca RAG
    """

    id: int
    id_origem: str
    score: float  # Similarity score (0-1)

    # Dados originais
    descricao_breve: Optional[str] = None
    categorias: Optional[List[str]] = None
    tags: Optional[List[str]] = None

    # Análise
    scene_description: Optional[str] = None
    emotional_tone: Optional[str] = None
    intensity: Optional[float] = None
    viral_potential: Optional[float] = None

    # Metadata
    duration_seconds: Optional[float] = None
    times_used: int = 0

    class Config:
        from_attributes = True


class EnrichmentRequest(BaseModel):
    """
    Request para enriquecer um clip
    """

    clip_id: Optional[int] = None
    id_origem: Optional[str] = None
    force: bool = False  # Re-analisar mesmo se já foi analisado


class EnrichmentResult(BaseModel):
    """
    Resultado do enriquecimento
    """

    success: bool
    clip_id: int
    id_origem: str

    analysis: Optional[AnalysisResult] = None
    embedding_generated: bool = False
    error: Optional[str] = None

    processing_time_seconds: float = 0.0


class SearchQuery(BaseModel):
    """
    Query de busca RAG
    """

    query: str = Field(..., min_length=3, description="Tema ou descrição")

    # Filtros opcionais
    categorias: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    min_intensity: Optional[float] = Field(None, ge=0.0, le=10.0)
    min_viral_potential: Optional[float] = Field(None, ge=0.0, le=10.0)
    emotional_tones: Optional[List[str]] = None

    # Parâmetros de busca
    limit: int = Field(30, ge=1, le=100, description="Número de resultados")
    enable_reranking: bool = True
    mmr_lambda: float = Field(0.7, ge=0.0, le=1.0, description="Balance relevância/diversidade")


class ProductionRequest(BaseModel):
    """
    Request para produzir vídeo compilado
    """

    theme: str = Field(..., min_length=5, description="Tema do vídeo")
    target_duration: int = Field(600, ge=60, le=3600, description="Duração alvo (segundos)")
    style: str = Field("energetic", description="Estilo: energetic, chill, emotional")

    # Filtros
    categorias: Optional[List[str]] = None
    tags: Optional[List[str]] = None


# ============================================================================
# STATS MODELS
# ============================================================================

class SystemStats(BaseModel):
    """
    Estatísticas do sistema
    """

    total_clips: int
    analyzed_clips: int
    pending_clips: int
    failed_clips: int

    avg_intensity: Optional[float] = None
    avg_viral_potential: Optional[float] = None

    emotional_tone_distribution: Dict[str, int] = Field(default_factory=dict)
    category_distribution: Dict[str, int] = Field(default_factory=dict)

    most_used_clips: List[ClipSearchResult] = Field(default_factory=list)
    underutilized_clips: List[ClipSearchResult] = Field(default_factory=list)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def clip_to_search_result(clip: VideoClip, score: float = 1.0) -> ClipSearchResult:
    """
    Converte VideoClip (SQLAlchemy) para ClipSearchResult (Pydantic)
    """
    return ClipSearchResult(
        id=clip.id,
        id_origem=clip.id_origem or "",
        score=score,
        descricao_breve=clip.descricao_breve,
        categorias=clip.categorias or [],
        tags=clip.tags or [],
        scene_description=clip.scene_description,
        emotional_tone=clip.emotional_tone,
        intensity=clip.intensity,
        viral_potential=clip.viral_potential,
        duration_seconds=clip.duration_seconds,
        times_used=clip.times_used or 0
    )


# ============================================================================
# TESTE
# ============================================================================

if __name__ == "__main__":
    # Testar modelos Pydantic
    analysis = AnalysisResult(
        scene_description="Skatista tenta manobra em rampa alta",
        visual_elements=["rampa", "skate", "pessoa"],
        key_moments=[
            {"timestamp": 0.0, "event": "preparação"},
            {"timestamp": 2.5, "event": "salto"},
            {"timestamp": 4.0, "event": "queda"}
        ],
        emotional_tone="cômico",
        intensity=8.5,
        surprise_factor=9.0,
        viral_potential=8.0,
        narrative_arc="setup -> escalation -> payoff",
        standalone=True,
        theme_scores={
            "fails": 9.0,
            "sports": 8.0,
            "comedy": 7.5
        }
    )

    print("✅ AnalysisResult válido:")
    print(analysis.model_dump_json(indent=2))
