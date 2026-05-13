import streamlit as st
from pipeline.persistence import load_report
from pipeline.reportes_export import exportar_reporte_individual
from ui.components import page_hero, section_card, section_card_end, badge


LEVEL_LABELS = {0: "Sin evidencia", 1: "No aplica", 2: "Uso concreto", 3: "Dominio técnico"}
LEVEL_VARIANTS = {0: "red", 1: "yellow", 2: "blue", 3: "green"}


def _nivel_badge_html(nivel: int) -> str:
    label = LEVEL_LABELS.get(nivel, f"Nivel {nivel}")
    variant = LEVEL_VARIANTS.get(nivel, "gray")
    return badge(f"Nivel {nivel}: {label}", variant)


def render():
    report_id = st.session_state.get("selected_report_id")
    report = load_report(report_id) if report_id else None

    if not report:
        st.warning("No se encontró el informe seleccionado.")
        return

    preview = report.vista_preliminar
    tipo = report.tipo_documento.replace("_", " ").title()
    timestamp = report.timestamp[:19] if hasattr(report, "timestamp") and report.timestamp else ""

    meta_items = [tipo]
    if timestamp:
        meta_items.append(timestamp)

    page_hero(
        report.pdf_name,
        subtitle="Evaluación detallada por competencia del informe.",
        meta_items=meta_items,
        back_target="cohort_reports",
    )

    if not preview:
        section_card("Resultados")
        st.info("Este informe no tiene resultados de competencias.")
        section_card_end()
        return

    total = len(preview)
    aprobadas = sum(1 for r in preview if r["nivel"] >= 2)
    no_aprobadas = total - aprobadas
    nivel_prom = sum(r["nivel"] for r in preview) / total if total else 0

    st.markdown(
        '<div class="uandes-metrics-grid">'
        f'<div class="uandes-metric-card"><div class="uandes-metric-label">Competencias Evaluadas</div><div class="uandes-metric-value">{total}</div></div>'
        f'<div class="uandes-metric-card"><div class="uandes-metric-label">Aprobadas</div><div class="uandes-metric-value green">{aprobadas}</div></div>'
        f'<div class="uandes-metric-card"><div class="uandes-metric-label">No Aprobadas</div><div class="uandes-metric-value red">{no_aprobadas}</div></div>'
        f'<div class="uandes-metric-card"><div class="uandes-metric-label">Nivel Promedio</div><div class="uandes-metric-value">{nivel_prom:.2f}</div></div>'
        "</div>",
        unsafe_allow_html=True,
    )

    section_card("Evaluación por Competencia")

    for i, r in enumerate(preview):
        cid = r["competencia_id"]
        nivel = r["nivel"]
        nombre = r.get("competencia_nombre", "")
        nivel_bdg = _nivel_badge_html(nivel)

        with st.expander(f"{cid} — {nombre}", expanded=(i == 0)):
            st.markdown(f"<p>{nivel_bdg}</p>", unsafe_allow_html=True)
            st.markdown(f"**Justificación:** {r.get('justificacion', 'Sin justificación')}")

            secciones = r.get("secciones_fuente", [])
            if secciones:
                st.markdown(f"**Secciones fuente:** {', '.join(secciones)}")

            citas = r.get("citas", [])
            if citas:
                st.markdown("**Citas del informe:**")
                for j, cita in enumerate(citas):
                    st.markdown(f"{j+1}. _{cita}_")

            confianza = r.get("confianza", 0)
            if confianza:
                st.markdown(f"**Confianza:** {confianza:.1%}")

    section_card_end()

    col1, col2, col3 = st.columns(3)
    with col1:
        buf = exportar_reporte_individual(report_id)
        if buf.getvalue():
            st.download_button(
                "Descargar .xlsx",
                data=buf,
                file_name=f"{report.pdf_name.replace('.pdf', '')}_evaluacion.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    with col2:
        if st.button("Volver a informes", use_container_width=True):
            st.session_state.pop("selected_report_id", None)
            st.session_state["page"] = "cohort_reports"
            st.rerun()
    with col3:
        if st.button("Volver a cohorte", use_container_width=True):
            st.session_state.pop("selected_report_id", None)
            st.session_state["page"] = "cohort_macro"
            st.rerun()
