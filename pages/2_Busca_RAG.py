"""
Pagina de Busca RAG - Busca semantica de videos com interface chat.
Suporta busca DUAL (visual + narrativa) com pesos configuraveis.
"""

import streamlit as st

from src.config import settings
from src.components import video_player, video_thumbnail
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


def _display_results(results: list[dict], show_dual_scores: bool = False):
    """Renderiza lista de videos encontrados."""
    if not results:
        return

    for i, r in enumerate(results):
        # Montar label com scores
        score_label = f"relevancia: {r.get('score', r.get('combined_score', 0)):.2f}"
        if show_dual_scores and "visual_score" in r and "narrative_score" in r:
            score_label = (
                f"visual: {r['visual_score']:.2f} | "
                f"narrativa: {r['narrative_score']:.2f} | "
                f"combinado: {r.get('combined_score', 0):.2f}"
            )

        with st.expander(
            f"#{i+1} - {r.get('filename', 'N/A')} ({score_label})",
            expanded=(i < 3),
        ):
            col1, col2 = st.columns([1, 2])
            with col1:
                file_path = r.get("file_path")
                if file_path:
                    video_thumbnail(
                        file_path=file_path,
                        video_id=r.get("id", i),
                        filename=r.get("filename", "video"),
                    )

            with col2:
                # Mostrar descricoes visuais e narrativas se disponiveis
                if r.get("visual_description"):
                    st.markdown("**Analise Visual:**")
                    st.write(r["visual_description"])

                if r.get("narrative_description"):
                    st.markdown("**Analise Narrativa:**")
                    st.write(r["narrative_description"])

                # Fallback para descricao combinada
                if not r.get("visual_description") and not r.get("narrative_description"):
                    if r.get("analysis_description"):
                        st.write(r["analysis_description"])

                # Tags (combinar visual e narrativa)
                all_tags = []
                if r.get("visual_tags"):
                    all_tags.extend(r["visual_tags"][:5])
                if r.get("narrative_tags"):
                    all_tags.extend(r["narrative_tags"][:5])
                if not all_tags and r.get("tags"):
                    all_tags = r["tags"][:10]

                if all_tags:
                    st.write("**Tags:** " + ", ".join(all_tags))

                # Metricas
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

                # Info adicional do dual
                if r.get("visual_style"):
                    st.caption(f"Estilo visual: {r['visual_style']}")
                if r.get("target_audience"):
                    st.caption(f"Publico-alvo: {r['target_audience']}")


# ============================================================================
# Layout
# ============================================================================

st.title("Busca Inteligente de Videos")
st.markdown("Busca semantica DUAL (visual + narrativa) com respostas geradas por IA.")

# Verificar API key
if not settings.google_api_key:
    st.error("GOOGLE_API_KEY nao configurada. Edite o arquivo .env na raiz do projeto.")
    st.stop()

# ============================================================================
# Configuracoes na sidebar
# ============================================================================

with st.sidebar:
    st.subheader("Configuracoes de Busca")

    # Pesos para busca dual
    st.markdown("**Pesos da Busca Dual**")
    visual_weight = st.slider(
        "Peso Visual",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.1,
        help="Peso para similaridade visual (objetos, cenas, cores)",
    )
    narrative_weight = 1.0 - visual_weight
    st.caption(f"Peso Narrativa: {narrative_weight:.1f}")

    st.divider()

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
            _display_results(msg["results"], show_dual_scores=True)

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
            with st.spinner("Buscando videos relevantes (busca dual)..."):
                query_embedding = embedding_svc.generate(query)

            # 2. Buscar no Qdrant (DUAL - visual + narrativa)
            dual_results = qdrant.search_dual(
                query_embedding,
                limit=20,
                visual_weight=visual_weight,
                narrative_weight=narrative_weight,
            )

            if not dual_results:
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
                video_ids = [hit.id for hit in dual_results]

                # Buscar todos os videos de uma vez (evita N+1 queries)
                videos_dict = db.get_videos_by_ids_dict(video_ids)

                for hit in dual_results:
                    payload = hit.payload
                    video_id = payload.get("video_id", hit.id)

                    clip_info = {
                        "id": video_id,
                        "filename": payload.get("filename", "N/A"),
                        "score": hit.combined_score,
                        "visual_score": hit.visual_score,
                        "narrative_score": hit.narrative_score,
                        "combined_score": hit.combined_score,
                        # Visual
                        "visual_description": payload.get("visual_description", ""),
                        "visual_tags": payload.get("visual_tags", []),
                        "objects_detected": payload.get("objects_detected", []),
                        "visual_style": payload.get("visual_style", ""),
                        "color_palette": payload.get("color_palette", []),
                        # Narrativa
                        "narrative_description": payload.get("narrative_description", ""),
                        "narrative_tags": payload.get("narrative_tags", []),
                        "emotional_tone": payload.get("emotional_tone", ""),
                        "intensity": payload.get("intensity"),
                        "viral_potential": payload.get("viral_potential"),
                        "themes": payload.get("themes", {}),
                        "target_audience": payload.get("target_audience", ""),
                        # Legado
                        "analysis_description": payload.get("analysis_description", ""),
                        "tags": payload.get("tags", []),
                    }
                    clips_context.append(clip_info)

                    # Buscar file_path do dicionario (sem query adicional)
                    result_display = dict(clip_info)
                    video = videos_dict.get(video_id)
                    if video:
                        result_display["file_path"] = video.file_path
                        result_display["duration_seconds"] = video.duration_seconds
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
                        f"Analisando {min(len(video_paths), max_videos)} video(s) com Gemini..."
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

                # Info sobre a busca
                st.caption(
                    f"Busca dual: visual={visual_weight:.0%}, narrativa={narrative_weight:.0%}"
                )

                # 6. Mostrar videos
                _display_results(results_display, show_dual_scores=True)

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
