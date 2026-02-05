"""
VideoProcessor - Logica de processamento de video extraida para uso com fila.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from src.models import VideoAnalysis
from src.services.database_service import DatabaseService
from src.services.embedding_service import EmbeddingService
from src.services.gemini_service import GeminiService
from src.services.qdrant_service import QdrantService
from src.services.queue_service import QueueTask

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Resultado do processamento de um video."""

    success: bool
    video_id: int
    analysis: Optional[VideoAnalysis] = None
    embedding_id: Optional[str] = None
    error: Optional[str] = None


class VideoProcessor:
    """
    Processador de videos que coordena:
    1. Analise Gemini
    2. Geracao de embedding
    3. Indexacao no Qdrant
    4. Atualizacao no PostgreSQL
    """

    def __init__(
        self,
        db_service: DatabaseService,
        gemini_service: GeminiService,
        embedding_service: EmbeddingService,
        qdrant_service: QdrantService,
    ):
        self.db = db_service
        self.gemini = gemini_service
        self.embedding = embedding_service
        self.qdrant = qdrant_service

    def process(self, task: QueueTask) -> ProcessingResult:
        """
        Processa um video da fila.

        Args:
            task: Item da fila com video_id

        Returns:
            ProcessingResult com status do processamento
        """
        video_id = task.video_id

        try:
            # 1. Buscar video no banco
            video = self.db.get_video(video_id)
            if not video:
                return ProcessingResult(
                    success=False,
                    video_id=video_id,
                    error=f"Video {video_id} nao encontrado no banco",
                )

            # 2. Marcar como analyzing
            self.db.set_analyzing(video_id)
            logger.info(f"Iniciando analise do video {video_id}: {video.filename}")

            # 3. Analise Gemini
            logger.info(f"Enviando video {video_id} para Gemini...")
            analysis = self.gemini.analyze_video(video.file_path)
            logger.info(f"Analise Gemini concluida para video {video_id}")

            # 4. Gerar embedding
            logger.info(f"Gerando embedding para video {video_id}...")
            embedding = self.embedding.generate_for_video(analysis)
            logger.info(f"Embedding gerado para video {video_id}")

            # 5. Indexar no Qdrant
            logger.info(f"Indexando video {video_id} no Qdrant...")
            payload = {
                "video_id": video_id,
                "filename": video.filename,
                "analysis_description": analysis.description,
                "tags": analysis.tags,
                "emotional_tone": analysis.emotional_tone,
                "intensity": analysis.intensity,
                "viral_potential": analysis.viral_potential,
                "themes": analysis.themes,
            }
            embedding_id = self.qdrant.index(video_id, embedding, payload)
            logger.info(f"Video {video_id} indexado no Qdrant")

            # 6. Atualizar PostgreSQL
            self.db.update_analysis(video_id, analysis, embedding_id)
            logger.info(f"Video {video_id} processado com sucesso")

            return ProcessingResult(
                success=True,
                video_id=video_id,
                analysis=analysis,
                embedding_id=embedding_id,
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Erro processando video {video_id}: {error_msg}")

            # Marcar como erro no banco
            try:
                self.db.set_error(video_id, error_msg)
            except Exception as db_error:
                logger.error(f"Erro ao salvar status de erro: {db_error}")

            return ProcessingResult(
                success=False,
                video_id=video_id,
                error=error_msg,
            )

    def process_video_id(self, video_id: int) -> ProcessingResult:
        """
        Processa um video pelo ID (sem QueueTask).
        Util para processamento direto sem fila.
        """
        dummy_task = QueueTask(
            id=0,
            video_id=video_id,
            status="processing",
            priority=0,
            attempts=1,
            max_attempts=3,
            error_message=None,
            created_at=None,
        )
        return self.process(dummy_task)


def create_processor_callback(
    db_service: DatabaseService,
    gemini_service: GeminiService,
    embedding_service: EmbeddingService,
    qdrant_service: QdrantService,
):
    """
    Cria callback de processamento para uso com QueueService.start_worker().

    Returns:
        Funcao que recebe QueueTask e processa o video
    """
    processor = VideoProcessor(
        db_service=db_service,
        gemini_service=gemini_service,
        embedding_service=embedding_service,
        qdrant_service=qdrant_service,
    )

    def process_callback(task: QueueTask) -> None:
        result = processor.process(task)
        if not result.success:
            # Levantar excecao para que o QueueService marque como falha
            raise RuntimeError(result.error or "Erro desconhecido no processamento")

    return process_callback
