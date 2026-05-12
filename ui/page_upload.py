import json
import os
import io
import streamlit as st
import pandas as pd


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


def _cargar_defaults() -> tuple[pd.DataFrame | None, dict | None]:
    df = None
    rubrica = None
    ruta_csv = "config/matriz.csv"
    ruta_json = "config/rubrica.json"
    if os.path.exists(ruta_csv):
        df = pd.read_csv(ruta_csv, header=None)
    if os.path.exists(ruta_json):
        with open(ruta_json) as f:
            rubrica = json.load(f)
    return df, rubrica


def _validar_csv(contenido: bytes) -> tuple[bool, str]:
    try:
        df = pd.read_csv(io.BytesIO(contenido), header=None)
        if df.shape[1] < 2:
            return False, "El CSV debe tener al menos 2 columnas."
        if df.shape[0] < 2:
            return False, "El CSV debe tener al menos 2 filas."
        return True, ""
    except Exception as e:
        return False, f"Error al leer el CSV: {e}"


def _validar_json(contenido: bytes) -> tuple[bool, str]:
    try:
        data = json.loads(contenido.decode("utf-8"))
        if not isinstance(data, dict):
            return False, "El JSON debe ser un diccionario (objeto)."
        if len(data) < 1:
            return False, "El JSON debe tener al menos una clave (tipo de documento)."
        return True, ""
    except Exception as e:
        return False, f"Error al leer el JSON: {e}"


def render():
    st.title("Carga de Informes")
    st.markdown("Sube los archivos necesarios para comenzar la evaluación.")

    pdf_file = st.file_uploader("Informe en PDF", type=["pdf"], key="pdf_upload")

    tipos_disponibles = _cargar_tipos_rubrica()
    tipo_doc = st.radio(
        "Tipo de Práctica",
        options=tipos_disponibles,
        format_func=_formatear_tipo,
        horizontal=True,
    )

    st.divider()

    df_default, rubrica_default = _cargar_defaults()
    usar_propios = st.checkbox("Ingresar mis propios archivos", value=False)

    if usar_propios:
        csv_file = st.file_uploader("Matriz de Competencias (CSV)", type=["csv"], key="csv_upload")
        json_file = st.file_uploader("Rúbrica Estructural (JSON)", type=["json"], key="json_upload")
    else:
        st.info("Se están usando los archivos predeterminados de matriz y rúbrica.")
        with st.expander("Ver contenido de archivos predeterminados"):
            col_csv, col_json = st.columns(2)
            with col_csv:
                st.markdown("**Matriz de Competencias**")
                if df_default is not None:
                    st.dataframe(df_default, use_container_width=True)
                else:
                    st.info("No se encontró el archivo predeterminado.")
            with col_json:
                st.markdown("**Rúbrica Estructural**")
                if rubrica_default is not None:
                    st.json(rubrica_default)
                else:
                    st.info("No se encontró el archivo predeterminado.")
        csv_file = None
        json_file = None

    if st.button("Cargar y Validar", type="primary", use_container_width=True):
        if not pdf_file:
            st.error("Debes subir un archivo PDF.")
            return

        st.session_state["pdf_bytes"] = pdf_file.getvalue()
        st.session_state["pdf_name"] = pdf_file.name
        st.session_state["tipo_documento"] = tipo_doc

        if usar_propios:
            if not csv_file:
                st.error("Debes subir una matriz de competencias (CSV).")
                return
            if not json_file:
                st.error("Debes subir una rúbrica estructural (JSON).")
                return

            valido_csv, msg_csv = _validar_csv(csv_file.getvalue())
            if not valido_csv:
                st.error(f"Matriz inválida: {msg_csv}")
                return

            valido_json, msg_json = _validar_json(json_file.getvalue())
            if not valido_json:
                st.error(f"Rúbrica inválida: {msg_json}")
                return

            st.session_state["csv_bytes"] = csv_file.getvalue()
            st.session_state["json_bytes"] = json_file.getvalue()
        else:
            st.session_state["csv_bytes"] = None
            st.session_state["json_bytes"] = None

        st.session_state["usar_propios"] = usar_propios
        st.session_state["pipeline_iniciado"] = False
        st.session_state["page"] = "pipeline"
        st.rerun()
