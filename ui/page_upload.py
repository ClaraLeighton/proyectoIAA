import json
import os
import streamlit as st


def _cargar_tipos_rubrica() -> list[str]:
    ruta = "config/rubrica.json"
    if os.path.exists(ruta):
        with open(ruta) as f:
            rubrica = json.load(f)
        return list(rubrica.keys())
    return ["pre_professional_practice", "professional_practice"]


def _formatear_tipo(tipo: str) -> str:
    nombre = tipo.replace("_", " ").title()
    nombre = nombre.replace("Pre ", "Pre-")
    nombre = nombre.replace("Practica", "Práctica")
    return nombre


def render():
    st.title("Carga de Informes")
    st.markdown("Sube los archivos necesarios para comenzar la evaluación.")

    pdf_file = st.file_uploader("Informe en PDF", type=["pdf"], key="pdf_upload")
    csv_file = st.file_uploader("Matriz de Competencias (CSV)", type=["csv"], key="csv_upload")
    json_file = st.file_uploader("Rúbrica Estructural (JSON)", type=["json"], key="json_upload")

    tipos_disponibles = _cargar_tipos_rubrica()
    tipo_doc = st.radio(
        "Tipo de Práctica",
        options=tipos_disponibles,
        format_func=_formatear_tipo,
        horizontal=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        usar_defaults = st.checkbox("Usar archivos de configuración por defecto", value=True)

    if st.button("Cargar y Validar", type="primary", use_container_width=True):
        if not pdf_file:
            st.error("Debes subir un archivo PDF.")
            return

        st.session_state["pdf_bytes"] = pdf_file.getvalue()
        st.session_state["pdf_name"] = pdf_file.name
        st.session_state["tipo_documento"] = tipo_doc

        if csv_file:
            st.session_state["csv_bytes"] = csv_file.getvalue()
        else:
            st.session_state["csv_bytes"] = None

        if json_file:
            st.session_state["json_bytes"] = json_file.getvalue()
        else:
            st.session_state["json_bytes"] = None

        st.session_state["usar_defaults"] = usar_defaults
        st.session_state["pipeline_iniciado"] = False
        st.session_state["page"] = "pipeline"
        st.rerun()
