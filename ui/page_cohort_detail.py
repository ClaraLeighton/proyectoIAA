import streamlit as st
import pandas as pd
from html import escape

from pipeline.cohorts import get_cohort, compute_cohort_macro
from pipeline.reportes_export import build_export_index, exportar_excel_multi_hoja
from ui.components import page_hero, empty_state, badge


LEVEL_COLORS = {"0": "#ef4444", "1": "#f97316", "2": "#2e9cdb", "3": "#22c55e"}
LEVEL_LABELS = {"0": "Sin evidencia", "1": "No aplica", "2": "Uso concreto", "3": "Dominio técnico"}


def _formatear_tipo(tipo: str) -> str:
    nombre = tipo.replace("_", " ").title()
    nombre = nombre.replace("Pre ", "Pre-")
    nombre = nombre.replace("Practica", "Práctica")
    return nombre


def _macro_dashboard_html(cohort, tipo_label, g, nivel_dist, total_comps, competencias):
    score_pct = max(0, min(100, g["score_pct"] * 100))
    aprob_pct = max(0, min(100, g["tasa_aprobacion_global"] * 100))
    nivel_pct = max(0, min(100, (g["nivel_promedio_global"] / 3) * 100 if g["nivel_promedio_global"] else 0))
    levels = []
    for lvl in ["0", "1", "2", "3"]:
        count = nivel_dist.get(lvl, 0)
        pct = (count / total_comps * 100) if total_comps else 0
        levels.append(
            f'<div class="macro-level-row">'
            f'<div class="macro-level-label"><span style="background:{LEVEL_COLORS[lvl]}"></span>{LEVEL_LABELS[lvl]}</div>'
            f'<div class="macro-level-track"><div style="width:{pct:.1f}%;background:{LEVEL_COLORS[lvl]}"></div></div>'
            f'<div class="macro-level-count">{count}</div>'
            f'</div>'
        )

    top = sorted(
        competencias.items(),
        key=lambda item: item[1].get("score_pct", 0),
        reverse=True,
    )[:4]
    top_rows = []
    for cid, data in top:
        pct = data.get("score_pct", 0) * 100
        top_rows.append(
            f'<div class="macro-rank-row">'
            f'<div><strong>{escape(cid)}</strong><span>{escape(data.get("nombre", "")[:42])}</span></div>'
            f'<em>{pct:.0f}%</em>'
            f'</div>'
        )

    return f"""
    <div class="macro-dashboard">
      <div class="macro-dashboard-main">
        <div>
          <div class="macro-eyebrow">{escape(tipo_label)} · {g["total_reportes"]} informes</div>
          <h2>{escape(cohort["name"])}</h2>
          <p>Lectura agregada del cumplimiento del perfil de egreso, con foco en aprobación, nivel alcanzado y evidencia disponible.</p>
        </div>
        <div class="macro-donut" style="--score:{score_pct:.1f}">
          <div><strong>{score_pct:.0f}%</strong><span>Score global</span></div>
        </div>
      </div>
      <div class="macro-dashboard-grid">
        <div class="macro-color-card red">
          <span>Aprobación</span>
          <strong>{aprob_pct:.1f}%</strong>
          <div class="macro-mini-track"><div style="width:{aprob_pct:.1f}%"></div></div>
        </div>
        <div class="macro-color-card yellow">
          <span>Nivel promedio</span>
          <strong>{g["nivel_promedio_global"]:.2f}/3</strong>
          <div class="macro-mini-track"><div style="width:{nivel_pct:.1f}%"></div></div>
        </div>
        <div class="macro-color-card blue">
          <span>Competencias</span>
          <strong>{g["total_competencias"]}</strong>
          <small>{total_comps} evaluaciones acumuladas</small>
        </div>
      </div>
      <div class="macro-bottom-grid">
        <div class="macro-panel">
          <div class="macro-panel-title">Distribución de niveles</div>
          {''.join(levels)}
        </div>
        <div class="macro-panel">
          <div class="macro-panel-title">Competencias más fuertes</div>
          {''.join(top_rows) if top_rows else '<p>Sin competencias disponibles.</p>'}
        </div>
      </div>
    </div>
    """


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
        st.subheader("Resultados")
        empty_state(
            "Sin resultados",
            "Aún no hay informes procesados in esta cohorte.",
        )
        return

    nivel_dist = {}
    for c in competencias.values():
        for lvl, count in c["distribucion"].items():
            nivel_dist[lvl] = nivel_dist.get(lvl, 0) + count
    total_comps = sum(nivel_dist.values())

    with st.container(border=True):
        st.markdown(
            _macro_dashboard_html(cohort, tipo_label, g, nivel_dist, total_comps, competencias),
            unsafe_allow_html=True,
        )
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
            export_index = build_export_index(cohort.get("report_ids", []))
            st.download_button(
                "Exportar Excel",
                data=exportar_excel_multi_hoja(export_index),
                file_name=f"{cohort['name']}_resultados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"macro_export_{cohort_id}",
                use_container_width=True,
            )

    if competencias:
        st.subheader("Desglose por Competencia")
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
        with st.container(border=True):
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.subheader("Distribución por Competencia")
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
        with st.container(border=True):
            st.dataframe(df_dist, use_container_width=True, hide_index=True)
