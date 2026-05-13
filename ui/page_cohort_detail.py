import streamlit as st
import pandas as pd

from pipeline.cohorts import get_cohort, compute_cohort_macro
from pipeline.reportes_export import exportar_excel_multi_hoja
from pipeline.persistence import load_report
from ui.components import page_hero, section_card, section_card_end, metric_grid, level_bar_panel, empty_state, badge
from ui.icons import chart, upload, download, trash


LEVEL_COLORS = {"0": "#ef4444", "1": "#f97316", "2": "#2e9cdb", "3": "#22c55e"}
LEVEL_LABELS = {"0": "Sin evidencia", "1": "No aplica", "2": "Uso concreto", "3": "Dominio técnico"}


def _formatear_tipo(tipo: str) -> str:
    nombre = tipo.replace("_", " ").title()
    nombre = nombre.replace("Pre ", "Pre-")
    nombre = nombre.replace("Practica", "Práctica")
    return nombre


def render():
    cohort_id = st.session_state.get("selected_cohort_id")
    cohort = get_cohort(cohort_id) if cohort_id else None

    if not cohort:
        st.warning("No se encontró la cohorte seleccionada.")
        return

    macro = compute_cohort_macro(cohort_id)
    g = macro["global"]
    competencias = macro["competencias"]
    tipo_label = _formatear_tipo(cohort.get("tipo_documento", ""))

    meta_items = [
        badge(tipo_label, "outline"),
        f'{g["total_reportes"]} informe{"s" if g["total_reportes"] != 1 else ""} procesado{"s" if g["total_reportes"] != 1 else ""}',
    ]
    if cohort.get("created_at"):
        meta_items.append(f'Creada: {cohort["created_at"][:10]}')

    breadcrumb = '<a href="#" onclick="alert(\'cohorts\')">Mis Cohortes</a> <span style="color:var(--uandes-text-muted)">/</span> Resultados Macro'

    page_hero(
        "Resultados Macro",
        subtitle=f"Resumen de evaluación de {cohort['name']}",
        meta_items=meta_items,
        back_target="cohort_config",
    )

    if g["total_reportes"] == 0:
        section_card("Resultados")
        empty_state(
            "Sin resultados",
            "Aún no hay informes procesados en esta cohorte.",
        )
        section_card_end()
        return

    metric_grid([
        ("Total Informes", g["total_reportes"]),
        ("Score Global", f'{g["score_pct"]:.1%}', True, f'{g["score_actual"]}/{g["score_max"]}'),
        ("% Aprobación", f'{g["tasa_aprobacion_global"]:.1%}'),
        ("Nivel Promedio", f'{g["nivel_promedio_global"]:.2f}'),
    ])

    nivel_dist = {}
    for c in competencias.values():
        for lvl, count in c["distribucion"].items():
            nivel_dist[lvl] = nivel_dist.get(lvl, 0) + count
    total_comps = sum(nivel_dist.values())

    if total_comps > 0:
        level_bar_panel("Distribución de Niveles", nivel_dist, total_comps, LEVEL_COLORS, LEVEL_LABELS)

    if competencias:
        section_card("Desglose por Competencia")
        rows = []
        for cid in sorted(competencias.keys()):
            c = competencias[cid]
            rows.append({
                "Competencia": cid,
                "Nombre": c.get("nombre", ""),
                "Nivel Prom.": c["nivel_promedio"],
                "% Score": f'{c["score_pct"]:.1%}',
                "% Aprobación": f'{c["tasa_aprobacion"]:.1%}',
                "JPC Prom.": c["jpc_promedio"],
                "Confianza": c["confianza_promedio"],
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        section_card_end()

        section_card("Distribución por Competencia")
        dist_rows = []
        for cid in sorted(competencias.keys()):
            c = competencias[cid]
            d = c["distribucion"]
            dist_rows.append({
                "Competencia": cid,
                "Sin evidencia": d.get("0", 0),
                "No aplica": d.get("1", 0),
                "Uso concreto": d.get("2", 0),
                "Dominio técnico": d.get("3", 0),
            })
        df_dist = pd.DataFrame(dist_rows)
        st.dataframe(df_dist, use_container_width=True, hide_index=True)
        section_card_end()

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("Resultados Micro", use_container_width=True):
            st.session_state["page"] = "cohort_reports"
            st.rerun()
    with col_b:
        if st.button("Agregar más informes", use_container_width=True):
            st.session_state["new_cohort"] = False
            st.session_state["page"] = "upload"
            st.rerun()
    with col_c:
        if st.button("Exportar Excel", use_container_width=True):
            index = [load_report(rid).to_index_entry() for rid in cohort["report_ids"] if load_report(rid)]
            index = [e for e in index if e]
            st.session_state["_export_buf"] = exportar_excel_multi_hoja(index)
            st.session_state["_export_name"] = f"{cohort['name']}_resultados.xlsx"
        if st.session_state.get("_export_buf"):
            st.download_button(
                "Descargar .xlsx",
                data=st.session_state["_export_buf"],
                file_name=st.session_state["_export_name"],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
