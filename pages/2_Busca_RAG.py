"""
Pagina de Busca RAG - Busca semantica de videos com interface chat.
"""

import streamlit as st

from src.config import settings
from src.components import video_player
from src.models import SearchResult, SearchResponse
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
# Funcao auxiliar para mostrar resultados
# ============================================================================


def _display_results(results: list[dict]):
    """Renderiza lista de videos encontrados."""
    if not results:
        return

    for i, r in enumerate(results):
        with st.expander(
            f"#{i+1} - {r.get('filename', 'N/A')} "
            f"(relevancia: {r.get('score', 0):.2f})",
            expanded=(i < 3),
        ):
            col1, col2 = st.columns([1, 2])
            with col1:
                file_path = r.get("file_path")
                if file_path:
                    video_player(file_path)
            with col2:
                if r.get("analysis_description"):
                    st.write(r["analysis_description"])
                if r.get("tags"):
                    st.write("**Tags:** " + ", ".join(r["tags"]))
                metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
                with metrics_col1:
                    if r.get("emotional_tone"):
                        st.write(f"**Tom:** {r['emotional_tone']}")
                with metrics_col2:
                    if r.get("intensity") is not None:
                        st.write(f"**Intensidade:** {r['intensity']:.1f}")
                with metrics_col3:
                    if r.get("viral_potential") is not None:
                        st.write(f"**Viral:** {r['viral_potential']:.1f}")


# ============================================================================
# Layout
# ============================================================================

st.title("Busca Inteligente de Videos")
st.markdown("Busca semantica no acervo com respostas geradas por IA.")

# Verificar API key
if not settings.google_api_key:
    st.error("GOOGLE_API_KEY nao configurada. Edite o arquivo .env na raiz do projeto.")
    st.stop()

# ============================================================================
# Configuracoes na sidebar
# ============================================================================

with st.sidebar:
    st.subheader("Modo de RAG")

    rag_mode = st.radio(
        "Selecione o modo de analise:",
        options=["textual", "video"],
        format_func=lambda x: "Textual (rapido)" if x == "textual" else "Com Video (preciso)",
        index=0,
        help="Textual usa a analise pre-processada. Video envia os arquivos para o Gemini analisar em tempo real.",
    )

    if rag_mode == "video":
        max_videos = st.slider(
            "Max videos a analisar:",
            min_value=1,
            max_value=3,
            value=1,
            help="Mais videos = resposta mais completa, mas mais lenta.",
        )
        st.info(
            f"Tempo estimado: ~{max_videos * 30}-{max_videos * 60}s por video. "
            "Comece com 1 video para testar."
        )
    else:
        max_videos = 3

    st.divider()

    if st.button("Limpar historico"):
        st.session_state.messages = []
        st.rerun()

# ============================================================================
# Historico de chat
# ============================================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar historico
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # Se for resposta do assistant, mostrar videos e modo
        if msg["role"] == "assistant" and "results" in msg:
            mode_label = "video" if msg.get("mode") == "video" else "textual"
            st.caption(f"Modo: {mode_label}")
            _display_results(msg["results"])

# ============================================================================
# Chat input
# ============================================================================

query = st.chat_input("Descreva o tipo de video que procura...")

if query:
    # Mostrar mensagem do usuario
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # Processar busca
    with st.chat_message("assistant"):
        try:
            embedding_svc = get_embedding_service()
            qdrant = get_qdrant_service()
            db = get_db_service()
            gemini = get_gemini_service()

            # 1. Gerar embedding da query
            with st.spinner("Buscando videos relevantes..."):
                query_embedding = embedding_svc.generate(query)

            # 2. Buscar no Qdrant
            qdrant_results = qdrant.search(query_embedding, limit=20)

            if not qdrant_results:
                response_text = (
                    "Nenhum video encontrado para essa busca. "
                    "Tente termos diferentes ou faca upload de mais videos."
                )
                st.markdown(response_text)
                st.session_state.messages.append(
                    {"role": "assistant", "content": response_text}
                )
            else:
                # 3. Montar contexto para RAG
                clips_context = []
                results_display = []

                # Coletar todos os video_ids primeiro
                video_ids = []
                for hit in qdrant_results:
                    payload = hit.get("payload", {})
                    video_id = payload.get("video_id", hit.get("id"))
                    video_ids.append(video_id)

                # Buscar todos os videos de uma vez (evita N+1 queries)
                videos_dict = db.get_videos_by_ids_dict(video_ids)

                for hit in qdrant_results:
                    payload = hit.get("payload", {})
                    video_id = payload.get("video_id", hit.get("id"))

                    clip_info = {
                        "id": video_id,
                        "filename": payload.get("filename", "N/A"),
                        "score": hit.get("score", 0),
                        "analysis_description": payload.get(
                            "analysis_description", ""
                        ),
                        "tags": payload.get("tags", []),
                        "emotional_tone": payload.get("emotional_tone", ""),
                        "intensity": payload.get("intensity"),
                        "viral_potential": payload.get("viral_potential"),
                        "themes": payload.get("themes", {}),
                    }
                    clips_context.append(clip_info)

                    # Buscar file_path do dicionario (sem query adicional)
                    result_display = dict(clip_info)
                    video = videos_dict.get(video_id)
                    if video:
                        result_display["file_path"] = video.file_path
                        result_display["duration_seconds"] = (
                            video.duration_seconds
                        )
                    results_display.append(result_display)

                # 4. Gerar resposta RAG
                if rag_mode == "video":
                    # RAG com video - envia os videos para o Gemini
                    video_paths = [
                        r["file_path"]
                        for r in results_display
                        if r.get("file_path")
                    ]
                    with st.spinner(
                        f"Analisando {min(len(video_paths), max_videos)} video(s) com Gemini... (isso pode levar alguns minutos)"
                    ):
                        rag_response = gemini.generate_rag_response_with_videos(
                            query, video_paths, max_videos=max_videos
                        )
                else:
                    # RAG textual - usa analise pre-processada
                    with st.spinner("Gerando resposta inteligente..."):
                        rag_response = gemini.generate_rag_response(
                            query, clips_context
                        )

                # 5. Mostrar resposta
                st.markdown(rag_response)

                # 6. Mostrar videos
                _display_results(results_display)

                # Salvar no historico
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": rag_response,
                        "results": results_display,
                        "mode": rag_mode,
                    }
                )

        except Exception as e:
            error_msg = f"Erro na busca: {e}"
            st.error(error_msg)
            st.session_state.messages.append(
                {"role": "assistant", "content": error_msg}
            )
