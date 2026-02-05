"""
Router de RAG - busca + geracao de resposta.
"""

import logging

from fastapi import APIRouter, Depends

from api.dependencies import (
    get_composer,
    get_db,
    get_embedding,
    get_gemini,
    get_qdrant,
    verify_api_key,
)
from api.schemas.requests import RAGQueryRequest
from api.schemas.responses import RAGResponse, RAGSource

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"], dependencies=[Depends(verify_api_key)])


@router.post("/query", response_model=RAGResponse)
def rag_query(
    request: RAGQueryRequest,
    embedding_svc=Depends(get_embedding),
    qdrant=Depends(get_qdrant),
    db=Depends(get_db),
    gemini=Depends(get_gemini),
    composer=Depends(get_composer),
):
    """
    Query RAG: busca semantica + geracao de resposta via Gemini.
    Suporta modo textual e modo com video direto.
    """
    # 1. Gerar embedding da query
    query_embedding = embedding_svc.generate(request.query)

    # 2. Buscar na collection unificada
    filters = None
    if request.filters:
        filters = request.filters.model_dump(exclude_none=True)

    search_results = qdrant.search_unified(
        query_embedding=query_embedding,
        limit=request.limit,
        filters=filters if filters else None,
    )

    if not search_results:
        return RAGResponse(
            query=request.query,
            answer="Nenhum video encontrado para esta busca.",
            sources=[],
            model_used=gemini.model,
        )

    # 3. Buscar videos completos do DB
    video_ids = [r["id"] for r in search_results]
    videos_dict = db.get_videos_by_ids_dict(video_ids)

    # 4. Montar contexto para RAG
    sources = []
    clips_context = []

    for r in search_results:
        video = videos_dict.get(r["id"])
        if not video:
            continue

        context = composer.compose_rag_context(video, score=r["score"])
        clips_context.append(context)

        sources.append(
            RAGSource(
                video_id=video.id,
                filename=video.filename,
                score=r["score"],
                category=video.category,
                emotional_tone=video.emotional_tone,
            )
        )

    # 5. Gerar resposta
    if request.include_video_analysis:
        # Modo com video: enviar videos diretamente para Gemini
        video_paths = [
            videos_dict[r["id"]].file_path
            for r in search_results
            if r["id"] in videos_dict and videos_dict[r["id"]].file_path
        ]
        answer = gemini.generate_rag_response_with_videos(
            query=request.query,
            video_paths=video_paths,
            max_videos=request.max_videos_for_analysis,
        )
        model_used = gemini.fast_model
    else:
        # Modo textual: usar contexto dos videos
        answer = gemini.generate_rag_response(
            query=request.query,
            clips_context=clips_context,
        )
        model_used = gemini.model

    return RAGResponse(
        query=request.query,
        answer=answer,
        sources=sources,
        model_used=model_used,
    )
