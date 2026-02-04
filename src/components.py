"""
Componentes UI reutilizaveis para Streamlit.
"""

import base64
from pathlib import Path

import streamlit as st

# Tamanho padrao do player de video
VIDEO_PLAYER_WIDTH = 320
VIDEO_PLAYER_HEIGHT = 180


def video_player(file_path: str, width: int = VIDEO_PLAYER_WIDTH, height: int = VIDEO_PLAYER_HEIGHT) -> None:
    """
    Renderiza player de video customizado sem opcao de download.

    Args:
        file_path: Caminho absoluto ou relativo do arquivo de video.
        width: Largura do player em pixels.
        height: Altura do player em pixels.
    """
    path = Path(file_path).resolve()

    if not path.exists():
        st.warning(f"Video nao encontrado: {path.name}")
        return

    # Detectar mime type
    suffix = path.suffix.lower()
    mime_types = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".ogg": "video/ogg",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
    }
    mime_type = mime_types.get(suffix, "video/mp4")

    # Ler video como base64
    with open(path, "rb") as f:
        video_bytes = f.read()

    video_b64 = base64.b64encode(video_bytes).decode()

    # HTML customizado sem download
    html = f"""
    <video
        width="{width}"
        height="{height}"
        controls
        controlslist="nodownload nofullscreen"
        disablepictureinpicture
        style="border-radius: 8px; background: #000;"
    >
        <source src="data:{mime_type};base64,{video_b64}" type="{mime_type}">
        Seu navegador nao suporta video HTML5.
    </video>
    <style>
        video::-webkit-media-controls-download-button {{
            display: none !important;
        }}
        video::-webkit-media-controls-overflow-menu {{
            display: none !important;
        }}
    </style>
    """

    st.markdown(html, unsafe_allow_html=True)
