import os
import threading
import streamlit as st
from pipeline.models import BatchConfig
from pipeline.batch_orchestrator import run_batch
from pipeline.persistence import load_index, get_global_stats


def render():
    st.title("Pipeline de Evaluación — Procesamiento Batch")

    pending = st.session_state.get("pending_reports", [])
    index = load_index()
    total_already = len(index)

    if not pending:
        st.info("No hay informes pendientes. Ve a 'Cargar Archivos' para subir PDFs.")

        if total_already > 0:
            st.markdown(f"Hay **{total_already}** informe(s) ya procesados en disco.")
            if st.button("Ir al Dashboard", width="stretch"):
                st.session_state["page"] = "dashboard"
                st.rerun()
        return

    st.markdown(f"### Informes listos para procesar: **{len(pending)}**")
    pending_df_data = []
    for i, r in enumerate(pending):
        pending_df_data.append({
            "#": i + 1,
            "Informe": r.get("pdf_name", f"Reporte {i+1}"),
            "Tipo": r.get("tipo_documento", "").replace("_", " "),
        })
    st.dataframe(pending_df_data, width="stretch")

    col1, col2, col3 = st.columns(3)
    with col1:
        max_workers = st.number_input("Workers paralelos", min_value=1, max_value=20, value=5)
    with col2:
        semaphore = st.number_input("LLM calls simultáneas", min_value=1, max_value=20, value=5)
    with col3:
        max_per_batch = st.number_input("Máx por batch", min_value=1, max_value=50, value=10)

    if "batch_running" not in st.session_state:
        st.session_state["batch_running"] = False
    if "batch_progress" not in st.session_state:
        st.session_state["batch_progress"] = None
    if "batch_thread" not in st.session_state:
        st.session_state["batch_thread"] = None

    if st.button("Ejecutar Pipeline Batch", type="primary", width="stretch", disabled=st.session_state["batch_running"]):
        api_key = st.session_state.get("api_key", "")
        if not api_key:
            st.error("API Key para embeddings no configurada.")
            return

        c6_provider = st.session_state.get("c6_provider", "gemini")
        c6_api_key = api_key
        if c6_provider == "openrouter":
            c6_api_key = st.session_state.get("openrouter_key_input", "") or os.getenv("OPENROUTER_API_KEY", "")
            if not c6_api_key:
                st.error("API Key de OpenRouter no configurada.")
                return

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
        batch_config = BatchConfig(
            max_workers=max_workers,
            max_reports_per_batch=max_per_batch,
            semaphore_limit=semaphore,
        )

        progress = {}
        st.session_state["batch_progress"] = progress
        st.session_state["batch_running"] = True

        thread = threading.Thread(
            target=run_batch,
            args=(pending, llm_config, batch_config, progress),
            daemon=True,
        )
        st.session_state["batch_thread"] = thread
        thread.start()
        st.rerun()

    if st.session_state["batch_running"]:
        progress = st.session_state.get("batch_progress", {})
        thread = st.session_state.get("batch_thread")
        total = progress.get("_total", len(pending))
        done = progress.get("_done", 0)
        errors = progress.get("_errors", 0)
        phase = progress.get("_phase", "processing")

        pct = done / total if total > 0 else 0
        st.progress(pct, text=f"{done}/{total} informes completados")

        col_a, col_b = st.columns(2)
        col_a.metric("Completados", done)
        col_b.metric("Errores", errors)

        is_alive = thread and thread.is_alive() if thread else False

        if phase == "processing":
            with st.expander("Progreso por informe", expanded=True):
                for r in pending:
                    rid = r["report_id"]
                    pname = r.get("pdf_name", rid[:8])
                    pdata = progress.get(rid, {})
                    stage = pdata.get("stage", "esperando")
                    comps_done = pdata.get("comps_done", 0)
                    comps_total = pdata.get("total_comps", "?")
                    st.markdown(f"**{pname}**: {stage}  ({comps_done}/{comps_total} competencias)")

        if phase == "processing" and is_alive:
            st.rerun()
        else:
            st.session_state["batch_running"] = False
            st.session_state["batch_thread"] = None
            st.session_state["pending_reports"] = []
            st.session_state["report_count"] = len(load_index())

            if errors:
                st.warning(f"Procesamiento completado con {errors} error(es).")
            else:
                st.success("Procesamiento batch completado exitosamente.")
            if st.button("Ir al Dashboard", type="primary", width="stretch"):
                st.session_state["page"] = "dashboard"
                st.rerun()
