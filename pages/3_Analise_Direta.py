"""
Pagina de Analise Direta - RAG com video sem indexacao previa.

Duas modalidades:
1. Upload Direto: Envie um video e faca perguntas imediatamente (sem salvar no acervo)
2. Chat com Video: Selecione um video do acervo e converse sobre ele

Ambas usam o Gemini File API para analise frame a frame em tempo real.
"""

import tempfile
from pathlib import Path

import streamlit as st

from src.config import settings
from src.components import video_player
from src.services.database_service import DatabaseService
from src.services.gemini_service import GeminiService


# ============================================================================
# Inicializacao de servicos (cached)
# ============================================================================


@st.cache_resource
def get_db_service():
    return DatabaseService(settings.postgres_url)


@st.cache_resource
def get_gemini_service():
    return GeminiService(settings.google_api_key, settings.gemini_model)


# ============================================================================
# Layout Principal
# ============================================================================

st.title("Analise Direta de Video")

st.markdown("""
Converse diretamente com videos usando IA, **sem necessidade de indexacao previa**.

O video e enviado ao Gemini via File API para analise frame a frame em tempo real.
""")

# Verificar API key
if not settings.google_api_key:
    st.error("GOOGLE_API_KEY nao configurada. Edite o arquivo .env na raiz do projeto.")
    st.stop()

# ============================================================================
# Tabs para as duas modalidades
# ============================================================================

tab_upload, tab_acervo = st.tabs([
    "📤 Upload Direto",
    "🎬 Video do Acervo"
])

# ============================================================================
# TAB 1: Upload Direto
# ============================================================================

with tab_upload:
    st.subheader("Upload Direto")
    st.markdown("""
    **Como funciona:**
    1. Faca upload de um video (nao sera salvo no acervo)
    2. Faca perguntas sobre o video
    3. O Gemini analisa o video em tempo real e responde

    *Ideal para analise rapida de videos que voce nao quer indexar.*
    """)

    # Upload temporario
    uploaded_file = st.file_uploader(
        "Selecione um video para analise direta",
        type=["mp4", "avi", "mov", "mkv", "webm"],
        help="O video sera enviado ao Gemini mas NAO sera salvo no acervo.",
        key="direct_upload",
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
        else:
            # Salvar temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp:
                tmp.write(uploaded_file.getbuffer())
                temp_path = tmp.name

            # Preview do video
            with st.expander("Preview do video", expanded=True):
                video_player(temp_path)

            st.caption(f"**{uploaded_file.name}** ({file_size / (1024*1024):.1f} MB)")

            # Historico de chat para este video
            if "direct_chat_history" not in st.session_state:
                st.session_state.direct_chat_history = []
            if "direct_video_path" not in st.session_state:
                st.session_state.direct_video_path = None

            # Se mudou o video, limpar historico
            if st.session_state.direct_video_path != temp_path:
                st.session_state.direct_chat_history = []
                st.session_state.direct_video_path = temp_path

            # Mostrar historico
            for msg in st.session_state.direct_chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            # Input de pergunta
            question = st.chat_input(
                "Faca uma pergunta sobre o video...",
                key="direct_question",
            )

            if question:
                # Adicionar pergunta ao historico
                st.session_state.direct_chat_history.append({
                    "role": "user",
                    "content": question,
                })

                with st.chat_message("user"):
                    st.markdown(question)

                # Gerar resposta
                with st.chat_message("assistant"):
                    with st.spinner("Analisando video com Gemini..."):
                        try:
                            gemini = get_gemini_service()

                            # Montar contexto com historico
                            context = ""
                            if len(st.session_state.direct_chat_history) > 1:
                                context = "Historico da conversa:\n"
                                for msg in st.session_state.direct_chat_history[:-1]:
                                    role = "Usuario" if msg["role"] == "user" else "Assistente"
                                    context += f"{role}: {msg['content']}\n"
                                context += "\nPergunta atual: "

                            # Enviar video + pergunta para o Gemini
                            response = gemini.generate_rag_response_with_videos(
                                query=context + question,
                                video_paths=[temp_path],
                                max_videos=1,
                            )

                            st.markdown(response)

                            # Adicionar resposta ao historico
                            st.session_state.direct_chat_history.append({
                                "role": "assistant",
                                "content": response,
                            })

                        except Exception as e:
                            error_msg = f"Erro na analise: {e}"
                            st.error(error_msg)
                            st.session_state.direct_chat_history.append({
                                "role": "assistant",
                                "content": error_msg,
                            })

            # Botao para limpar historico
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("Limpar Chat", key="clear_direct"):
                    st.session_state.direct_chat_history = []
                    st.rerun()

# ============================================================================
# TAB 2: Video do Acervo
# ============================================================================

with tab_acervo:
    st.subheader("Chat com Video do Acervo")
    st.markdown("""
    **Como funciona:**
    1. Selecione um video ja indexado no acervo
    2. Faca perguntas sobre ele
    3. Mantenha uma conversa contextual

    *Ideal para explorar videos ja analisados com perguntas especificas.*
    """)

    try:
        db = get_db_service()

        # Listar videos analisados
        videos = db.list_videos(status="analyzed")

        if not videos:
            st.info(
                "Nenhum video analisado no acervo. "
                "Use a pagina de Enriquecimento para adicionar videos."
            )
        else:
            # Seletor de video
            video_options = {v.id: f"{v.filename}" for v in videos}
            selected_id = st.selectbox(
                "Selecione um video:",
                options=list(video_options.keys()),
                format_func=lambda x: video_options[x],
                key="acervo_video_select",
            )

            if selected_id:
                selected_video = db.get_video(selected_id)

                if selected_video and selected_video.file_path:
                    # Preview do video
                    with st.expander("Preview do video", expanded=False):
                        video_player(selected_video.file_path)

                    # Info do video
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if selected_video.duration_seconds:
                            mins = int(selected_video.duration_seconds // 60)
                            secs = int(selected_video.duration_seconds % 60)
                            st.metric("Duracao", f"{mins}:{secs:02d}")
                    with col2:
                        if selected_video.emotional_tone:
                            st.metric("Tom", selected_video.emotional_tone)
                    with col3:
                        if selected_video.viral_potential:
                            st.metric("Viral", f"{selected_video.viral_potential:.1f}/10")

                    # Mostrar analise previa (se disponivel)
                    with st.expander("Analise previa (do acervo)"):
                        if selected_video.visual_description:
                            st.markdown("**Analise Visual:**")
                            st.write(selected_video.visual_description)
                        if selected_video.narrative_description:
                            st.markdown("**Analise Narrativa:**")
                            st.write(selected_video.narrative_description)
                        if not selected_video.visual_description and not selected_video.narrative_description:
                            if selected_video.analysis_description:
                                st.write(selected_video.analysis_description)

                    st.divider()

                    # Historico de chat para este video
                    if "acervo_chat_history" not in st.session_state:
                        st.session_state.acervo_chat_history = {}

                    if selected_id not in st.session_state.acervo_chat_history:
                        st.session_state.acervo_chat_history[selected_id] = []

                    chat_history = st.session_state.acervo_chat_history[selected_id]

                    # Mostrar historico
                    for msg in chat_history:
                        with st.chat_message(msg["role"]):
                            st.markdown(msg["content"])

                    # Input de pergunta
                    question = st.chat_input(
                        "Faca uma pergunta sobre este video...",
                        key="acervo_question",
                    )

                    if question:
                        # Adicionar pergunta ao historico
                        chat_history.append({
                            "role": "user",
                            "content": question,
                        })

                        with st.chat_message("user"):
                            st.markdown(question)

                        # Gerar resposta
                        with st.chat_message("assistant"):
                            with st.spinner("Analisando video com Gemini..."):
                                try:
                                    gemini = get_gemini_service()

                                    # Montar contexto com historico e analise previa
                                    context = f"Video: {selected_video.filename}\n"

                                    if selected_video.analysis_description:
                                        context += f"Analise previa: {selected_video.analysis_description[:500]}...\n"

                                    if len(chat_history) > 1:
                                        context += "\nHistorico da conversa:\n"
                                        for msg in chat_history[:-1]:
                                            role = "Usuario" if msg["role"] == "user" else "Assistente"
                                            context += f"{role}: {msg['content']}\n"

                                    context += "\nPergunta atual: "

                                    # Enviar video + pergunta para o Gemini
                                    response = gemini.generate_rag_response_with_videos(
                                        query=context + question,
                                        video_paths=[selected_video.file_path],
                                        max_videos=1,
                                    )

                                    st.markdown(response)

                                    # Adicionar resposta ao historico
                                    chat_history.append({
                                        "role": "assistant",
                                        "content": response,
                                    })

                                except Exception as e:
                                    error_msg = f"Erro na analise: {e}"
                                    st.error(error_msg)
                                    chat_history.append({
                                        "role": "assistant",
                                        "content": error_msg,
                                    })

                    # Botao para limpar historico
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        if st.button("Limpar Chat", key="clear_acervo"):
                            st.session_state.acervo_chat_history[selected_id] = []
                            st.rerun()
                else:
                    st.warning("Video selecionado nao encontrado ou sem arquivo.")

    except Exception as e:
        st.warning(f"Erro ao carregar videos: {e}")

# ============================================================================
# Documentacao
# ============================================================================

with st.expander("Sobre esta pagina"):
    st.markdown("""
    ## Analise Direta de Video

    Esta pagina permite conversar diretamente com videos usando o Gemini,
    **sem necessidade de indexacao previa** (embeddings).

    ### Modalidades

    #### 📤 Upload Direto
    - Faca upload de qualquer video
    - O video **NAO e salvo** no acervo
    - Ideal para analise rapida de videos temporarios
    - Cada upload inicia uma nova conversa

    #### 🎬 Video do Acervo
    - Selecione um video ja indexado
    - Aproveite a analise previa como contexto
    - Historico de conversa persistente por video
    - Ideal para explorar videos com perguntas especificas

    ### Tecnologia

    - **Modelo:** Gemini 2.0 Flash (rapido para evitar timeouts)
    - **API:** File API do Google (analise frame a frame)
    - **Contexto:** Historico da conversa e enviado junto com cada pergunta

    ### Limitacoes

    - Videos muito longos podem demorar para processar
    - Limite de tamanho: {max_size} MB
    - Cada pergunta envia o video novamente (pode haver custos de API)
    """.format(max_size=settings.max_video_size_mb))
