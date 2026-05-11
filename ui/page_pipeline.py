import os
import re
import streamlit as st
from pipeline.orchestrator import ejecutar_pipeline_completo, procesar_ajuste, actualizar_competencia_manual


def render():
    st.title("Pipeline de Evaluación")

    if "pipeline_iniciado" not in st.session_state:
        st.session_state["pipeline_iniciado"] = False

    if not st.session_state["pipeline_iniciado"]:
        st.info("Haz clic en 'Ejecutar Pipeline' para comenzar la evaluación automatizada.")

        col1, col2 = st.columns(2)
        with col1:
            top_k = st.number_input("Top-K fragmentos", min_value=1, max_value=20, value=5)
        with col2:
            umbral = st.slider("Umbral de similitud", min_value=0.0, max_value=1.0, value=0.45, step=0.05)

        st.caption(f"Embeddings: **{st.session_state.get('provider', 'gemini').title()}**  |  C6: **{st.session_state.get('c6_provider', 'gemini').title()}**")

        use_pdf = False
        if st.session_state.get("c6_provider") == "gemini":
            st.caption("PDF en C6 activo")
            use_pdf = True

        if st.button("Ejecutar Pipeline", type="primary", use_container_width=True):
            progress_bar = st.progress(0)

            stages_order = ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
            stage_labels = {
                "C1": "Ingesta del PDF + matriz + rúbrica",
                "C2": "Parseo de secciones del documento",
                "C3": "Fragmentación (chunking) del texto",
                "C4": "Generación de embeddings",
                "C5": "Recuperación de evidencia",
                "C6": "Evaluación LLM",
                "C7": "Generación de reporte",
            }
            boxes = {}
            c6_output_placeholder = None
            for s in stages_order:
                if s == "C6":
                    with st.status(f"**{s}**: {stage_labels[s]}", state="running", expanded=True) as box:
                        c6_output_placeholder = st.empty()
                        boxes[s] = box
                else:
                    boxes[s] = st.status(f"**{s}**: {stage_labels[s]}", state="running")

            last_stage = None
            loop_stages = {"C4", "C5", "C6"}

            def output_callback(stage, raw_output):
                if stage == "C6" and raw_output and c6_output_placeholder:
                    c6_output_placeholder.code(raw_output[:3000], language="json")

            def progress_callback(stage, message):
                nonlocal last_stage
                if stage != last_stage:
                    if last_stage and last_stage in boxes and last_stage not in loop_stages:
                        boxes[last_stage].update(
                            state="complete",
                            label=f"✅ **{last_stage}**: {stage_labels[last_stage]} — Completado",
                        )
                    last_stage = stage
                    boxes[stage].update(state="running", label=f"🔄 **{stage}**: {message}")
                else:
                    boxes[stage].update(label=f"🔄 **{stage}**: {message}")

                m = re.search(r'\((\d+)/(\d+)\)', message)
                if m:
                    i, n = int(m.group(1)), int(m.group(2))
                    if stage == "C4":
                        p = 0.35 + (i - 1) / n * 0.10
                    elif stage == "C5":
                        p = 0.45 + (i - 1) / n * 0.25
                    elif stage == "C6":
                        if "✓" in message:
                            p = 0.70 + i / n * 0.25
                        else:
                            p = 0.70 + (i - 1) / n * 0.25
                    else:
                        p = 0.0
                else:
                    p = {"C1": 0.05, "C2": 0.15, "C3": 0.25, "C4": 0.35}.get(stage, 0.0)
                progress_bar.progress(min(p, 1.0))

            try:
                api_key = st.session_state.get("api_key", "")
                if not api_key:
                    st.error("API Key para embeddings no configurada. Verifica en el panel lateral.")
                    return

                c6_provider = st.session_state.get("c6_provider", "gemini")
                if c6_provider == "openrouter":
                    c6_key = st.session_state.get("openrouter_key_input", "")
                    if not c6_key:
                        c6_key = os.getenv("OPENROUTER_API_KEY", "")
                    if not c6_key:
                        st.error("API Key de OpenRouter no configurada. Verifica en el panel lateral.")
                        return
                elif c6_provider == "openai":
                    c6_key = st.session_state.get("api_key", "")
                else:
                    c6_key = api_key

                result = ejecutar_pipeline_completo(
                    pdf_bytes=st.session_state["pdf_bytes"],
                    api_key=api_key,
                    csv_bytes=st.session_state.get("csv_bytes"),
                    json_bytes=st.session_state.get("json_bytes"),
                    provider=st.session_state.get("provider", "gemini"),
                    c6_provider=c6_provider,
                    c6_api_key=c6_key,
                    use_pdf=use_pdf,
                    top_k=top_k,
                    umbral=umbral,
                    progress_callback=progress_callback,
                    output_callback=output_callback,
                )
                progress_bar.progress(1.0)
                for s in stages_order:
                    boxes[s].update(
                        state="complete",
                        label=f"✅ **{s}**: {stage_labels[s]} — Completado",
                    )
                st.session_state["pipeline_state"] = result
                st.session_state["pipeline_iniciado"] = True
                st.rerun()
            except Exception as e:
                if last_stage and last_stage in boxes:
                    boxes[last_stage].update(
                        state="error",
                        label=f"❌ **{last_stage}**: {stage_labels.get(last_stage, '')} — Error",
                    )
                st.error(f"Error durante la ejecución del pipeline: {e}")
                return
        return

    state = st.session_state["pipeline_state"]
    c7 = state["c7"]
    preview = c7["vista_preliminar"]["resultados_competencias"]
    reporte = c7["reporte_procesamiento"]
    c1 = state["c1"]

    st.success(f"Documento detectado: **{c1['tipo_documento']}**")

    total = len(preview)
    aprobadas = sum(1 for r in preview if r["estado_revision"] == "respaldo_suficiente")
    pendientes = sum(1 for r in preview if r["estado_revision"] in ("requiere_revision", "sin_evidencia"))

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Competencias", total)
    col2.metric("Respaldo Suficiente", aprobadas, delta_color="off")
    col3.metric("Requiere Revisión", pendientes, delta_color="inverse")

    st.divider()
    st.subheader("Revisión por Competencia (HITL)")

    for i, r in enumerate(preview):
        cid = r["competencia_id"]
        nivel = r["nivel"]
        label = r["nivel_label"]
        estado_icono = {"pendiente": "", "aprobada": "✅", "rechazada": "❌", "modificada": "✏️"}.get(r.get("estado_final", "pendiente"), "")
        with st.expander(f"{cid} - {r['competencia_nombre']} (Nivel {nivel}: {label})", expanded=True):
            if estado_icono:
                hdr_cols = st.columns([6, 1])
                with hdr_cols[1]:
                    st.markdown(f"## {estado_icono}")
            col_a, col_b = st.columns([3, 1])
            with col_a:
                estado = r["estado_revision"]
                if estado == "respaldo_suficiente":
                    st.success(f"Estado: Respaldo Suficiente")
                elif estado == "requiere_revision":
                    st.warning(f"Estado: Requiere Revisión")
                else:
                    st.error(f"Estado: Sin Evidencia")

                st.markdown(f"**Nivel Asignado:** {nivel} - {label}")
                st.markdown(f"**Justificación:** {r['justificacion']}")
                st.markdown(f"**Secciones Fuente:** {', '.join(r['secciones_fuente'])}")

                if r["citas"]:
                    st.markdown("**Citas:**")
                    for j, cita in enumerate(r["citas"]):
                        st.markdown(f"{j+1}. _{cita}_")

                p = r.get("p", [])
                if p:
                    p_str = " ".join(f"N{i}={v:.2f}" for i, v in enumerate(p))
                    st.markdown(f"**Confianza:** {r.get('confianza', 0):.2%}")
                    st.markdown(f"**p:** {p_str}")

                raw = r.get("raw_response", "")
                if raw:
                    with st.expander("Ver respuesta LLM raw", expanded=False):
                        st.code(raw, language="json")

            with col_b:
                st.markdown("**Acciones**")
                if st.button("Aceptar", key=f"accept_{i}_{cid}"):
                    actualizar_competencia_manual(state, cid, "estado_final", "aprobada")
                    st.rerun()
                if st.button("Rechazar", key=f"reject_{i}_{cid}"):
                    actualizar_competencia_manual(state, cid, "estado_final", "rechazada")
                    st.rerun()

            st.markdown("---")
            st.markdown("**Modificar**")
            col_c, col_d = st.columns([3, 1])
            with col_c:
                nuevo_nivel = st.number_input(
                    "Nuevo nivel",
                    min_value=0,
                    max_value=st.session_state.get("_max_nivel", 3),
                    value=nivel,
                    key=f"nivel_{i}_{cid}",
                )
                solicitud = st.text_input(
                    "Solicitud de ajuste",
                    placeholder="Ej: cambiar nivel a 2, agregar cita...",
                    key=f"req_{i}_{cid}",
                )
            with col_d:
                if st.button("Aplicar Cambio", key=f"apply_{i}_{cid}"):
                    if solicitud.strip():
                        with st.spinner("Procesando ajuste..."):
                            api_key = st.session_state.get("api_key", "")
                            state = procesar_ajuste(state, solicitud, cid, api_key=api_key)
                            st.session_state["pipeline_state"] = state
                            st.success(f"Ajuste aplicado a {cid}.")
                            st.rerun()
                    elif nuevo_nivel != nivel:
                        actualizar_competencia_manual(state, cid, "nivel", nuevo_nivel)
                        actualizar_competencia_manual(state, cid, "estado_final", "modificada")
                        st.success(f"Nivel de {cid} actualizado a {nuevo_nivel}.")
                        st.rerun()
                    else:
                        st.info("No se detectaron cambios.")

    st.divider()
    st.subheader("Resumen de Revisión")
    estados = [r.get("estado_final", "pendiente") for r in preview]
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Aprobadas", estados.count("aprobada"))
    col_b.metric("Modificadas", estados.count("modificada"))
    col_c.metric("Rechazadas", estados.count("rechazada"))
    col_d.metric("Pendientes", estados.count("pendiente"))

    if st.button("Ir a Resultados", type="primary", use_container_width=True):
        st.session_state["page"] = "resultados"
        st.rerun()
