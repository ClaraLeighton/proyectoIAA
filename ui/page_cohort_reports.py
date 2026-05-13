import streamlit as st
from pipeline.cohorts import get_cohort, compute_cohort_macro
from pipeline.persistence import load_report
from ui.components import page_hero, section_card, section_card_end, badge, report_card
from ui.icons import circle_green, circle_yellow, circle_red


def _formatear_tipo(tipo: str) -> str:
    nombre = tipo.replace("_", " ").title()
    nombre = nombre.replace("Pre ", "Pre-")
    nombre = nombre.replace("Practica", "Práctica")
    return nombre


def _nivel_icon(nivel: float) -> str:
    if nivel >= 2.5:
        return circle_green(14, 14)
    elif nivel >= 1.5:
        return circle_yellow(14, 14)
    return circle_red(14, 14)


def render():
    cohort_id = st.session_state.get("selected_cohort_id")
    cohort = get_cohort(cohort_id) if cohort_id else None

    if not cohort:
        st.warning("No se encontró la cohorte.")
        return

    tipo_label = _formatear_tipo(cohort.get("tipo_documento", ""))
    n_reports = len(cohort.get("report_ids", []))

    page_hero(
        "Resultados Micro",
        subtitle=f"Informes individuales de {cohort['name']}",
        meta_items=[
            badge(tipo_label, "outline"),
            f"{n_reports} informe{'s' if n_reports != 1 else ''}",
        ],
        back_target="cohort_macro",
    )

    section_card("Informes")

    search = st.text_input("", placeholder="Buscar informe por nombre...", label_visibility="collapsed")
    q = search.lower().strip() if search else ""

    report_ids = cohort.get("report_ids", [])

    if not report_ids:
        st.info("Esta cohorte no tiene informes aún.")
        section_card_end()
        return

    macro = compute_cohort_macro(cohort_id)

    for rid in reversed(report_ids):
        report = load_report(rid)
        if not report:
            continue
        name = report.pdf_name
        if q and q not in name.lower() and q not in rid.lower():
            continue
        preview = report.vista_preliminar
        nivel = sum(r.get("nivel", 0) for r in preview) / len(preview) if preview else 0
        n_comps = len(preview)

        nivel_html = f'{_nivel_icon(nivel)}{nivel:.1f}'
        comps_bdg = badge(f"{n_comps} competencias", "blue")
        estado_bdg = badge("Completado", "green") if report.estado == "completado" else badge("Error", "red")

        btn_html = f'<button class="uandes-btn uandes-btn-secondary" style="padding:6px 16px;font-size:13px">Ver informe</button>'

        report_card(name, rid[:8], nivel_html, comps_bdg, estado_bdg, btn_html)
        if st.button("Ver informe", key=f"view_report_{rid}", help=name):
            st.session_state["selected_report_id"] = rid
            st.session_state["page"] = "report_detail"
            st.rerun()

    section_card_end()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Volver a cohorte", use_container_width=True):
            st.session_state["page"] = "cohort_config"
            st.rerun()
    with col2:
        if st.button("Cargar más informes", use_container_width=True):
            st.session_state["new_cohort"] = False
            st.session_state["page"] = "upload"
            st.rerun()
