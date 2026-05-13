import streamlit as st
import pandas as pd
from pipeline.persistence import load_index, get_global_stats, load_report, delete_report
from pipeline.reportes_export import exportar_excel_multi_hoja


LEVEL_COLORS = {"0": "#ef4444", "1": "#f97316", "2": "#2e9cdb", "3": "#22c55e"}
LEVEL_LABELS = {"0": "Sin evidencia", "1": "No aplica", "2": "Uso concreto", "3": "Dominio técnico"}


def _nivel_color(nivel: float) -> str:
    if nivel >= 2.5:
        return "#22c55e"
    elif nivel >= 1.5:
        return "#eab308"
    return "#ef4444"


def _render_level_bar(nivel_dist: dict[str, int], total: int) -> str:
    if total == 0:
        return "<i>sin datos</i>"
    segments = []
    for lvl in ["0", "1", "2", "3"]:
        count = nivel_dist.get(lvl, 0)
        pct = count / total * 100
        color = LEVEL_COLORS[lvl]
        if count > 0:
            segments.append(
                f'<div style="display:inline-block;width:{pct:.1f}%;height:24px;'
                f'background:{color};text-align:center;line-height:24px;'
                f'font-size:12px;font-weight:bold;color:white;'
                f'min-width:24px" title="Nivel {lvl}: {count} ({pct:.0f}%)">{count}</div>'
            )
    joined = "".join(segments)
    return (
        f'<div style="display:flex;width:100%;border-radius:6px;overflow:hidden;">{joined}</div>'
    )


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
    col_c.metric("Total Competencias", stats.get("total_competencias_global", 0))

    st.divider()
    st.subheader("Distribución Global de Niveles")

    nivel_dist = stats.get("nivel_distribucion_global", {})
    total_comps = stats.get("total_competencias_global", 0)

    bar_html = _render_level_bar(nivel_dist, total_comps)
    st.html(
        f'<div style="margin:8px 0 4px 0">{bar_html}</div>'
    )
    legend_html = " ".join(
        f'<span style="color:{LEVEL_COLORS[lvl]};font-weight:bold">■</span> '
        f'N{lvl} {nivel_dist.get(lvl,0)} ({nivel_dist.get(lvl,0)/total_comps*100:.0f}%)'
        for lvl in ["0", "1", "2", "3"]
    )
    st.html(
        f'<div style="font-size:14px;color:#555;display:flex;gap:24px;flex-wrap:wrap;">{legend_html}</div>'
    )

    st.divider()
    st.subheader("Reportes Procesados")

    rows = []
    for entry in sorted(index, key=lambda e: e.get("timestamp", ""), reverse=True):
        pct = entry.get("avg_jpc", 0)
        nivel = entry.get("nivel_promedio", 0)
        estado = entry.get("estado", "desconocido")
        rows.append({
            "report_id": entry["report_id"],
            "Informe": entry.get("pdf_name", entry["report_id"][:8]),
            "Tipo": entry.get("tipo_documento", "").replace("_", " "),
            "Fecha": entry.get("timestamp", "")[:19],
            "Comp.": entry.get("total_competencias", 0),
            "JPC": pct,
            "Nivel": nivel,
            "Confianza": entry.get("avg_confianza", 0),
            "Estado": ("✅" if estado == "completado" else "❌") + f" {estado}",
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        st.dataframe(
            df.drop(columns=["report_id"]),
            column_config={
                "JPC": st.column_config.ProgressColumn(
                    "JPC",
                    format=".0%",
                    width="medium",
                    min_value=0,
                    max_value=1,
                ),
                "Nivel": st.column_config.NumberColumn(
                    "Nivel",
                    format="%.1f",
                    width="small",
                ),
                "Confianza": st.column_config.ProgressColumn(
                    "Confianza",
                    format=".0%",
                    width="medium",
                    min_value=0,
                    max_value=1,
                ),
                "Comp.": st.column_config.NumberColumn("Comp.", width="small"),
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
