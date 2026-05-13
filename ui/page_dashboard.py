import streamlit as st
import pandas as pd
from pipeline.persistence import load_index, get_global_stats, load_report, delete_report
from pipeline.reportes_export import exportar_excel_multi_hoja


def _colored_bar(pct: float, max_width: int = 200) -> str:
    color = "#22c55e" if pct >= 0.7 else "#eab308" if pct >= 0.4 else "#ef4444"
    fill = int(pct * max_width)
    return f"""
    <div style="width:{max_width}px;height:18px;background:#e5e7eb;border-radius:4px;overflow:hidden;">
      <div style="width:{fill}px;height:100%;background:{color};border-radius:4px;"></div>
    </div>
    """


def _nivel_color(nivel: float) -> str:
    if nivel >= 2.5:
        return "#22c55e"
    elif nivel >= 1.5:
        return "#eab308"
    return "#ef4444"


def render():
    st.title("Dashboard Global de Evaluaciones")

    index = load_index()
    stats = get_global_stats()

    if not index:
        st.info("No hay informes procesados. Ve a 'Cargar Archivos' para comenzar.")
        if st.button("Ir a Carga", width="stretch"):
            st.session_state["page"] = "upload"
            st.rerun()
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Informes", stats.get("total_reports", 0))
    col2.metric("Completados", stats.get("completados", 0))
    col3.metric("Errores", stats.get("errores", 0))
    col4.metric("Avg JPC Global", f"{stats.get('avg_jpc_global', 0):.2%}")

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Avg Confianza", f"{stats.get('avg_confianza_global', 0):.2%}")
    col_b.metric("Avg Nivel", stats.get("avg_nivel_global", 1))
    col_c.metric("Total Competencias", sum(e.get("total_competencias", 0) for e in index))

    st.divider()
    st.subheader("Reportes Procesados")

    rows = []
    for entry in sorted(index, key=lambda e: e.get("timestamp", ""), reverse=True):
        pct = entry.get("avg_jpc", 0)
        nivel = entry.get("nivel_promedio", 0)
        estado = entry.get("estado", "desconocido")
        error = entry.get("error")
        rows.append({
            "report_id": entry["report_id"],
            "Informe": entry.get("pdf_name", entry["report_id"][:8]),
            "Tipo": entry.get("tipo_documento", "").replace("_", " "),
            "Fecha": entry.get("timestamp", "")[:19],
            "Comp.": entry.get("total_competencias", 0),
            "JPC": f"{pct:.0%}",
            "JPC_bar": _colored_bar(pct),
            "Nivel": f"{nivel:.1f}",
            "Nivel_color": f'<span style="color:{_nivel_color(nivel)};font-weight:bold">{nivel:.1f}</span>',
            "Confianza": f"{entry.get('avg_confianza', 0):.0%}",
            "Estado": ("✅" if estado == "completado" else "❌") + f" {estado}",
            "_error": error or "",
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        display_cols = ["Informe", "Tipo", "Fecha", "Comp.", "JPC", "JPC_bar", "Nivel_color", "Confianza", "Estado"]
        col_map = {
            "JPC_bar": "JPC (bar)",
            "Nivel_color": "Nivel",
        }
        st.html(
            "<style>"
            "td:has(> div) { padding: 2px 8px !important; }"
            ".stHtml { overflow-x: auto; }"
            "</style>"
        )
        st.dataframe(
            df[display_cols].rename(columns=col_map),
            column_config={
                "JPC (bar)": st.column_config.TextColumn("JPC (bar)"),
                "Nivel": st.column_config.TextColumn("Nivel"),
            },
            width="stretch",
            hide_index=True,
        )

    st.divider()
    st.subheader("Acciones")

    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        if st.button("Exportar Excel (multi-hoja)", width="stretch"):
            buf = exportar_excel_multi_hoja(index)
            st.download_button(
                "Descargar Excel",
                data=buf,
                file_name="evaluacion_global.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )
    with col_dl2:
        report_ids = {e["report_id"]: e.get("pdf_name", e["report_id"][:8]) for e in index}
        selected = st.selectbox(
            "Ver detalle de informe:",
            options=list(report_ids.keys()),
            format_func=lambda rid: report_ids[rid],
            key="dashboard_report_selector",
        )
        if selected and st.button("Ver Detalle", width="stretch"):
            st.session_state["selected_report_id"] = selected
            st.session_state["page"] = "resultados"
            st.rerun()

    with st.expander("Eliminar informes", expanded=False):
        to_delete = st.selectbox(
            "Seleccionar informe a eliminar:",
            options=[""] + list(report_ids.keys()),
            format_func=lambda rid: report_ids.get(rid, "Seleccionar...") if rid else "Seleccionar...",
        )
        if to_delete and st.button("Eliminar", type="secondary", width="stretch"):
            delete_report(to_delete)
            st.success(f"Informe {report_ids.get(to_delete, to_delete)} eliminado.")
            st.rerun()
