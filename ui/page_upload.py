import json
import os
import html
import io
import threading
import time
import zipfile
import uuid
import streamlit as st

from pipeline.batch_orchestrator import run_batch
from pipeline.cohorts import create_cohort, get_cohort, add_reports_to_cohort
from pipeline.models import BatchConfig
from pipeline.persistence import load_index
from ui.components import page_hero, processing_panel
from ui.icons import spinner, check, search, cut, brain, clip, cpu, chart, xmark, clock, doc


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


def _build_pending_report(
    pdf_bytes: bytes,
    pdf_name: str,
    tipo_doc: str,
    csv_bytes: bytes | None = None,
    json_bytes: bytes | None = None,
) -> dict:
    return {
        "report_id": str(uuid.uuid4()),
        "pdf_bytes": pdf_bytes,
        "pdf_name": pdf_name,
        "tipo_documento": tipo_doc,
        "csv_bytes": csv_bytes,
        "json_bytes": json_bytes,
        "top_k": 5,
        "umbral": 0.65,
        "use_pdf": False,
    }


STAGE_LABELS = {
    "esperando": (clock, "En espera"),
    "c1_ingesta": (doc, "Extrayendo texto..."),
    "c2_parser": (search, "Analizando secciones..."),
    "c3_chunker": (cut, "Fragmentando..."),
    "c4_embeddings": (brain, "Generando embeddings..."),
    "c5_retrieval": (clip, "Recuperando evidencia..."),
    "c6_evaluacion": (cpu, "Evaluando con IA..."),
    "c7_agregacion": (chart, "Agregando resultados..."),
    "completado": (check, "Completado"),
    "error": (xmark, "Error"),
}


def _stage_html(stage: str, comps_done: int, comps_total) -> str:
    icon_fn, label = STAGE_LABELS.get(stage, (doc, stage))
    icon_svg = icon_fn(14, 14, "#5F6B76")
    return f'{icon_svg} {label} ({comps_done}/{comps_total})'


def _render_processing():
    pending = st.session_state.get("pending_reports", [])
    total = len(pending)

    progress = st.session_state.get("batch_progress", {})
    thread = st.session_state.get("batch_thread")
    done = progress.get("_done", 0)
    errors = progress.get("_errors", 0)

    is_alive = thread and thread.is_alive() if thread else False

    if not is_alive and thread is not None:
        st.session_state["batch_thread"] = None
        st.session_state["batch_running"] = False
        st.session_state["pending_reports"] = []
        st.session_state["report_count"] = len(load_index())
        st.session_state["page"] = "cohort_macro"
        st.rerun()
        return

    st.markdown(f'<h3 style="margin-bottom:24px">Procesando Informes</h3>', unsafe_allow_html=True)

    for r in pending:
        rid = r["report_id"]
        pdata = progress.get(rid, {})
        stage = pdata.get("stage", "esperando")
        comps_done = pdata.get("comps_done", 0)
        comps_total = pdata.get("total_comps", "?")
        current_comp = pdata.get("current_comp_name", "")
        name = r.get("pdf_name", rid[:8])

        icon_fn, stage_label = STAGE_LABELS.get(stage, (doc, stage))
        icon_svg = icon_fn(16, 16, "#5F6B76")

        is_complete = stage in ("done", "completado") or (
            isinstance(comps_total, int) and comps_total > 0 and comps_done >= comps_total
        )

        if is_complete:
            comp_pct = 1
            remaining = 0
            stage_label = "Completado"
        elif stage == "C42_C5_C6" and isinstance(comps_total, int) and comps_total > 0:
            comp_pct = comps_done / comps_total
            remaining = comps_total - comps_done
        else:
            comp_pct = 0
            remaining = 0

        if stage == "C42_C5_C6" and isinstance(comps_total, int) and comps_total > 0:
            detail_text = f"Competencia: {current_comp} ({remaining} restantes)"
        elif is_complete:
            detail_text = "Informe procesado correctamente"
        else:
            detail_text = "Preparando competencias..."

        card_class = "uandes-processing-report-card complete" if is_complete else "uandes-processing-report-card loading"
        st.markdown(
            f"""
            <div class="{card_class}" style="--progress:{comp_pct * 100:.1f}%">
                <div class="uandes-processing-report-header">
                    <div class="uandes-processing-report-name">{html.escape(name)}</div>
                    <div class="uandes-processing-report-stage">{icon_svg} {html.escape(stage_label)}</div>
                </div>
                <div class="uandes-processing-report-detail">{html.escape(detail_text)}</div>
                <div class="uandes-processing-report-progress">
                    <div class="uandes-processing-report-progress-fill"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Overall progress bar at the bottom
    pct = done / total if total > 0 else 0
    st.markdown('<hr style="margin:20px 0 12px">', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:14px;font-weight:600;margin-bottom:6px">{done} de {total} informes completados ({errors} errores)</div>', unsafe_allow_html=True)
    st.progress(pct)

    sp = spinner(32, 32)
    st.markdown(f'<div style="text-align:center;margin-top:16px">{sp}</div>', unsafe_allow_html=True)

    time.sleep(0.3)
    st.rerun()


def _start_processing(pending, cohort_id):
    api_key = st.session_state.get("api_key", "")
    c6_provider = "openrouter"
    c6_api_key = st.session_state.get("openrouter_key_input") or os.getenv("OPENROUTER_API_KEY", "")
    provider = st.session_state.get("provider", "gemini")
    st.session_state["c6_provider"] = c6_provider

    for r in pending:
        r["use_pdf"] = False
        r["top_k"] = r.get("top_k", 5)
        r["umbral"] = r.get("umbral", 0.65)

    llm_config = {
        "api_key": api_key,
        "provider": provider,
        "c6_provider": c6_provider,
        "c6_api_key": c6_api_key,
    }
    batch_config = BatchConfig(max_workers=5, max_reports_per_batch=10, semaphore_limit=5)

    progress = {}
    st.session_state["batch_progress"] = progress
    st.session_state["batch_running"] = True

    def _run_and_save():
        try:
            results = run_batch(pending, llm_config, batch_config, progress)
            report_ids = [r.report_id for r in results if r.estado != "error"]
            if report_ids and cohort_id:
                add_reports_to_cohort(cohort_id, report_ids)
        except Exception:
            pass

    thread = threading.Thread(target=_run_and_save, daemon=True)
    st.session_state["batch_thread"] = thread
    thread.start()


def render():
    if st.session_state.get("batch_running"):
        _render_processing()
        return

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

    st.subheader("Crear Cohortes")

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

    with st.expander("Configuración Avanzada"):
        csv_file = st.file_uploader(
            "Matriz de competencias (CSV)",
            type=["csv"],
            key="csv_upload",
            help="Si no se provee, se usará la matriz por defecto (config/matriz.csv).",
        )
        json_file = st.file_uploader(
            "Rúbrica de evaluación (JSON)",
            type=["json"],
            key="json_upload",
            help="Si no se provee, se usará la rúbrica por defecto (config/rubrica.json).",
        )

    csv_bytes = csv_file.getvalue() if csv_file else None
    json_bytes = json_file.getvalue() if json_file else None

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
                    pending.append(_build_pending_report(pdf_bytes, pdf_name, tipo_doc, csv_bytes, json_bytes))
            elif f.name.lower().endswith(".pdf"):
                pending.append(_build_pending_report(f.getvalue(), f.name, tipo_doc, csv_bytes, json_bytes))

        if pending:
            st.markdown('<hr class="uandes-divider">', unsafe_allow_html=True)

            chip_html = '<div class="uandes-file-chips">'
            for r in pending:
                doc_svg = doc(14, 14, "currentColor")
                chip_html += f'<span class="uandes-file-chip">{doc_svg} {r["pdf_name"]}</span>'
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
                        _start_processing(pending, st.session_state["current_cohort_id"])
                        st.rerun()
