import os
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google")
warnings.filterwarnings("ignore", message=".*python_version_support.*")
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from pipeline.persistence import load_index
from pipeline.cohorts import list_cohorts
from ui.components import sidebar_group, topbar_html
from ui.icons import folder, folder_plus, chart, list_icon, settings, bar_chart, layers, file_text

load_dotenv()


def _inject_css():
    css_path = Path("assets/style.css")
    if css_path.exists():
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def _init_session():
    if "page" not in st.session_state:
        st.session_state["page"] = "cohorts"
    if "pending_reports" not in st.session_state:
        st.session_state["pending_reports"] = []
    if "report_count" not in st.session_state:
        index = load_index()
        st.session_state["report_count"] = len(index)
    if "new_cohort" not in st.session_state:
        st.session_state["new_cohort"] = True

    for k in ["provider", "api_key", "c6_provider"]:
        if k not in st.session_state:
            st.session_state[k] = "" if k == "api_key" else ("openrouter" if k == "c6_provider" else "gemini")

    emb_prov = st.session_state.get("provider", "gemini")
    env_key = os.getenv(
        {"gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY"}[emb_prov], ""
    )
    if env_key:
        st.session_state["api_key"] = env_key

    if st.session_state.get("c6_provider") == "openrouter":
        or_key = os.getenv("OPENROUTER_API_KEY", "")
        if or_key:
            st.session_state["openrouter_key_input"] = or_key


def _nav_button(label, page_key, icon_svg):
    is_active = st.session_state.get("page", "") == page_key
    is_context = st.session_state.get("selected_cohort_id") is not None
    if page_key in ("cohort_macro", "cohort_reports", "cohort_config") and not is_context:
        return
    col1, col2 = st.columns([1, 4])
    with col1:
        st.markdown(
            f'<div class="sidebar-nav-icon-box{" active" if is_active else ""}">{icon_svg}</div>',
            unsafe_allow_html=True,
        )
    with col2:
        kind = "primary" if is_active else "secondary"
        if st.button(label, key=f"nav_{page_key}", type=kind, use_container_width=True):
            st.session_state["page"] = page_key
            if page_key == "cohorts":
                st.session_state.pop("selected_cohort_id", None)
            if page_key in ("upload",):
                st.session_state["new_cohort"] = True
            st.rerun()


def _sidebar():
    with st.sidebar:
        st.markdown('<div class="sidebar-inner">', unsafe_allow_html=True)

        logo_path = Path("assets/logo_uandes.png")
        b64 = None
        if logo_path.exists():
            import base64
            with open(logo_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()

        if b64:
            st.markdown(
                f'<div class="sidebar-logo-block">'
                f'<div class="sidebar-logo-row">'
                f'<img src="data:image/png;base64,{b64}" alt="UANDES">'
                f"</div>"
                f'<div class="sidebar-brand">Evaluador de Perfil</div>'
                f'<div class="sidebar-brand-sub">de Egreso</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="sidebar-logo-block">'
                '<div class="sidebar-logo-row">'
                '<svg width="28" height="28" viewBox="0 0 50 50" fill="none">'
                '<rect x="2" y="2" width="46" height="46" rx="6" stroke="#CE0019" stroke-width="3" fill="none"/>'
                '<path d="M10 36 L14 14 L18 22 L25 10 L32 22 L36 14 L40 36" stroke="#CE0019" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
                '<line x1="8" y1="38" x2="42" y2="38" stroke="#CE0019" stroke-width="2"/>'
                '</svg>'
                '<div>'
                '<div class="sidebar-brand">Evaluador de Perfil</div>'
                '<div class="sidebar-brand-sub">de Egreso</div>'
                '</div>'
                "</div>"
                "</div>",
                unsafe_allow_html=True,
            )

        st.markdown(sidebar_group("Navegación"), unsafe_allow_html=True)

        _nav_button("Mis Cohortes", "cohorts", layers(20, 20, "currentColor"))
        _nav_button("Nueva Cohorte", "upload", folder_plus(20, 20, "currentColor"))

        cohort_id = st.session_state.get("selected_cohort_id")
        if cohort_id:
            cohorts = list_cohorts()
            cohort = next((c for c in cohorts if c["cohort_id"] == cohort_id), None)
            if cohort:
                st.markdown(sidebar_group(cohort["name"]), unsafe_allow_html=True)
                _nav_button("Resultados Macro", "cohort_macro", bar_chart(20, 20, "currentColor"))
                _nav_button("Resultados Micro", "cohort_reports", file_text(20, 20, "currentColor"))
                _nav_button("Configuración", "cohort_config", settings(20, 20, "currentColor"))

        st.markdown(
            f'<div class="sidebar-footer"><span>{st.session_state.get("report_count", 0)} informes en disco</span></div>',
            unsafe_allow_html=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)

        has_env_key = any(os.getenv(k) for k in ["GEMINI_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY"])
        if not has_env_key:
            with st.expander("Config. API"):
                emb_prov = st.selectbox(
                    "Proveedor Embeddings",
                    options=["gemini", "openai"],
                    index=0 if st.session_state.get("provider", "gemini") == "gemini" else 1,
                    key="emb_prov_sel",
                )
                st.session_state["provider"] = emb_prov
                inp = st.text_input(f"API Key {emb_prov.title()}", key="embed_key_input", type="password")
                if inp:
                    st.session_state["api_key"] = inp

                c6_prov = st.selectbox(
                    "Proveedor Eval.",
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
                    or_key = st.text_input("OpenRouter Key", key="openrouter_key_input", type="password")
                    if or_key:
                        st.session_state["openrouter_key_input"] = or_key


def main():
    st.set_page_config(
        page_title="Evaluador de Perfil de Egreso - Universidad de los Andes",
        page_icon="assets/logo_uandes.svg",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _inject_css()

    st.markdown(topbar_html(), unsafe_allow_html=True)

    # Handle URL query params (cohort card links) — these come from full page reloads
    # triggered by cohort card buttons using window.location.search.
    params = st.query_params
    if "page" in params:
        st.session_state["page"] = params["page"]
    if "cid" in params:
        st.session_state["selected_cohort_id"] = params["cid"]
    if "page" in params or "cid" in params:
        st.query_params.clear()

    _init_session()

    _sidebar()

    page = st.session_state["page"]

    if page == "cohorts":
        from ui.page_cohorts import render as render_cohorts
        render_cohorts()
    elif page == "cohort_config":
        from ui.page_cohort_config import render as render_config
        render_config()
    elif page == "cohort_macro":
        from ui.page_cohort_detail import render as render_macro
        render_macro()
    elif page == "upload":
        from ui.page_upload import render as render_upload
        render_upload()
    elif page == "processing":
        from ui.page_processing import render as render_processing
        render_processing()
    elif page == "cohort_reports":
        from ui.page_cohort_reports import render as render_reports
        render_reports()
    elif page == "report_detail":
        from ui.page_report_detail import render as render_report_detail
        render_report_detail()


if __name__ == "__main__":
    main()
