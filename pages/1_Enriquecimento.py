"""
Pagina de Enriquecimento - Upload e analise de videos com Gemini.
Usa fila de processamento em background para nao bloquear a UI.
"""

from pathlib import Path

import streamlit as st

from src.config import settings
from src.components import (
    video_player,
    video_thumbnail,
    pagination_controls,
    queue_dashboard,
    queue_status_badge,
    calculate_total_pages,
)
from src.services.database_service import DatabaseService
from src.services.queue_service import QueueService


# ============================================================================
# Constantes
# ============================================================================

VIDEOS_PER_PAGE = 10
AUTO_REFRESH_INTERVAL = 5  # segundos


# ============================================================================
# Inicializacao de servicos (cached)
# ============================================================================


@st.cache_resource
def get_db_service():
    return DatabaseService(settings.postgres_url)


@st.cache_resource
def get_queue_service():
    return QueueService(settings.postgres_url)


# ============================================================================
# Layout
# ============================================================================

st.title("Enriquecimento de Videos")
st.markdown("Upload de videos para analise automatica com Gemini.")

# Verificar API key
if not settings.google_api_key:
    st.error("GOOGLE_API_KEY nao configurada. Edite o arquivo .env na raiz do projeto.")
    st.stop()

# ============================================================================
# Dashboard de Status da Fila
# ============================================================================

try:
    queue = get_queue_service()
    stats = queue.get_stats()

    st.subheader("Status do Processamento")
    queue_dashboard(
        pending=stats.pending,
        processing=stats.processing,
        completed=stats.completed,
        failed=stats.failed,
    )

    # Auto-refresh se houver itens pendentes ou em processamento
    if stats.pending > 0 or stats.processing > 0:
        st.caption(
            f"Processamento em andamento. "
            f"Clique em 'Atualizar' para ver o status mais recente."
        )
        if st.button("Atualizar Status", key="refresh_queue"):
            st.rerun()

except Exception as e:
    st.warning(f"Nao foi possivel conectar a fila: {e}")

st.divider()

# ============================================================================
# Upload
# ============================================================================

st.subheader("Upload de Video")

uploaded_file = st.file_uploader(
    "Selecione um video",
    type=["mp4", "avi", "mov", "mkv", "webm"],
    help=f"Tamanho maximo: {settings.max_video_size_mb} MB",
)

if uploaded_file is not None:
    # Validar tamanho
    file_size = uploaded_file.size
    max_bytes = settings.max_video_size_mb * 1024 * 1024

    if file_size > max_bytes:
        st.error(
            f"Arquivo muito grande ({file_size / (1024*1024):.1f} MB). "
            f"Maximo permitido: {settings.max_video_size_mb} MB."
        )
        st.stop()

    # Salvar em uploads/
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / uploaded_file.name

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Mostrar preview do video
    with st.expander("Preview do video", expanded=True):
        video_player(str(file_path))

    st.markdown(
        f"**Arquivo:** {uploaded_file.name} "
        f"({file_size / (1024*1024):.1f} MB)"
    )

    # Botao de enfileirar para analise
    if st.button("Enfileirar para Analise", type="primary"):
        db = get_db_service()
        queue = get_queue_service()

        # Criar registro no banco
        video = db.create_video(
            filename=uploaded_file.name,
            file_path=str(file_path),
            file_size=file_size,
            mime_type=uploaded_file.type,
        )

        # Adicionar a fila
        queue_id = queue.enqueue(video.id)

        if queue_id:
            st.success(
                f"Video '{uploaded_file.name}' adicionado a fila de processamento! "
                f"O processamento ocorrera em background."
            )
            st.info(
                "Voce pode continuar usando o sistema normalmente. "
                "O status sera atualizado automaticamente."
            )
            # Limpar uploader e recarregar
            st.rerun()
        else:
            st.warning("Este video ja esta na fila de processamento.")

# ============================================================================
# Lista de videos com paginacao
# ============================================================================

st.divider()
st.subheader("Videos no Acervo")

# Controle de pagina no session_state
if "videos_page" not in st.session_state:
    st.session_state.videos_page = 1

try:
    db = get_db_service()

    # Buscar videos com paginacao
    videos, total = db.list_videos_paginated(
        page=st.session_state.videos_page,
        per_page=VIDEOS_PER_PAGE,
    )
    total_pages = calculate_total_pages(total, VIDEOS_PER_PAGE)

    if not videos:
        st.info("Nenhum video no acervo ainda. Faca upload acima.")
    else:
        st.caption(f"Mostrando {len(videos)} de {total} videos")

        # Controles de paginacao no topo
        new_page = pagination_controls(
            page=st.session_state.videos_page,
            total_pages=total_pages,
            key_prefix="videos_top",
        )
        if new_page != st.session_state.videos_page:
            st.session_state.videos_page = new_page
            st.rerun()

        # Lista de videos
        for video in videos:
            status_badge = queue_status_badge(video.processing_status)

            with st.expander(
                f"{status_badge} - {video.filename}",
                expanded=False,
            ):
                col1, col2 = st.columns([1, 2])

                with col1:
                    # Usar thumbnail em vez de player completo
                    if video.file_path:
                        video_thumbnail(
                            file_path=video.file_path,
                            video_id=video.id,
                            filename=video.filename,
                        )

                with col2:
                    # Info basica
                    if video.file_size_bytes:
                        size_mb = video.file_size_bytes / (1024 * 1024)
                        st.caption(f"Tamanho: {size_mb:.1f} MB")

                    if video.duration_seconds:
                        mins = int(video.duration_seconds // 60)
                        secs = int(video.duration_seconds % 60)
                        st.caption(f"Duracao: {mins}:{secs:02d}")

                    # Status de processamento
                    if video.processing_status == "pending":
                        st.info("Aguardando processamento na fila...")

                    elif video.processing_status == "analyzing":
                        st.info("Processamento em andamento...")

                    elif video.processing_status == "analyzed":
                        # Mostrar resultados da analise
                        if video.analysis_description:
                            st.write(video.analysis_description)

                        if video.tags:
                            st.write("**Tags:** " + ", ".join(video.tags))

                        if video.emotional_tone:
                            st.write(f"**Tom:** {video.emotional_tone}")

                        # Metricas em colunas
                        if video.intensity is not None or video.viral_potential is not None:
                            m1, m2 = st.columns(2)
                            with m1:
                                if video.intensity is not None:
                                    st.metric("Intensidade", f"{video.intensity:.1f}/10")
                            with m2:
                                if video.viral_potential is not None:
                                    st.metric("Potencial Viral", f"{video.viral_potential:.1f}/10")

                        # Temas
                        if video.themes:
                            with st.expander("Temas detectados"):
                                for theme, score in sorted(
                                    video.themes.items(),
                                    key=lambda x: x[1],
                                    reverse=True,
                                ):
                                    st.progress(score / 10, text=f"{theme}: {score:.1f}")

                    elif video.processing_status == "failed":
                        st.error(f"Erro: {video.error_message or 'Erro desconhecido'}")

                        # Botao para reprocessar
                        if st.button(
                            "Tentar Novamente",
                            key=f"retry_{video.id}",
                        ):
                            queue = get_queue_service()
                            queue.retry(video.id)
                            st.success("Video reenfileirado para processamento!")
                            st.rerun()

        # Controles de paginacao no rodape
        if total_pages > 1:
            st.divider()
            new_page_bottom = pagination_controls(
                page=st.session_state.videos_page,
                total_pages=total_pages,
                key_prefix="videos_bottom",
            )
            if new_page_bottom != st.session_state.videos_page:
                st.session_state.videos_page = new_page_bottom
                st.rerun()

except Exception as e:
    st.warning(f"Nao foi possivel conectar ao banco de dados: {e}")

# ============================================================================
# Fila de Processamento (detalhes)
# ============================================================================

with st.expander("Detalhes da Fila de Processamento"):
    try:
        queue = get_queue_service()

        # Itens pendentes
        pending_items = queue.get_queue_items(status="pending", limit=10)
        if pending_items:
            st.markdown("**Pendentes:**")
            for item in pending_items:
                st.caption(
                    f"- Video #{item.video_id} "
                    f"(prioridade: {item.priority}, tentativas: {item.attempts})"
                )

        # Itens em processamento
        processing_items = queue.get_queue_items(status="processing", limit=5)
        if processing_items:
            st.markdown("**Em processamento:**")
            for item in processing_items:
                st.caption(
                    f"- Video #{item.video_id} "
                    f"(tentativa {item.attempts}/{item.max_attempts})"
                )

        # Itens com falha
        failed_items = queue.get_queue_items(status="failed", limit=5)
        if failed_items:
            st.markdown("**Falhas recentes:**")
            for item in failed_items:
                st.caption(
                    f"- Video #{item.video_id}: {item.error_message or 'Erro desconhecido'}"
                )

        if not pending_items and not processing_items and not failed_items:
            st.caption("Fila vazia - todos os videos foram processados!")

    except Exception as e:
        st.caption(f"Erro ao carregar fila: {e}")
