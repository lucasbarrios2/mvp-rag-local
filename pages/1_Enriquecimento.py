"""
Pagina de Enriquecimento - Upload e analise de videos com Gemini.
"""

import os
from pathlib import Path

import streamlit as st

from src.config import settings
from src.services.database_service import DatabaseService
from src.services.embedding_service import EmbeddingService
from src.services.gemini_service import GeminiService
from src.services.qdrant_service import QdrantService


# ============================================================================
# Inicializacao de servicos (cached)
# ============================================================================


@st.cache_resource
def get_db_service():
    return DatabaseService(settings.postgres_url)


@st.cache_resource
def get_gemini_service():
    return GeminiService(settings.google_api_key, settings.gemini_model)


@st.cache_resource
def get_embedding_service():
    return EmbeddingService(
        settings.google_api_key,
        settings.embedding_model,
        settings.embedding_dimensions,
    )


@st.cache_resource
def get_qdrant_service():
    return QdrantService(
        settings.qdrant_host,
        settings.qdrant_port,
        settings.qdrant_collection,
        settings.embedding_dimensions,
    )


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
# Upload
# ============================================================================

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

    # Mostrar player
    st.video(str(file_path))

    st.markdown(
        f"**Arquivo:** {uploaded_file.name} "
        f"({file_size / (1024*1024):.1f} MB)"
    )

    # Botao de analise
    if st.button("Analisar com Gemini", type="primary"):
        db = get_db_service()
        gemini = get_gemini_service()
        embedding_svc = get_embedding_service()
        qdrant = get_qdrant_service()

        # Criar registro no banco
        video = db.create_video(
            filename=uploaded_file.name,
            file_path=str(file_path),
            file_size=file_size,
            mime_type=uploaded_file.type,
        )

        try:
            db.set_analyzing(video.id)

            # Analise Gemini
            with st.spinner("Enviando video para analise Gemini..."):
                analysis = gemini.analyze_video(str(file_path))

            # Gerar embedding
            with st.spinner("Gerando embedding..."):
                embedding = embedding_svc.generate_for_video(analysis)

            # Indexar no Qdrant
            with st.spinner("Indexando no banco vetorial..."):
                payload = {
                    "video_id": video.id,
                    "filename": uploaded_file.name,
                    "analysis_description": analysis.description,
                    "tags": analysis.tags,
                    "emotional_tone": analysis.emotional_tone,
                    "intensity": analysis.intensity,
                    "viral_potential": analysis.viral_potential,
                    "themes": analysis.themes,
                }
                embedding_id = qdrant.index(video.id, embedding, payload)

            # Salvar resultados no PostgreSQL
            db.update_analysis(video.id, analysis, embedding_id)

            # Mostrar resultados
            st.success("Analise concluida!")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Intensidade", f"{analysis.intensity:.1f}/10")
            with col2:
                st.metric("Potencial Viral", f"{analysis.viral_potential:.1f}/10")
            with col3:
                st.metric("Tom Emocional", analysis.emotional_tone)

            st.subheader("Descricao")
            st.write(analysis.description)

            st.subheader("Tags")
            st.write(", ".join(analysis.tags))

            if analysis.themes:
                st.subheader("Temas")
                for theme, score in sorted(
                    analysis.themes.items(), key=lambda x: x[1], reverse=True
                ):
                    st.progress(score / 10, text=f"{theme}: {score:.1f}")

            if analysis.key_moments:
                st.subheader("Momentos-chave")
                for moment in analysis.key_moments:
                    ts = moment.get("timestamp_ms", 0)
                    event = moment.get("event", "")
                    st.write(f"- **{ts/1000:.1f}s** - {event}")

        except Exception as e:
            db.set_error(video.id, str(e))
            st.error(f"Erro na analise: {e}")

# ============================================================================
# Lista de videos ja analisados
# ============================================================================

st.divider()
st.subheader("Videos no acervo")

try:
    db = get_db_service()
    videos = db.list_videos()

    if not videos:
        st.info("Nenhum video no acervo ainda. Faca upload acima.")
    else:
        for video in videos:
            status_emoji = {
                "pending": "⏳",
                "analyzing": "🔄",
                "analyzed": "✅",
                "failed": "❌",
            }.get(video.processing_status, "❓")

            with st.expander(
                f"{status_emoji} {video.filename} - {video.processing_status}"
            ):
                col1, col2 = st.columns([1, 2])
                with col1:
                    if video.file_path and os.path.exists(video.file_path):
                        st.video(video.file_path)
                with col2:
                    if video.analysis_description:
                        st.write(video.analysis_description)
                    if video.tags:
                        st.write(
                            "**Tags:** " + ", ".join(video.tags)
                        )
                    if video.emotional_tone:
                        st.write(f"**Tom:** {video.emotional_tone}")
                    if video.intensity is not None:
                        st.write(f"**Intensidade:** {video.intensity:.1f}/10")
                    if video.viral_potential is not None:
                        st.write(
                            f"**Potencial viral:** {video.viral_potential:.1f}/10"
                        )
                    if video.error_message:
                        st.error(video.error_message)

except Exception as e:
    st.warning(f"Nao foi possivel conectar ao banco de dados: {e}")
