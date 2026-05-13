import os
import threading
import time
import streamlit as st

from pipeline.models import BatchConfig
from pipeline.batch_orchestrator import run_batch
from pipeline.cohorts import add_reports_to_cohort
from pipeline.persistence import load_index
from ui.components import page_hero, section_card, section_card_end, processing_panel
from ui.icons import check, search, cut, brain, clip, cpu, chart, xmark, clock, doc, spinner


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


def render():
    pending = st.session_state.get("pending_reports", [])
    cohort_id = st.session_state.get("current_cohort_id")

    if not pending and st.session_state.get("processing_finished"):
        _cleanup_and_redirect()
        return

    if not pending and not st.session_state.get("batch_running"):
        st.info("No hay informes pendientes para procesar.")
        return

    if not st.session_state.get("batch_running") and not st.session_state.get("batch_ready", False):
        st.session_state["batch_ready"] = True

    total = len(pending)

    if st.session_state.get("batch_ready") and not st.session_state.get("batch_running"):
        _start_batch(pending, cohort_id)
        st.rerun()

    done = st.session_state.get("batch_progress", {}).get("_done", 0) if st.session_state.get("batch_progress") else 0
    meta = f"{done} de {total} informes procesados" if done > 0 else f"{total} informe{'s' if total != 1 else ''} pendiente{'s' if total != 1 else ''}"

    page_hero("Procesando Informes", subtitle="Los informes se están procesando con IA.", meta_items=[meta])

    if st.session_state.get("batch_running"):
        _show_progress(pending, total, cohort_id)

    if st.session_state.get("processing_finished"):
        done_count = st.session_state.get("processing_done_count", 0)
        err_count = st.session_state.get("processing_error_count", 0)
        st.success(f"Procesamiento completado — {done_count} de {total} informes")
        if err_count > 0:
            st.warning(f"Con {err_count} error(es)")
        _cleanup_and_redirect()


def _start_batch(pending, cohort_id):
    api_key = st.session_state.get("api_key", "")
    c6_provider = st.session_state.get("c6_provider", "gemini")
    c6_api_key = api_key
    if c6_provider == "openrouter":
        c6_api_key = os.getenv("OPENROUTER_API_KEY", "")
    provider = st.session_state.get("provider", "gemini")

    for r in pending:
        r["use_pdf"] = (c6_provider == "gemini")
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
    st.session_state["batch_ready"] = False
    st.session_state["_total"] = len(pending)

    thread = threading.Thread(
        target=_run_and_save,
        args=(pending, llm_config, batch_config, progress, cohort_id),
        daemon=True,
    )
    st.session_state["batch_thread"] = thread
    thread.start()


def _show_progress(pending, total, cohort_id):
    progress = st.session_state.get("batch_progress", {})
    thread = st.session_state.get("batch_thread")
    done = progress.get("_done", 0)
    errors = progress.get("_errors", 0)

    pct = done / total if total > 0 else 0
    sp = spinner(40, 40)

    metrics_html = (
        f'<div style="text-align:center;display:flex;gap:24px;justify-content:center">'
        f'<div><div style="font-size:28px;font-weight:700;color:var(--uandes-text)">{done}</div>'
        f'<div style="font-size:12px;color:var(--uandes-text-muted);text-transform:uppercase;letter-spacing:0.5px">Completados</div></div>'
        f'<div><div style="font-size:28px;font-weight:700;color:var(--uandes-text)">{errors}</div>'
        f'<div style="font-size:12px;color:var(--uandes-text-muted);text-transform:uppercase;letter-spacing:0.5px">Errores</div></div>'
        f'</div>'
    )

    detail_html = ""
    is_alive = thread and thread.is_alive() if thread else False
    phase = progress.get("_phase", "processing")

    if phase == "processing" and is_alive:
        detail_parts = []
        for r in pending:
            rid = r["report_id"]
            pdata = progress.get(rid, {})
            stage = pdata.get("stage", "esperando")
            comps_done = pdata.get("comps_done", 0)
            comps_total = pdata.get("total_comps", "?")
            name = r.get("pdf_name", rid[:8])
            stage_markup = _stage_html(stage, comps_done, comps_total)
            detail_parts.append(
                f'<div style="padding:10px 0;border-bottom:1px solid var(--uandes-border-light);display:flex;justify-content:space-between;align-items:center">'
                f'<span style="font-weight:600;font-size:14px">{name}</span>'
                f'<span style="font-size:13px;color:var(--uandes-text-secondary)">{stage_markup}</span>'
                f"</div>"
            )

        if detail_parts:
            section_card("Detalle por Informe")
            for part in detail_parts:
                st.markdown(part, unsafe_allow_html=True)
            section_card_end()

        time.sleep(0.3)
        st.rerun()
    else:
        if not is_alive:
            st.session_state["batch_thread"] = None
        _finish_processing(errors)

    spinner_html = f'<div class="uandes-processing-spinner">{sp}</div>'
    processing_panel(
        "Procesando informes",
        f"{done} de {total} informes procesados",
        pct,
        metrics_html,
        None,
    )
    st.markdown(spinner_html, unsafe_allow_html=True)


def _finish_processing(errors):
    st.session_state["batch_running"] = False
    st.session_state["batch_ready"] = False
    st.session_state["processing_finished"] = True
    done = st.session_state.get("batch_progress", {}).get("_done", 0)
    st.session_state["processing_done_count"] = done
    st.session_state["processing_error_count"] = errors
    st.session_state["pending_reports"] = []
    st.session_state["report_count"] = len(load_index())
    st.rerun()


def _cleanup_and_redirect():
    st.session_state.pop("processing_finished", None)
    st.session_state.pop("batch_running", None)
    st.session_state.pop("batch_ready", None)
    st.session_state.pop("batch_progress", None)
    st.session_state.pop("batch_thread", None)
    st.session_state.pop("processing_done_count", None)
    st.session_state.pop("processing_error_count", None)
    st.session_state["page"] = "cohort_macro"
    st.rerun()


def _run_and_save(pending, llm_config, batch_config, progress, cohort_id):
    try:
        results = run_batch(pending, llm_config, batch_config, progress)
        report_ids = [r.report_id for r in results if r.estado != "error"]
        if report_ids and cohort_id:
            add_reports_to_cohort(cohort_id, report_ids)
    except Exception:
        pass
