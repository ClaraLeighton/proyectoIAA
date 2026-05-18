import base64
from pathlib import Path
import streamlit as st
from pipeline.cohorts import get_cohort, compute_cohort_macro
from pipeline.persistence import load_report
from ui.components import page_hero, badge
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


# Helper to get PDF path for a report
def _get_pdf_path(report):
    possible_attrs = ["pdf_path", "file_path", "path", "pdf_file", "document_path"]
    for attr in possible_attrs:
        value = getattr(report, attr, None)
        if value:
            path = Path(value)
            if path.exists():
                return path

    saved_pdf = Path("data/reports") / report.report_id / "report.pdf"
    if saved_pdf.exists():
        return saved_pdf

    possible_dirs = [Path("data/reports"), Path("reports"), Path("uploads"), Path("data/uploads")]
    pdf_name = getattr(report, "pdf_name", "")
    for folder in possible_dirs:
        candidate = folder / pdf_name
        if candidate.exists():
            return candidate

    return None


def _show_pdf_preview_modal(report, rid: str):
    @st.dialog("Previsualización del informe", width="large")
    def modal():
        pdf_name = getattr(report, "pdf_name", "Informe")
        pdf_path = _get_pdf_path(report)

        st.markdown(
            f'<p style="font-size:13px;color:#6B7280;margin-bottom:12px">{pdf_name} &mdash; Previsualización del informe</p>',
            unsafe_allow_html=True,
        )

        if not pdf_path:
            st.warning("No se encontró el archivo PDF asociado a este informe.")
            return

        try:
            pdf_bytes = pdf_path.read_bytes()
            base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
            st.markdown(
                f"""
                <iframe
                    src="data:application/pdf;base64,{base64_pdf}"
                    width="100%"
                    height="650px"
                    style="border: 1px solid #E5E7EB; border-radius: 18px; background: white;"
                ></iframe>
                """,
                unsafe_allow_html=True,
            )
        except Exception:
            st.error("No se pudo cargar la previsualización del PDF.")

    modal()


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

    st.subheader("Informes")

    search = st.text_input("", placeholder="Buscar informe por nombre...", label_visibility="collapsed")
    q = search.lower().strip() if search else ""

    report_ids = cohort.get("report_ids", [])

    if not report_ids:
        st.info("Esta cohorte no tiene informes aún.")
        return

    macro = compute_cohort_macro(cohort_id)

    st.markdown(
        """
        <style>
        .report-card-inner {
            padding: 6px 0;
        }
        .report-card-title {
            font-size: 20px;
            font-weight: 750;
            color: #1F2937;
            line-height: 1.25;
            margin-bottom: 6px;
        }
        .report-card-id {
            font-size: 14px;
            font-weight: 600;
            color: #9CA3AF;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 28px !important;
            border: 1px solid #E2E2E2 !important;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08) !important;
            background: #FFFFFF !important;
            padding: 18px 22px !important;
            margin-bottom: 18px !important;
        }
        div[data-testid="stButton"] > button {
            min-height: 42px;
            border-radius: 14px;
            font-weight: 650;
            white-space: nowrap;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

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

        nivel_html = f'{_nivel_icon(nivel)} {nivel:.1f}'
        comps_bdg = badge(f"{n_comps} competencias", "blue")
        estado_bdg = badge("Completado", "green") if report.estado == "completado" else badge("Error", "red")

        with st.container(border=True):
            info_col, nivel_col, comps_col, estado_col, preview_col, detail_col = st.columns(
                [3.2, 0.75, 1.35, 1.15, 1.05, 1.05],
                vertical_alignment="center",
            )

            with info_col:
                st.markdown(
                    f"""
                    <div class="report-card-inner">
                        <div class="report-card-title">{name}</div>
                        <div class="report-card-id">ID: {rid[:8]}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with nivel_col:
                st.markdown(
                    f'<span style="display:flex;align-items:center;gap:8px;font-size:14px;font-weight:700">{nivel_html}</span>',
                    unsafe_allow_html=True,
                )
            with comps_col:
                st.markdown(comps_bdg, unsafe_allow_html=True)
            with estado_col:
                st.markdown(estado_bdg, unsafe_allow_html=True)
            with preview_col:
                if st.button(
                    "Ver informe",
                    key=f"preview_report_{rid}",
                    help="Abrir previsualización del PDF",
                    use_container_width=True,
                ):
                    _show_pdf_preview_modal(report, rid)
            with detail_col:
                if st.button(
                    "Ver detalle",
                    key=f"view_report_{rid}",
                    help=name,
                    use_container_width=True,
                ):
                    st.session_state["selected_report_id"] = rid
                    st.session_state["page"] = "report_detail"
                    st.rerun()

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
