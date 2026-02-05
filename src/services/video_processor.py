"""
VideoProcessor - Logica de processamento de video extraida para uso com fila.
Suporta analise dual (visual + narrativa) com embeddings separados.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from src.models import VideoAnalysis, DualVideoAnalysis
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
    analysis: Optional[DualVideoAnalysis] = None
    visual_embedding_id: Optional[str] = None
    narrative_embedding_id: Optional[str] = None
    error: Optional[str] = None


class VideoProcessor:
    """
    Processador de videos que coordena:
    1. Analise Gemini DUAL (visual + narrativa)
    2. Geracao de embeddings duplos
    3. Indexacao no Qdrant (collection dual)
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
        Processa um video da fila com analise DUAL.

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
            logger.info(f"Iniciando analise DUAL do video {video_id}: {video.filename}")

            # 3. Analise Gemini DUAL (visual + narrativa)
            logger.info(f"Enviando video {video_id} para Gemini (analise dual)...")
            dual_analysis = self.gemini.analyze_video_dual(video.file_path)
            logger.info(f"Analise dual concluida para video {video_id}")

            # 4. Gerar embeddings duplos
            logger.info(f"Gerando embeddings duplos para video {video_id}...")
            dual_embeddings = self.embedding.generate_dual(dual_analysis)
            logger.info(f"Embeddings duplos gerados para video {video_id}")

            # 5. Indexar no Qdrant (collection dual)
            logger.info(f"Indexando video {video_id} no Qdrant (dual)...")
            payload = {
                "video_id": video_id,
                "filename": video.filename,
                # Visual
                "visual_description": dual_analysis.visual.visual_description,
                "visual_tags": dual_analysis.visual.visual_tags,
                "objects_detected": dual_analysis.visual.objects_detected,
                "visual_style": dual_analysis.visual.visual_style,
                "color_palette": dual_analysis.visual.color_palette,
                # Narrativa
                "narrative_description": dual_analysis.narrative.narrative_description,
                "narrative_tags": dual_analysis.narrative.narrative_tags,
                "emotional_tone": dual_analysis.narrative.emotional_tone,
                "intensity": dual_analysis.narrative.intensity,
                "viral_potential": dual_analysis.narrative.viral_potential,
                "themes": dual_analysis.narrative.themes,
                "target_audience": dual_analysis.narrative.target_audience,
            }
            visual_id, narrative_id = self.qdrant.index_dual(
                video_id,
                dual_embeddings.visual,
                dual_embeddings.narrative,
                payload,
            )
            logger.info(f"Video {video_id} indexado no Qdrant (dual)")

            # 6. Atualizar PostgreSQL
            self.db.update_dual_analysis(video_id, dual_analysis, visual_id, narrative_id)
            logger.info(f"Video {video_id} processado com sucesso (dual)")

            return ProcessingResult(
                success=True,
                video_id=video_id,
                analysis=dual_analysis,
                visual_embedding_id=visual_id,
                narrative_embedding_id=narrative_id,
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
