"""
MVP RAG Local - Entry point Streamlit
"""

import streamlit as st

st.set_page_config(
    page_title="MVP RAG Local",
    page_icon="🎬",
    layout="wide",
)

pg_upload = st.Page("pages/1_Enriquecimento.py", title="Enriquecimento", icon="📤")
pg_search = st.Page("pages/2_Busca_RAG.py", title="Busca RAG", icon="🔍")

nav = st.navigation([pg_upload, pg_search])
nav.run()
