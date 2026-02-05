"""
Router de estatisticas.
"""

from fastapi import APIRouter, Depends

from api.dependencies import get_db, get_qdrant, get_queue, verify_api_key
from api.schemas.responses import StatsResponse

router = APIRouter(prefix="/stats", tags=["stats"], dependencies=[Depends(verify_api_key)])


@router.get("", response_model=StatsResponse)
def get_stats(
    db=Depends(get_db),
    queue=Depends(get_queue),
    qdrant=Depends(get_qdrant),
):
    """Retorna estatisticas completas do sistema."""
    db_stats = db.get_stats()
    queue_stats = queue.get_stats()
    qdrant_stats = qdrant.get_collection_stats()

    return StatsResponse(
        videos_total=db_stats["total"],
        videos_analyzed=db_stats["analyzed"],
        videos_pending=db_stats["pending"],
        videos_failed=db_stats["failed"],
        videos_with_metadata=db.count_with_metadata(),
        videos_with_unified_embedding=db.count_with_unified_embedding(),
        queue_pending=queue_stats.pending,
        queue_processing=queue_stats.processing,
        queue_completed=queue_stats.completed,
        queue_failed=queue_stats.failed,
        qdrant_collections=qdrant_stats,
    )
