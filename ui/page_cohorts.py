import streamlit as st
from pipeline.cohorts import list_cohorts, compute_cohort_macro
from ui.components import page_hero, section_card, section_card_end, badge, empty_state


def _formatear_tipo(tipo: str) -> str:
    nombre = tipo.replace("_", " ").title()
    nombre = nombre.replace("Pre ", "Pre-")
    nombre = nombre.replace("Practica", "Práctica")
    return nombre


def render():
    cohorts = list_cohorts()
    n_cohorts = len(cohorts)
    n_total_reports = sum(len(c.get("report_ids", [])) for c in cohorts)

    meta_items = []
    if cohorts:
        meta_items.append(f"{n_cohorts} cohorte{'s' if n_cohorts != 1 else ''} activa{'s' if n_cohorts != 1 else ''}")
        meta_items.append(f"{n_total_reports} informe{'s' if n_total_reports != 1 else ''} procesado{'s' if n_total_reports != 1 else ''}")

    page_hero(
        "Mis Cohortes",
        subtitle="Gestiona, revisa y analiza las cohortes de informes de práctica.",
        meta_items=meta_items if meta_items else None,
    )

    col_cta_spacer = st.columns([4, 1])
    with col_cta_spacer[1]:
        if st.button("+ Nueva Cohorte", type="primary", key="btn_new_cohort", use_container_width=True):
            st.session_state["new_cohort"] = True
            st.session_state["page"] = "upload"
            st.rerun()

    if not cohorts:
        section_card(None)
        empty_state(
            "No hay cohortes aún",
            "Crea tu primera cohorte para comenzar a evaluar informes de práctica.",
        )
        section_card_end()
        return

    for cohort in sorted(cohorts, key=lambda c: c.get("created_at", ""), reverse=True):
        cid = cohort["cohort_id"]
        name = cohort["name"]
        tipo = _formatear_tipo(cohort.get("tipo_documento", ""))
        n_reports = len(cohort.get("report_ids", []))

        macro = compute_cohort_macro(cid)
        g = macro["global"]

        meta = f'{badge(tipo, "outline")} <span class="coh-card-report-count">{n_reports} informe{"s" if n_reports != 1 else ""}</span>'

        score_str = f'{g["score_pct"]:.0%}' if g["total_reportes"] > 0 else "—"
        nivel_str = f'{g["nivel_promedio_global"]:.2f}' if g["total_reportes"] > 0 else "—"

        html = f"""
        <div class="cohort-card" data-cid="{cid}">
          <div class="cohort-card-left">
            <div class="cohort-card-name">{name}</div>
            <div class="cohort-card-meta">{meta}</div>
          </div>
          <div class="cohort-card-stats">
            <div class="cohort-stat">
              <div class="cohort-stat-value">{score_str}</div>
              <div class="cohort-stat-label">Score Global</div>
            </div>
            <div class="cohort-stat">
              <div class="cohort-stat-value">{nivel_str}</div>
              <div class="cohort-stat-label">Nivel Prom.</div>
            </div>
          </div>
          <div class="cohort-card-actions">
            <a class="cohort-btn cohort-btn-secondary" href="?page=cohort_config&cid={cid}" target="_self">Ver cohorte</a>
            <a class="cohort-btn cohort-btn-primary" href="?page=cohort_macro&cid={cid}" target="_self">Resultados</a>
          </div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
