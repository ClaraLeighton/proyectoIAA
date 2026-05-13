import os
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google")
warnings.filterwarnings("ignore", message=".*python_version_support.*")

import streamlit as st
from dotenv import load_dotenv
from pipeline.persistence import load_index

load_dotenv()


def _init_session():
    for k in ["provider", "api_key", "c6_provider"]:
        if k not in st.session_state:
            st.session_state[k] = "" if k == "api_key" else ("openrouter" if k == "c6_provider" else "gemini")
    if "page" not in st.session_state:
        st.session_state["page"] = "upload"
    if "pending_reports" not in st.session_state:
        st.session_state["pending_reports"] = []
    if "report_count" not in st.session_state:
        index = load_index()
        st.session_state["report_count"] = len(index)


def main():
    st.set_page_config(
        page_title="Evaluador de Informes de Práctica",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _init_session()

    with st.sidebar:
        st.title("Evaluador de Informes")

        total_reports = st.session_state.get("report_count", 0)
        if total_reports > 0:
            st.markdown(f"**Informes en disco:** {total_reports}")

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
        if st.button("Cargar Archivos", width="stretch"):
            st.session_state["page"] = "upload"
            st.rerun()
        if st.button("Pipeline", width="stretch"):
            st.session_state["page"] = "pipeline"
            st.rerun()
        if st.button("Dashboard", width="stretch"):
            st.session_state["page"] = "dashboard"
            st.rerun()
        if st.button("Resultados", width="stretch"):
            st.session_state["page"] = "resultados"
            st.rerun()
        if st.button("Configuración", width="stretch"):
            st.session_state["page"] = "admin"
            st.rerun()

        st.markdown("---")
        st.markdown("**Pipeline C1-C7 con procesamiento paralelo**")
        st.markdown("Desarrollado para IAA - Grupo 2")

    page = st.session_state["page"]

    if page == "upload":
        from ui.page_upload import render as render_upload
        render_upload()
    elif page == "pipeline":
        from ui.page_pipeline import render as render_pipeline
        render_pipeline()
    elif page == "dashboard":
        from ui.page_dashboard import render as render_dashboard
        render_dashboard()
    elif page == "resultados":
        from ui.page_resultados import render as render_resultados
        render_resultados()
    elif page == "admin":
        from ui.page_admin import render as render_admin
        render_admin()


if __name__ == "__main__":
    main()
