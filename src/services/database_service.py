"""
DatabaseService - CRUD PostgreSQL para videos.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.models import Video, VideoAnalysis, DualVideoAnalysis, FullVideoAnalysis


class DatabaseService:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def _session(self) -> Session:
        return self.SessionLocal()

    def create_video(
        self,
        filename: str,
        file_path: str,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
    ) -> Video:
        """Cria registro inicial do video."""
        with self._session() as session:
            video = Video(
                filename=filename,
                file_path=file_path,
                file_size_bytes=file_size,
                mime_type=mime_type,
                processing_status="pending",
            )
            session.add(video)
            session.commit()
            session.refresh(video)
            return video

    def update_analysis(
        self,
        video_id: int,
        analysis: VideoAnalysis,
        embedding_id: str,
    ) -> Video:
        """Atualiza video com resultados da analise Gemini (legado)."""
        with self._session() as session:
            video = session.query(Video).filter(Video.id == video_id).one()
            video.analysis_description = analysis.description
            video.tags = analysis.tags
            video.emotional_tone = analysis.emotional_tone
            video.intensity = analysis.intensity
            video.viral_potential = analysis.viral_potential
            video.key_moments = analysis.key_moments
            video.themes = analysis.themes
            video.embedding_id = embedding_id
            video.processing_status = "analyzed"
            video.analyzed_at = datetime.utcnow()
            if analysis.duration_estimate:
                video.duration_seconds = analysis.duration_estimate
            session.commit()
            session.refresh(video)
            return video

    def update_dual_analysis(
        self,
        video_id: int,
        analysis: DualVideoAnalysis,
        visual_embedding_id: str,
        narrative_embedding_id: str,
    ) -> Video:
        """Atualiza video com resultados da analise DUAL (visual + narrativa)."""
        with self._session() as session:
            video = session.query(Video).filter(Video.id == video_id).one()

            # Analise VISUAL
            video.visual_description = analysis.visual.visual_description
            video.visual_tags = analysis.visual.visual_tags
            video.objects_detected = analysis.visual.objects_detected
            video.scenes = analysis.visual.scenes
            video.visual_style = analysis.visual.visual_style
            video.color_palette = analysis.visual.color_palette
            video.movement_intensity = analysis.visual.movement_intensity

            # Analise NARRATIVA
            video.narrative_description = analysis.narrative.narrative_description
            video.narrative_tags = analysis.narrative.narrative_tags
            video.emotional_tone = analysis.narrative.emotional_tone
            video.intensity = analysis.narrative.intensity
            video.viral_potential = analysis.narrative.viral_potential
            video.key_moments = analysis.narrative.key_moments
            video.themes = analysis.narrative.themes
            video.storytelling_elements = analysis.narrative.storytelling_elements
            video.target_audience = analysis.narrative.target_audience

            # Campos combinados (legado/compatibilidade)
            video.analysis_description = (
                f"[VISUAL] {analysis.visual.visual_description}\n\n"
                f"[NARRATIVA] {analysis.narrative.narrative_description}"
            )
            video.tags = list(set(
                analysis.visual.visual_tags + analysis.narrative.narrative_tags
            ))

            # Embeddings
            video.visual_embedding_id = visual_embedding_id
            video.narrative_embedding_id = narrative_embedding_id
            video.embedding_id = visual_embedding_id  # Legado

            # Status
            video.processing_status = "analyzed"
            video.analyzed_at = datetime.utcnow()

            if analysis.visual.duration_estimate:
                video.duration_seconds = analysis.visual.duration_estimate

            session.commit()
            session.refresh(video)
            return video

    def update_full_analysis(
        self,
        video_id: int,
        analysis: FullVideoAnalysis,
        visual_embedding_id: str,
        narrative_embedding_id: str,
    ) -> Video:
        """Atualiza video com resultados da analise FULL (visual + narrativa + compilation)."""
        with self._session() as session:
            video = session.query(Video).filter(Video.id == video_id).one()

            # Analise VISUAL
            video.visual_description = analysis.visual.visual_description
            video.visual_tags = analysis.visual.visual_tags
            video.objects_detected = analysis.visual.objects_detected
            video.scenes = analysis.visual.scenes
            video.visual_style = analysis.visual.visual_style
            video.color_palette = analysis.visual.color_palette
            video.movement_intensity = analysis.visual.movement_intensity

            # Analise NARRATIVA
            video.narrative_description = analysis.narrative.narrative_description
            video.narrative_tags = analysis.narrative.narrative_tags
            video.emotional_tone = analysis.narrative.emotional_tone
            video.intensity = analysis.narrative.intensity
            video.viral_potential = analysis.narrative.viral_potential
            video.key_moments = analysis.narrative.key_moments
            video.themes = analysis.narrative.themes
            video.storytelling_elements = analysis.narrative.storytelling_elements
            video.target_audience = analysis.narrative.target_audience

            # Analise COMPILATION
            video.event_headline = analysis.compilation.event_headline
            video.trim_in_ms = analysis.compilation.trim_in_ms
            video.trim_out_ms = analysis.compilation.trim_out_ms
            video.money_shot_ms = analysis.compilation.money_shot_ms
            video.camera_type = analysis.compilation.camera_type
            video.audio_usability = analysis.compilation.audio_usability
            video.audio_usability_reason = analysis.compilation.audio_usability_reason
            video.compilation_themes = analysis.compilation.compilation_themes
            video.narration_suggestion = analysis.compilation.narration_suggestion
            video.location_country = analysis.compilation.location_country
            video.location_environment = analysis.compilation.location_environment
            video.standalone_score = analysis.compilation.standalone_score
            video.visual_quality_score = analysis.compilation.visual_quality_score

            # Campos combinados (legado/compatibilidade)
            video.analysis_description = (
                f"[VISUAL] {analysis.visual.visual_description}\n\n"
                f"[NARRATIVA] {analysis.narrative.narrative_description}"
            )
            video.tags = list(set(
                analysis.visual.visual_tags + analysis.narrative.narrative_tags
            ))

            # Embeddings
            video.visual_embedding_id = visual_embedding_id
            video.narrative_embedding_id = narrative_embedding_id
            video.embedding_id = visual_embedding_id  # Legado

            # Status
            video.processing_status = "analyzed"
            video.analyzed_at = datetime.utcnow()

            if analysis.visual.duration_estimate:
                video.duration_seconds = analysis.visual.duration_estimate

            session.commit()
            session.refresh(video)
            return video

    def set_error(self, video_id: int, error_message: str) -> None:
        """Marca video como falho."""
        with self._session() as session:
            video = session.query(Video).filter(Video.id == video_id).one()
            video.processing_status = "failed"
            video.error_message = error_message
            session.commit()

    def reset_to_pending(self, video_id: int) -> None:
        """Reseta video para pending, limpando erro."""
        with self._session() as session:
            video = session.query(Video).filter(Video.id == video_id).one()
            video.processing_status = "pending"
            video.error_message = None
            session.commit()

    def set_analyzing(self, video_id: int) -> None:
        """Marca video como em analise."""
        with self._session() as session:
            video = session.query(Video).filter(Video.id == video_id).one()
            video.processing_status = "analyzing"
            session.commit()

    def get_video(self, video_id: int) -> Optional[Video]:
        with self._session() as session:
            return session.query(Video).filter(Video.id == video_id).first()

    def get_videos_by_ids(self, ids: list[int]) -> list[Video]:
        with self._session() as session:
            return (
                session.query(Video).filter(Video.id.in_(ids)).all()
            )

    def list_videos(self, status: Optional[str] = None) -> list[Video]:
        with self._session() as session:
            query = session.query(Video).order_by(Video.created_at.desc())
            if status:
                query = query.filter(Video.processing_status == status)
            return query.all()

    def get_stats(self) -> dict:
        with self._session() as session:
            total = session.query(Video).count()
            analyzed = (
                session.query(Video)
                .filter(Video.processing_status == "analyzed")
                .count()
            )
            pending = (
                session.query(Video)
                .filter(Video.processing_status == "pending")
                .count()
            )
            failed = (
                session.query(Video)
                .filter(Video.processing_status == "failed")
                .count()
            )
            return {
                "total": total,
                "analyzed": analyzed,
                "pending": pending,
                "failed": failed,
            }

    def list_videos_paginated(
        self,
        page: int = 1,
        per_page: int = 10,
        status: Optional[str] = None,
    ) -> tuple[list[Video], int]:
        """
        Lista videos com paginacao.

        Args:
            page: Numero da pagina (1-indexed)
            per_page: Itens por pagina
            status: Filtro opcional por status

        Returns:
            Tupla (lista de videos, total de videos)
        """
        with self._session() as session:
            query = session.query(Video).order_by(Video.created_at.desc())
            if status:
                query = query.filter(Video.processing_status == status)

            total = query.count()
            offset = (page - 1) * per_page
            videos = query.offset(offset).limit(per_page).all()

            return videos, total

    def get_videos_by_ids_dict(self, ids: list[int]) -> dict[int, Video]:
        """
        Busca multiplos videos por ID e retorna como dicionario.

        Args:
            ids: Lista de IDs dos videos

        Returns:
            Dicionario {video_id: Video}
        """
        if not ids:
            return {}
        with self._session() as session:
            videos = session.query(Video).filter(Video.id.in_(ids)).all()
            return {v.id: v for v in videos}

    def get_video_by_newsflare_id(self, newsflare_id: str) -> Optional[Video]:
        """Busca video pelo newsflare_id."""
        with self._session() as session:
            return (
                session.query(Video)
                .filter(Video.newsflare_id == newsflare_id)
                .first()
            )

    def delete_video(self, video_id: int) -> bool:
        """Remove video do banco de dados. Retorna True se deletou."""
        with self._session() as session:
            video = session.query(Video).filter(Video.id == video_id).first()
            if not video:
                return False
            session.delete(video)
            session.commit()
            return True

    def update_source_metadata(self, video_id: int, metadata: dict) -> Video:
        """Atualiza metadata de fonte (Newsflare) de um video."""
        with self._session() as session:
            video = session.query(Video).filter(Video.id == video_id).one()
            for key, value in metadata.items():
                if hasattr(video, key) and value is not None:
                    setattr(video, key, value)
            video.source = metadata.get("source", video.source or "local")
            session.commit()
            session.refresh(video)
            return video

    def update_unified_embedding(self, video_id: int, embedding_id: str) -> None:
        """Atualiza o unified_embedding_id de um video."""
        with self._session() as session:
            video = session.query(Video).filter(Video.id == video_id).one()
            video.unified_embedding_id = embedding_id
            session.commit()

    def count_with_metadata(self) -> int:
        """Conta videos que possuem metadata de fonte (newsflare_id preenchido)."""
        with self._session() as session:
            return (
                session.query(Video)
                .filter(Video.newsflare_id.isnot(None))
                .count()
            )

    def count_with_unified_embedding(self) -> int:
        """Conta videos que possuem unified embedding."""
        with self._session() as session:
            return (
                session.query(Video)
                .filter(Video.unified_embedding_id.isnot(None))
                .count()
            )
