"""
DatabaseService - CRUD PostgreSQL para videos.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.models import Video, VideoAnalysis


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
        """Atualiza video com resultados da analise Gemini."""
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

    def set_error(self, video_id: int, error_message: str) -> None:
        """Marca video como falho."""
        with self._session() as session:
            video = session.query(Video).filter(Video.id == video_id).one()
            video.processing_status = "failed"
            video.error_message = error_message
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
