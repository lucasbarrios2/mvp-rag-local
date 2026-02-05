"""
Componentes UI reutilizaveis para Streamlit.
"""

import math
from pathlib import Path
from typing import Callable, Optional

import streamlit as st


def video_player(file_path: str) -> None:
    """
    Renderiza player de video usando o componente nativo do Streamlit.

    Args:
        file_path: Caminho absoluto ou relativo do arquivo de video.
    """
    path = Path(file_path).resolve()

    if not path.exists():
        st.warning(f"Video nao encontrado: {path.name}")
        return

    # Usar o componente nativo do Streamlit (streaming eficiente)
    st.video(str(path))


def video_thumbnail(
    file_path: str,
    video_id: int,
    filename: str,
    expanded: bool = False,
) -> bool:
    """
    Renderiza thumbnail de video com botao para expandir.

    Usa um expander para carregar o video apenas quando clicado,
    evitando carregamento de todos os videos na memoria.

    Args:
        file_path: Caminho do arquivo de video
        video_id: ID do video no banco
        filename: Nome do arquivo para exibir
        expanded: Se deve iniciar expandido

    Returns:
        True se o video foi expandido pelo usuario
    """
    path = Path(file_path).resolve()

    if not path.exists():
        st.caption(f"Video nao encontrado: {filename}")
        return False

    # Usar checkbox como toggle para expandir/colapsar
    key = f"thumb_{video_id}"
    show_video = st.checkbox(
        f"Assistir video",
        value=expanded,
        key=key,
        help="Clique para carregar o player de video",
    )

    if show_video:
        st.video(str(path))
        return True

    # Mostrar placeholder com info do arquivo
    file_size_mb = path.stat().st_size / (1024 * 1024)
    st.caption(f"{file_size_mb:.1f} MB - Clique para assistir")
    return False


def pagination_controls(
    page: int,
    total_pages: int,
    key_prefix: str = "pagination",
) -> int:
    """
    Renderiza controles de paginacao.

    Args:
        page: Pagina atual (1-indexed)
        total_pages: Total de paginas
        key_prefix: Prefixo para keys dos botoes

    Returns:
        Nova pagina selecionada
    """
    if total_pages <= 1:
        return page

    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])

    new_page = page

    with col1:
        if st.button("Primeira", key=f"{key_prefix}_first", disabled=(page == 1)):
            new_page = 1

    with col2:
        if st.button("Anterior", key=f"{key_prefix}_prev", disabled=(page == 1)):
            new_page = page - 1

    with col3:
        st.markdown(
            f"<div style='text-align: center; padding: 8px;'>"
            f"Pagina {page} de {total_pages}"
            f"</div>",
            unsafe_allow_html=True,
        )

    with col4:
        if st.button(
            "Proxima", key=f"{key_prefix}_next", disabled=(page == total_pages)
        ):
            new_page = page + 1

    with col5:
        if st.button(
            "Ultima", key=f"{key_prefix}_last", disabled=(page == total_pages)
        ):
            new_page = total_pages

    return new_page


def queue_status_badge(status: str) -> str:
    """
    Retorna emoji/badge colorido para status da fila.

    Args:
        status: Status do item (pending, processing, completed, failed)

    Returns:
        String com emoji representando o status
    """
    badges = {
        "pending": "🟡 Pendente",
        "processing": "🔵 Processando",
        "completed": "🟢 Concluido",
        "failed": "🔴 Falhou",
        "analyzing": "🔵 Analisando",
        "analyzed": "🟢 Analisado",
    }
    return badges.get(status, f"❓ {status}")


def queue_dashboard(
    pending: int,
    processing: int,
    completed: int,
    failed: int,
) -> None:
    """
    Renderiza dashboard de status da fila.

    Args:
        pending: Quantidade de itens pendentes
        processing: Quantidade em processamento
        completed: Quantidade concluida
        failed: Quantidade com falha
    """
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="🟡 Pendentes",
            value=pending,
            help="Videos aguardando processamento",
        )

    with col2:
        st.metric(
            label="🔵 Processando",
            value=processing,
            help="Videos sendo analisados agora",
        )

    with col3:
        st.metric(
            label="🟢 Concluidos",
            value=completed,
            help="Videos processados com sucesso",
        )

    with col4:
        st.metric(
            label="🔴 Falhas",
            value=failed,
            help="Videos que falharam no processamento",
        )


def calculate_total_pages(total_items: int, per_page: int) -> int:
    """Calcula numero total de paginas."""
    return max(1, math.ceil(total_items / per_page))
