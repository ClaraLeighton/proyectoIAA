import json
import os
import io
import zipfile
import uuid
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


def _extraer_pdfs_de_zip(zip_bytes: bytes) -> list[tuple[bytes, str]]:
    pdfs = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        for name in z.namelist():
            if name.lower().endswith(".pdf"):
                pdfs.append((z.read(name), os.path.basename(name)))
    return pdfs


def _extraer_config_de_zip(zip_bytes: bytes) -> tuple[bytes | None, bytes | None]:
    csv_bytes = None
    json_bytes = None
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        for name in z.namelist():
            lower = name.lower()
            if lower.endswith(".csv") and csv_bytes is None:
                csv_bytes = z.read(name)
            elif lower.endswith(".json") and json_bytes is None:
                json_bytes = z.read(name)
    return csv_bytes, json_bytes


def render():
    st.title("Carga de Informes")
    st.markdown("Sube uno o más informes para evaluar.")

    uploaded_files = st.file_uploader(
        "Selecciona PDFs individuales o un archivo ZIP",
        type=["pdf", "zip"],
        accept_multiple_files=True,
        key="pdf_upload",
    )

    tipos_disponibles = _cargar_tipos_rubrica()
    tipo_doc = st.radio(
        "Tipo de Práctica",
        options=tipos_disponibles,
        format_func=_formatear_tipo,
        horizontal=True,
    )

    st.divider()
    st.markdown("### Archivos de configuración")

    df_default, rubrica_default = _cargar_defaults()
    with st.expander("Ver archivos predeterminados del sistema", expanded=False):
        col_csv, col_json = st.columns(2)
        with col_csv:
            st.markdown("**Matriz de Competencias**")
            if df_default is not None:
                st.dataframe(df_default, width="stretch")
            else:
                st.info("No se encontró el archivo predeterminado.")
        with col_json:
            st.markdown("**Rúbrica Estructural**")
            if rubrica_default is not None:
                st.json(rubrica_default)
            else:
                st.info("No se encontró el archivo predeterminado.")

    col1, col2 = st.columns(2)
    with col1:
        csv_file = st.file_uploader(
            "Matriz de Competencias (CSV) — opcional",
            type=["csv"],
            key="csv_upload",
            help="Si no se sube, se usará la matriz predeterminada del sistema.",
        )
    with col2:
        json_file = st.file_uploader(
            "Rúbrica Estructural (JSON) — opcional",
            type=["json"],
            key="json_upload",
            help="Si no se sube, se usará la rúbrica predeterminada del sistema.",
        )

    if st.button("Cargar y Validar", type="primary", width="stretch"):
        if not uploaded_files:
            st.error("Debes subir al menos un archivo PDF o ZIP.")
            return

        csv_config = csv_file.getvalue() if csv_file else None
        json_config = json_file.getvalue() if json_file else None

        if csv_config:
            valido, msg = _validar_csv(csv_config)
            if not valido:
                st.error(f"Matriz inválida: {msg}")
                return

        if json_config:
            valido, msg = _validar_json(json_config)
            if not valido:
                st.error(f"Rúbrica inválida: {msg}")
                return

        pending_reports = []
        for f in uploaded_files:
            if f.name.lower().endswith(".zip"):
                pdfs = _extraer_pdfs_de_zip(f.getvalue())
                if not pdfs:
                    st.warning(f"El archivo ZIP '{f.name}' no contiene PDFs.")
                    continue
                for pdf_bytes, pdf_name in pdfs:
                    report_id = str(uuid.uuid4())
                    config_bytes_csv, config_bytes_json = _extraer_config_de_zip(f.getvalue())
                    pending_reports.append({
                        "report_id": report_id,
                        "pdf_bytes": pdf_bytes,
                        "pdf_name": pdf_name,
                        "tipo_documento": tipo_doc,
                        "csv_bytes": config_bytes_csv or csv_config,
                        "json_bytes": config_bytes_json or json_config,
                        "top_k": 5,
                        "umbral": 0.65,
                        "use_pdf": False,
                    })
            elif f.name.lower().endswith(".pdf"):
                report_id = str(uuid.uuid4())
                pending_reports.append({
                    "report_id": report_id,
                    "pdf_bytes": f.getvalue(),
                    "pdf_name": f.name,
                    "tipo_documento": tipo_doc,
                    "csv_bytes": csv_config,
                    "json_bytes": json_config,
                    "top_k": 5,
                    "umbral": 0.65,
                    "use_pdf": False,
                })

        if not pending_reports:
            st.error("No se encontraron archivos PDF válidos.")
            return

        st.success(f"{len(pending_reports)} informe(s) cargado(s) correctamente.")
        st.session_state["pending_reports"] = pending_reports
        st.session_state["pipeline_iniciado"] = False
        st.session_state["page"] = "pipeline"
        st.rerun()
