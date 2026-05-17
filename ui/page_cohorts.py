import streamlit as st
from pipeline.cohorts import list_cohorts, compute_cohort_macro, delete_cohort
from ui.components import page_hero, section_card, section_card_end, badge, empty_state
from ui.icons import eye, chart, trash


def _formatear_tipo(tipo: str) -> str:
    nombre = tipo.replace("_", " ").title()
    nombre = nombre.replace("Pre ", "Pre-")
    nombre = nombre.replace("Practica", "Práctica")
    return nombre


def render():
    if st.session_state.pop("_action", None) == "delete_cohort":
        cid_to_delete = st.session_state.pop("_action_cid", "")
        all_cohorts = list_cohorts()
        target = next((c for c in all_cohorts if c["cohort_id"] == cid_to_delete), None)
        if target:
            section_card(None)
            n = len(target.get("report_ids", []))
            st.warning(f"¿Eliminar la cohorte **'{target['name']}'** y sus **{n}** informe{'s' if n != 1 else ''}? Esta acción no se puede deshacer.")
            col1, col2, _ = st.columns([1, 1, 4])
            with col1:
                if st.button("Sí, eliminar", type="primary", key="confirm_del"):
                    delete_cohort(cid_to_delete)
                    st.success("Cohorte eliminada.")
                    st.rerun()
            with col2:
                if st.button("Cancelar", key="cancel_del"):
                    st.rerun()
            section_card_end()
            st.markdown("---")

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

    st.markdown('<div style="display:flex;justify-content:flex-end;margin-bottom:24px">', unsafe_allow_html=True)
    if st.button("+ Nueva Cohorte", type="primary", key="btn_new_cohort"):
        st.session_state["new_cohort"] = True
        st.session_state["page"] = "upload"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

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

        eye_svg = eye(18, 18)
        chart_svg = chart(18, 18, "#fff")
        trash_svg = trash(18, 18, "#CE0019")

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
            <a class="cohort-btn cohort-btn-icon" href="?page=cohort_config&cid={cid}" target="_self" title="Ver cohorte">{eye_svg}</a>
            <a class="cohort-btn cohort-btn-icon cohort-btn-icon-primary" href="?page=cohort_macro&cid={cid}" target="_self" title="Resultados">{chart_svg}</a>
            <a class="cohort-btn cohort-btn-icon cohort-btn-icon-danger" href="?page=cohorts&cid={cid}&action=delete_cohort" target="_self" title="Eliminar cohorte">{trash_svg}</a>
          </div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
