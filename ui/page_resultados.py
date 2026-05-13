import streamlit as st
import pandas as pd
from pipeline.persistence import load_report, load_index
from pipeline import c6_evaluador
from pipeline.reportes_export import exportar_reporte_individual


def _mostrar_competencias(report):
    c7 = report.c7
    preview = report.vista_preliminar
    reporte = report.reporte_procesamiento

    if not preview:
        st.info("No hay resultados de competencias disponibles.")
        return

    st.success(f"Reporte: **{report.pdf_name}**  |  Tipo: {report.tipo_documento.replace('_', ' ').title()}")
    st.caption(f"Procesado el {report.timestamp[:19]}  |  ID: {report.report_id}")

    total = len(preview)
    aprobadas = sum(1 for r in preview if r["nivel"] >= 2)
    st.metric("APROBADAS", f"{aprobadas} / {total}")

    trazabilidad = reporte.get("trazabilidad_competencias", [])
    if trazabilidad:
        df_traz = pd.DataFrame(trazabilidad)
        cols = [c for c in ["competencia_id", "estado_cobertura", "nivel_asignado", "JPC", "C_cobertura_citas", "S_pertinencia_seccion", "R_similitud_promedio", "F_confianza", "estado_final"] if c in df_traz.columns]
        if cols:
            st.subheader("Trazabilidad por Competencia")
            st.dataframe(df_traz[cols], width="stretch", hide_index=True)

    tiempos = reporte.get("tiempos", {})
    if tiempos:
        st.subheader("Tiempos de Procesamiento")
        tc = st.columns(4)
        labels = ["Auto (min)", "Revisión (min)", "Ajustes (min)", "IA Total (min)"]
        keys = ["T_procesamiento_automatico_min", "T_revision_humana_min", "T_ajustes_min", "T_IA_total_min"]
        for col, label, key in zip(tc, labels, keys):
            val = tiempos.get(key)
            if val is not None:
                col.metric(label, f"{val:.2f}")

    st.divider()
    st.subheader("Detalle por Competencia")
    levels, _ = c6_evaluador._extract_levels(report.pipeline_state["c1"]["config_activa"])

    for r in preview:
        cid = r["competencia_id"]
        nivel = r["nivel"]
        label = levels.get(nivel, f"Nivel {nivel}")
        with st.expander(f"{cid} - {r['competencia_nombre']} (Nivel {nivel}: {label})", expanded=False):
            if nivel >= 2:
                st.success(f"Nivel {nivel}: {label}")
            else:
                st.error(f"Nivel {nivel}: {label}")
            st.markdown(f"**Justificación:** {r['justificacion']}")
            st.markdown(f"**Secciones Fuente:** {', '.join(r['secciones_fuente'])}")
            if r["citas"]:
                st.markdown("**Citas:**")
                for j, cita in enumerate(r["citas"]):
                    st.markdown(f"{j+1}. _{cita}_")
            p = r.get("p", [])
            if p:
                conf = r.get("confianza", 0)
                st.markdown(f"**Confianza:** {conf:.2%}  |  **p:** {' '.join(f'N{i}={v:.2f}' for i, v in enumerate(p))}")
            raw = r.get("raw_response", "")
            if raw:
                with st.expander("Ver respuesta LLM raw", expanded=False):
                    st.code(raw, language="json")

    st.divider()
    historial = reporte.get("historial_ajustes", [])
    if historial:
        st.subheader("Historial de Ajustes")
        st.dataframe(pd.DataFrame(historial), width="stretch")

    buf = exportar_reporte_individual(report.report_id)
    if buf.getvalue():
        st.download_button(
            "Exportar Excel Individual",
            data=buf,
            file_name=f"{report.pdf_name.replace('.pdf', '')}_evaluacion.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )


def render():
    st.title("Historial de Reportes")

    index = load_index()
    selected_id = st.session_state.get("selected_report_id")

    if selected_id:
        report = load_report(selected_id)
        if report:
            _mostrar_competencias(report)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Ir a Revisión (HITL)", width="stretch"):
                    st.session_state["revision_report_id"] = selected_id
                    st.session_state["page"] = "admin"
                    st.rerun()
            with col2:
                if st.button("← Volver al listado", width="stretch"):
                    st.session_state.pop("selected_report_id", None)
                    st.rerun()
            return
        else:
            st.warning("Reporte no encontrado en disco.")
            st.session_state.pop("selected_report_id", None)

    if not index:
        st.info("No hay informes procesados. Ve a 'Cargar Archivos' para comenzar.")
        if st.button("Ir a Carga de Archivos", width="stretch"):
            st.session_state["page"] = "upload"
            st.rerun()
        return

    st.markdown(f"**{len(index)}** reporte(s) guardados en disco. Selecciona uno para ver sus resultados.")

    search = st.text_input("🔍 Buscar por nombre de archivo:", placeholder="Filtrar reportes...")
    filtered = index
    if search:
        q = search.lower()
        filtered = [e for e in index if q in e.get("pdf_name", "").lower() or q in e.get("report_id", "").lower()]

    cols = st.columns([1, 2, 1, 1, 1])
    cols[0].markdown("**Estado**")
    cols[1].markdown("**Informe**")
    cols[2].markdown("**Tipo**")
    cols[3].markdown("**Nivel**")
    cols[4].markdown("**Acción**")

    for entry in sorted(filtered, key=lambda e: e.get("timestamp", ""), reverse=True):
        rid = entry["report_id"]
        pname = entry.get("pdf_name", rid[:8])
        tipo = entry.get("tipo_documento", "").replace("_", " ").title()
        nivel = entry.get("nivel_promedio", 0)
        fecha = entry.get("timestamp", "")[:19]
        estado = entry.get("estado", "desconocido")

        icono = "✅" if estado == "completado" else "❌"
        st_cols = st.columns([1, 2, 1, 1, 1])
        with st_cols[0]:
            st.markdown(f"{icono}")
        with st_cols[1]:
            st.markdown(f"**{pname}**  ")
            st.caption(fecha)
        with st_cols[2]:
            st.markdown(tipo)
        with st_cols[3]:
            st.markdown(f"{nivel:.1f}")
        with st_cols[4]:
            if st.button("Ver", key=f"sel_{rid}", width="stretch"):
                st.session_state["selected_report_id"] = rid
                st.rerun()
