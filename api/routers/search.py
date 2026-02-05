"""
Router de busca semantica.
"""

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_db, get_embedding, get_qdrant, verify_api_key
from api.schemas.requests import SearchRequest, SimilarRequest
from api.schemas.responses import SearchHit, SearchResponse

router = APIRouter(prefix="/search", tags=["search"], dependencies=[Depends(verify_api_key)])


@router.post("", response_model=SearchResponse)
def search_videos(
    request: SearchRequest,
    embedding_svc=Depends(get_embedding),
    qdrant=Depends(get_qdrant),
):
    """Busca semantica na collection unificada com filtros opcionais."""
    # Gerar embedding da query
    query_embedding = embedding_svc.generate(request.query)

    # Montar filtros
    filters = None
    if request.filters:
        filters = request.filters.model_dump(exclude_none=True)

    # Buscar no Qdrant
    results = qdrant.search_unified(
        query_embedding=query_embedding,
        limit=request.limit,
        filters=filters if filters else None,
    )

    hits = []
    for r in results:
        payload = r.get("payload", {})
        hits.append(
            SearchHit(
                id=r["id"],
                filename=payload.get("filename"),
                score=r["score"],
                category=payload.get("category"),
                emotional_tone=payload.get("emotional_tone"),
                intensity=payload.get("intensity"),
                viral_potential=payload.get("viral_potential"),
                is_exclusive=payload.get("is_exclusive"),
                source=payload.get("source"),
            )
        )

    return SearchResponse(
        query=request.query,
        total_results=len(hits),
        results=hits,
    )


@router.post("/similar/{video_id}", response_model=SearchResponse)
def find_similar_videos(
    video_id: int,
    request: SimilarRequest = SimilarRequest(),
    qdrant=Depends(get_qdrant),
    db=Depends(get_db),
):
    """Busca videos similares a um dado video."""
    video = db.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    results = qdrant.find_similar(video_id=video_id, limit=request.limit)

    hits = []
    for r in results:
        payload = r.get("payload", {})
        hits.append(
            SearchHit(
                id=r["id"],
                filename=payload.get("filename"),
                score=r["score"],
                category=payload.get("category"),
                emotional_tone=payload.get("emotional_tone"),
                intensity=payload.get("intensity"),
                viral_potential=payload.get("viral_potential"),
                is_exclusive=payload.get("is_exclusive"),
                source=payload.get("source"),
            )
        )

    return SearchResponse(
        query=f"Similar to video {video_id} ({video.filename})",
        total_results=len(hits),
        results=hits,
    )
