import os
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google")
warnings.filterwarnings("ignore", message=".*python_version_support.*")

import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def main():
    st.set_page_config(
        page_title="Evaluador de Informes de Práctica",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    for k in ["provider", "api_key", "c6_provider"]:
        if k not in st.session_state:
            st.session_state[k] = "" if k == "api_key" else "gemini"
    if "page" not in st.session_state:
        st.session_state["page"] = "upload"

    with st.sidebar:
        st.title("Evaluador de Informes")

        st.markdown("### Embeddings (C4)")
        emb_prov = st.selectbox(
            "Proveedor",
            options=["gemini", "openai"],
            index=0 if st.session_state.get("provider", "gemini") == "gemini" else 1,
            key="emb_prov_sel",
        )
        st.session_state["provider"] = emb_prov
        emb_env_key = os.getenv(
            {"gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY"}[emb_prov], ""
        )
        if emb_env_key:
            st.session_state["api_key"] = emb_env_key
        else:
            inp = st.text_input(f"API Key de {emb_prov.title()}:", key="embed_key_input")
            if inp:
                st.session_state["api_key"] = inp

        st.markdown("---")
        st.markdown("### Evaluación LLM (C6)")
        c6_prov = st.selectbox(
            "Proveedor C6",
            options=["gemini", "openai", "openrouter"],
            index=(
                0 if st.session_state.get("c6_provider", "gemini") == "gemini"
                else 1 if st.session_state.get("c6_provider") == "openai"
                else 2
            ),
            key="c6_prov_sel",
        )
        st.session_state["c6_provider"] = c6_prov

        if c6_prov == "openrouter":
            or_key = os.getenv("OPENROUTER_API_KEY", "")
            if or_key:
                st.success("✓ OpenRouter key desde .env")
            else:
                st.text_input("OpenRouter API Key:", key="openrouter_key_input")

        st.markdown("---")
        if st.button("Cargar Archivos", use_container_width=True):
            st.session_state["page"] = "upload"
            st.rerun()
        if st.button("Pipeline", use_container_width=True):
            st.session_state["page"] = "pipeline"
            st.rerun()
        if st.button("Resultados", use_container_width=True):
            st.session_state["page"] = "resultados"
            st.rerun()
        if st.button("Configuración", use_container_width=True):
            st.session_state["page"] = "admin"
            st.rerun()

        st.markdown("---")
        st.markdown("**Pipeline C1-C7 + HITL**")
        st.markdown("Desarrollado para IAA - Grupo 2")

    page = st.session_state["page"]

    if page == "upload":
        from ui.page_upload import render as render_upload
        render_upload()
    elif page == "pipeline":
        from ui.page_pipeline import render as render_pipeline
        render_pipeline()
    elif page == "resultados":
        from ui.page_resultados import render as render_resultados
        render_resultados()
    elif page == "admin":
        from ui.page_admin import render as render_admin
        render_admin()


if __name__ == "__main__":
    main()
