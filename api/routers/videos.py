"""
Router de videos - ingest, metadata, context.
"""

import logging
import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from api.dependencies import (
    get_composer,
    get_db,
    get_embedding,
    get_qdrant,
    get_queue,
    verify_api_key,
)
from api.schemas.requests import NewsflareMetadata
from api.schemas.responses import (
    DeleteResponse,
    IngestResponse,
    MetadataUpdateResponse,
    VideoContext,
    VideoListResponse,
    VideoSummary,
)
from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["videos"], dependencies=[Depends(verify_api_key)])


@router.get("", response_model=VideoListResponse)
def list_videos(
    status: str = None,
    db=Depends(get_db),
):
    """Lista todos os videos, opcionalmente filtrados por status."""
    videos = db.list_videos(status=status)
    return VideoListResponse(
        total=len(videos),
        videos=[VideoSummary.model_validate(v) for v in videos],
    )


@router.post("/ingest", response_model=IngestResponse)
def ingest_video(
    file: UploadFile = File(...),
    metadata: str = Form(default="{}"),
    db=Depends(get_db),
    queue=Depends(get_queue),
):
    """
    Ingesta um video: salva em uploads/, cria registro no DB, enfileira para processamento.
    Metadata JSON opcional via form field.
    """
    import json

    # Validar arquivo
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Parse metadata
    try:
        meta_dict = json.loads(metadata)
        meta = NewsflareMetadata(**meta_dict) if meta_dict else None
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid metadata JSON: {e}")

    # Salvar arquivo
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Evitar nome duplicado
    dest_path = upload_dir / file.filename
    if dest_path.exists():
        stem = dest_path.stem
        suffix = dest_path.suffix
        counter = 1
        while dest_path.exists():
            dest_path = upload_dir / f"{stem}_{counter}{suffix}"
            counter += 1

    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    file_size = os.path.getsize(dest_path)

    # Criar registro no DB
    video = db.create_video(
        filename=file.filename,
        file_path=str(dest_path),
        file_size=file_size,
        mime_type=file.content_type,
    )

    # Aplicar metadata se fornecida
    if meta and meta.newsflare_id:
        meta_update = {}
        if meta.newsflare_id:
            meta_update["newsflare_id"] = meta.newsflare_id
        if meta.description:
            meta_update["source_description"] = meta.description
        if meta.uploader:
            meta_update["uploader"] = meta.uploader
        if meta.filming_date:
            meta_update["event_date"] = meta.filming_date
        if meta.filming_location:
            meta_update["filming_location"] = meta.filming_location
        if meta.is_exclusive is not None:
            meta_update["is_exclusive"] = meta.is_exclusive
        if meta.category:
            meta_update["category"] = meta.category
        if meta.tags:
            meta_update["source_tags"] = meta.tags
        if meta.license_type:
            meta_update["license_type"] = meta.license_type
        if meta.extra:
            meta_update["newsflare_metadata"] = meta.extra
        meta_update["source"] = "newsflare"
        db.update_source_metadata(video.id, meta_update)

    # Enfileirar para processamento
    queue_id = queue.enqueue(video.id)

    return IngestResponse(
        video_id=video.id,
        filename=file.filename,
        status="pending",
        queued=queue_id is not None,
        message="Video ingested and queued for processing",
    )


@router.post("/{video_id}/metadata", response_model=MetadataUpdateResponse)
def update_metadata(
    video_id: int,
    metadata: NewsflareMetadata,
    db=Depends(get_db),
    composer=Depends(get_composer),
    embedding_svc=Depends(get_embedding),
    qdrant=Depends(get_qdrant),
):
    """
    Atualiza metadata de fonte de um video.
    Se video ja esta analyzed, re-gera unified embedding.
    """
    video = db.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Montar update dict
    meta_update = {}
    if metadata.newsflare_id:
        meta_update["newsflare_id"] = metadata.newsflare_id
    if metadata.description:
        meta_update["source_description"] = metadata.description
    if metadata.uploader:
        meta_update["uploader"] = metadata.uploader
    if metadata.filming_date:
        meta_update["event_date"] = metadata.filming_date
    if metadata.filming_location:
        meta_update["filming_location"] = metadata.filming_location
    if metadata.is_exclusive is not None:
        meta_update["is_exclusive"] = metadata.is_exclusive
    if metadata.category:
        meta_update["category"] = metadata.category
    if metadata.tags:
        meta_update["source_tags"] = metadata.tags
    if metadata.license_type:
        meta_update["license_type"] = metadata.license_type
    if metadata.extra:
        meta_update["newsflare_metadata"] = metadata.extra
    meta_update["source"] = "newsflare"

    db.update_source_metadata(video_id, meta_update)

    # Re-gerar unified embedding se video ja foi analisado
    regenerated = False
    if video.processing_status == "analyzed":
        try:
            updated_video = db.get_video(video_id)
            composed_text = composer.compose_embedding_text(updated_video)
            if composed_text:
                unified_emb = embedding_svc.generate_unified(composed_text)
                payload = {
                    "video_id": video_id,
                    "filename": updated_video.filename,
                    "category": updated_video.category,
                    "emotional_tone": updated_video.emotional_tone,
                    "intensity": updated_video.intensity,
                    "viral_potential": updated_video.viral_potential,
                    "is_exclusive": updated_video.is_exclusive or False,
                    "source": updated_video.source or "local",
                }
                emb_id = qdrant.index_unified(video_id, unified_emb, payload)
                db.update_unified_embedding(video_id, emb_id)
                regenerated = True
        except Exception as e:
            logger.warning(f"Failed to regenerate unified embedding for video {video_id}: {e}")

    return MetadataUpdateResponse(
        video_id=video_id,
        updated=True,
        unified_embedding_regenerated=regenerated,
        message="Metadata updated successfully",
    )


@router.get("/{video_id}/context", response_model=VideoContext)
def get_video_context(
    video_id: int,
    db=Depends(get_db),
):
    """Retorna contexto completo de um video."""
    video = db.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return VideoContext.model_validate(video)


@router.delete("/{video_id}", response_model=DeleteResponse)
def delete_video(
    video_id: int,
    db=Depends(get_db),
    qdrant=Depends(get_qdrant),
):
    """Remove video do sistema: DB, Qdrant e arquivo em disco."""
    video = db.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    filename = video.filename

    # Remove do Qdrant (todas as collections)
    qdrant.delete(video_id)

    # Remove arquivo do disco
    if video.file_path:
        file_path = Path(video.file_path)
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete file {file_path}: {e}")

    # Remove do banco
    db.delete_video(video_id)

    return DeleteResponse(
        video_id=video_id,
        deleted=True,
        message=f"Video '{filename}' deleted successfully",
    )


@router.post("/{video_id}/retry")
def retry_video(
    video_id: int,
    db=Depends(get_db),
    queue=Depends(get_queue),
):
    """Reenfileira video falho para nova tentativa de processamento."""
    video = db.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.processing_status == "analyzing":
        raise HTTPException(status_code=400, detail="Video is currently being analyzed")

    # Reset video status
    db.reset_to_pending(video_id)

    # Retry in queue or enqueue fresh
    retried = queue.retry(video_id)
    if not retried:
        queue.enqueue(video_id)

    return {"video_id": video_id, "status": "pending", "message": "Video queued for reprocessing"}
