"""
Script de migracao: gera unified embeddings para videos ja analisados.

Uso:
    python scripts/migrate_to_unified.py
"""

import logging
import sys

sys.path.insert(0, ".")

from src.config import settings
from src.services.context_composer import ContextComposer
from src.services.database_service import DatabaseService
from src.services.embedding_service import EmbeddingService
from src.services.qdrant_service import QdrantService

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    logger.info("Iniciando migracao para unified embeddings...")

    # Inicializar servicos
    db = DatabaseService(settings.postgres_url)
    embedding_svc = EmbeddingService(
        api_key=settings.google_api_key,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )
    qdrant = QdrantService(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        collection=settings.qdrant_collection,
        vector_size=settings.embedding_dimensions,
    )
    composer = ContextComposer()

    # Listar videos analisados
    videos = db.list_videos(status="analyzed")
    logger.info(f"Encontrados {len(videos)} videos analisados")

    success = 0
    skipped = 0
    failed = 0

    for video in videos:
        try:
            # Pular se ja tem unified embedding
            if video.unified_embedding_id:
                logger.info(f"[SKIP] Video {video.id} ({video.filename}) ja tem unified embedding")
                skipped += 1
                continue

            # Compor texto
            composed_text = composer.compose_embedding_text(video)
            if not composed_text:
                logger.warning(f"[SKIP] Video {video.id} ({video.filename}) sem texto para embedding")
                skipped += 1
                continue

            # Gerar embedding
            unified_emb = embedding_svc.generate_unified(composed_text)

            # Payload para Qdrant
            payload = {
                "video_id": video.id,
                "filename": video.filename,
                "category": video.category,
                "emotional_tone": video.emotional_tone,
                "intensity": video.intensity,
                "viral_potential": video.viral_potential,
                "is_exclusive": video.is_exclusive or False,
                "source": video.source or "local",
            }

            # Indexar
            emb_id = qdrant.index_unified(video.id, unified_emb, payload)
            db.update_unified_embedding(video.id, emb_id)

            success += 1
            logger.info(f"[OK] Video {video.id} ({video.filename}) - unified embedding criado")

        except Exception as e:
            failed += 1
            logger.error(f"[FAIL] Video {video.id} ({video.filename}): {e}")

    logger.info(f"Migracao concluida: {success} sucesso, {skipped} pulados, {failed} falhas")


if __name__ == "__main__":
    main()
