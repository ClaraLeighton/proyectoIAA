import json
import os
import io
import zipfile
import uuid
import streamlit as st

from pipeline.cohorts import create_cohort, get_cohort
from ui.components import page_hero, section_card, section_card_end


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


def _extraer_pdfs_de_zip(zip_bytes: bytes) -> list[tuple[bytes, str]]:
    pdfs = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        for name in z.namelist():
            if name.lower().endswith(".pdf"):
                pdfs.append((z.read(name), os.path.basename(name)))
    return pdfs


def _build_pending_report(pdf_bytes: bytes, pdf_name: str, tipo_doc: str) -> dict:
    return {
        "report_id": str(uuid.uuid4()),
        "pdf_bytes": pdf_bytes,
        "pdf_name": pdf_name,
        "tipo_documento": tipo_doc,
        "csv_bytes": None,
        "json_bytes": None,
        "top_k": 5,
        "umbral": 0.65,
        "use_pdf": False,
    }


def render():
    st.session_state.pop("upload_submitted", None)
    new_cohort = st.session_state.get("new_cohort", True)
    cohort_id = st.session_state.get("selected_cohort_id")
    existing_cohort = get_cohort(cohort_id) if cohort_id else None

    if new_cohort:
        title = "Nueva Cohorte"
        subtitle = "Completa los datos y sube los archivos para crear una nueva cohorte de evaluación."
    elif existing_cohort:
        title = f"Agregar a {existing_cohort['name']}"
        subtitle = "Los informes se agregarán a la cohorte existente."
    else:
        title = "Cargar Informes"
        subtitle = ""

    target = "cohort_config" if existing_cohort else "cohorts"
    page_hero(title, subtitle=subtitle, back_target=target)

    section_card("Crear Cohortes")

    st.markdown('<div class="uandes-form-section"><div class="uandes-form-section-title">Información General</div></div>', unsafe_allow_html=True)

    if new_cohort:
        cohort_name = st.text_input(
            "Nombre de la cohorte",
            placeholder="Ej: Práctica Pre-Profesional 2026",
            key="cohort_name_input",
        )
    else:
        cohort_name = existing_cohort["name"] if existing_cohort else ""

    st.markdown('<div class="uandes-form-section"><div class="uandes-form-section-title">Archivos</div></div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "Arrastra tus archivos PDF o ZIP aquí",
        type=["pdf", "zip"],
        accept_multiple_files=True,
        key="pdf_upload",
    )
    st.markdown('<p style="font-size:13px;color:var(--uandes-text-muted);margin-top:-6px">Máximo 200MB por archivo. Se aceptan PDF y ZIP con múltiples PDFs.</p>', unsafe_allow_html=True)

    st.markdown('<div class="uandes-form-section"><div class="uandes-form-section-title">Tipo de Práctica</div></div>', unsafe_allow_html=True)
    tipos_disponibles = _cargar_tipos_rubrica()
    tipo_doc = st.radio(
        "Selecciona el tipo de práctica para estos informes",
        options=tipos_disponibles,
        format_func=_formatear_tipo,
        horizontal=True,
        key="tipo_doc_radio",
    )

    if not new_cohort and existing_cohort:
        if tipo_doc != existing_cohort["tipo_documento"]:
            st.warning(
                f"Esta cohorte es de tipo '{_formatear_tipo(existing_cohort['tipo_documento'])}'. "
                f"Los informes deben ser del mismo tipo."
            )

    if uploaded_files:
        pending = []
        for f in uploaded_files:
            if f.name.lower().endswith(".zip"):
                pdfs = _extraer_pdfs_de_zip(f.getvalue())
                for pdf_bytes, pdf_name in pdfs:
                    pending.append(_build_pending_report(pdf_bytes, pdf_name, tipo_doc))
            elif f.name.lower().endswith(".pdf"):
                pending.append(_build_pending_report(f.getvalue(), f.name, tipo_doc))

        if pending:
            st.markdown('<hr class="uandes-divider">', unsafe_allow_html=True)

            chip_html = '<div class="uandes-file-chips">'
            for r in pending:
                chip_html += f'<span class="uandes-file-chip">📄 {r["pdf_name"]}</span>'
            chip_html += "</div>"
            st.markdown(
                f'<p style="font-size:15px;font-weight:600;margin-bottom:8px">{len(pending)} archivo{"s" if len(pending) != 1 else ""} cargado{"s" if len(pending) != 1 else ""}</p>',
                unsafe_allow_html=True,
            )
            st.markdown(chip_html, unsafe_allow_html=True)

            st.markdown('<div style="margin-top:20px"></div>', unsafe_allow_html=True)
            st.markdown('<div class="uandes-form-section"><div class="uandes-form-section-title">Acción Final</div></div>', unsafe_allow_html=True)
            col_p1, col_p2 = st.columns([1, 1])
            with col_p1:
                if st.button("Cancelar", type="secondary", use_container_width=True):
                    target = "cohort_config" if existing_cohort else "cohorts"
                    st.session_state["page"] = target
                    st.rerun()
            with col_p2:
                btn_label = "Crear Cohorte" if new_cohort else "Agregar a cohorte"
                if st.button(btn_label, type="primary", use_container_width=True):
                    if new_cohort and not cohort_name.strip():
                        st.error("Debes ingresar un nombre para la cohorte.")
                    else:
                        if new_cohort:
                            cohort = create_cohort(cohort_name.strip(), tipo_doc)
                            st.session_state["selected_cohort_id"] = cohort["cohort_id"]
                            st.session_state["current_cohort_id"] = cohort["cohort_id"]
                        else:
                            st.session_state["current_cohort_id"] = cohort_id

                        st.session_state["pending_reports"] = pending
                        st.session_state["pipeline_iniciado"] = False
                        st.session_state["page"] = "processing"
                        st.rerun()

    section_card_end()
