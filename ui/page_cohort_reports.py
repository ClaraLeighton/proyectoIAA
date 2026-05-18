import base64
from pathlib import Path
from html import escape
from textwrap import dedent
import streamlit as st
from pipeline.cohorts import get_cohort
from pipeline.persistence import load_report
from ui.components import page_hero, badge
from ui.icons import search, file_text


LEVEL_COLORS = {"0": "#ef4444", "1": "#f97316", "2": "#2e9cdb", "3": "#22c55e"}
LEVEL_LABELS = {"0": "Sin evidencia", "1": "No aplica", "2": "Uso concreto", "3": "Dominio técnico"}


def _formatear_tipo(tipo: str) -> str:
    nombre = tipo.replace("_", " ").title()
    nombre = nombre.replace("Pre ", "Pre-")
    nombre = nombre.replace("Practica", "Práctica")
    return nombre


def _html_block(template: str) -> str:
    return "".join(line.strip() for line in dedent(template).splitlines())


def _report_stats(report) -> dict:
    preview = report.vista_preliminar or []
    total = len(preview)
    aprobadas = sum(1 for r in preview if r.get("nivel", 0) >= 2)
    nivel_prom = sum(r.get("nivel", 0) for r in preview) / total if total else 0
    confianza = sum(r.get("confianza", 0) for r in preview) / total if total else 0
    aprob_pct = aprobadas / total if total else 0
    dist = {"0": 0, "1": 0, "2": 0, "3": 0}
    for r in preview:
        dist[str(int(r.get("nivel", 0)))] = dist.get(str(int(r.get("nivel", 0))), 0) + 1
    if report.estado != "completado":
        estado = ("Error", "risk")
    elif aprob_pct >= 0.70 and nivel_prom >= 1.8:
        estado = ("Sobresaliente", "ok")
    elif aprob_pct < 0.50 or confianza < 0.50:
        estado = ("Requiere revisión", "risk")
    else:
        estado = ("En rango", "mid")
    return {
        "total": total,
        "aprobadas": aprobadas,
        "nivel_prom": nivel_prom,
        "confianza": confianza,
        "aprob_pct": aprob_pct,
        "dist": dist,
        "estado_label": estado[0],
        "estado_cls": estado[1],
    }


def _level_strip(dist: dict, total: int) -> str:
    if total == 0:
        return '<div class="micro-level-strip empty"></div>'
    parts = []
    for lvl in ["0", "1", "2", "3"]:
        count = dist.get(lvl, 0)
        if not count:
            continue
        pct = count / total * 100
        parts.append(
            f'<span style="width:{pct:.1f}%;background:{LEVEL_COLORS[lvl]}" '
            f'title="{LEVEL_LABELS[lvl]}: {count}">{count}</span>'
        )
    return f'<div class="micro-level-strip">{"".join(parts)}</div>'


def _report_card_html(report, rid: str, stats: dict, cohort_id: str = "") -> str:
    timestamp = getattr(report, "timestamp", "")[:10]
    cid_param = f"&cid={cohort_id}" if cohort_id else ""
    return _html_block(f"""
    <div class="micro-report-row {stats["estado_cls"]}">
      <div class="micro-report-main">
        <div class="micro-report-status">{escape(stats["estado_label"])}</div>
        <h3>{escape(report.pdf_name)}</h3>
        <div class="micro-report-meta">ID {escape(rid[:8])}{f" · {escape(timestamp)}" if timestamp else ""}</div>
      </div>
      <div class="micro-report-actions-container">
        <a href="?page=report_detail&selected_report_id={rid}&cid={cohort_id}" target="_self" class="cohort-btn cohort-btn-icon" title="Ver detalle de {escape(report.pdf_name)}">
            {search(18, 18, "currentColor")}
        </a>
        <a href="?page=cohort_reports&action=preview_pdf&selected_report_id={rid}&cid={cohort_id}" target="_self" class="cohort-btn cohort-btn-icon" title="Ver informe PDF de {escape(report.pdf_name)}">
            {file_text(18, 18, "currentColor")}
        </a>
      </div>
      <div class="micro-report-approved"><strong>{stats["aprobadas"]}/{stats["total"]}</strong><span>competencias aprobadas</span></div>
    </div>
    """)


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
    cohort_id = st.session_state.get("selected_cohort_id") or ""
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
        back_target="cohort_config",
    )

    report_ids = cohort.get("report_ids", [])

    if not report_ids:
        st.info("Esta cohorte no tiene informes aún.")
        return

    reports = []
    for rid in report_ids:
        report = load_report(rid)
        if not report:
            continue
        stats = _report_stats(report)
        reports.append({"rid": rid, "report": report, "stats": stats})

    st.markdown(
        _html_block(f"""
        <div class="micro-list-intro">
          <span class="uandes-badge-tipo">{escape(cohort["name"])}</span>
          <h2>Informes individuales</h2>
          <p>Listado simple de informes. Usa búsqueda y filtros para encontrar entregas que requieren revisión.</p>
        </div>
        """),
        unsafe_allow_html=True,
    )

    filter_col, sort_col = st.columns([1, 1])
    with filter_col:
        search_val = st.text_input("Buscar informe", placeholder="Buscar informe por nombre o ID...", label_visibility="collapsed")
    with sort_col:
        view_filter = st.selectbox(
            "Filtro",
            ["Todos", "Requieren revisión", "Sobresalientes", "Completados", "Errores"],
            label_visibility="collapsed",
        )
    sort = st.radio(
        "Orden",
        ["Más recientes", "Más sobresalientes", "Requieren revisión", "Nombre"],
        horizontal=True,
        label_visibility="collapsed",
    )
    q = search_val.lower().strip() if search_val else ""

    filtered = []
    for item in reports:
        rid = item["rid"]
        report = item["report"]
        stats = item["stats"]
        name = report.pdf_name or ""
        if q and q not in name.lower() and q not in rid.lower():
            continue
        if view_filter == "Requieren revisión" and stats["estado_cls"] != "risk":
            continue
        if view_filter == "Sobresalientes" and stats["estado_label"] != "Sobresaliente":
            continue
        if view_filter == "Completados" and report.estado != "completado":
            continue
        if view_filter == "Errores" and report.estado != "error":
            continue
        filtered.append(item)

    if sort == "Más recientes":
        filtered.sort(key=lambda item: getattr(item["report"], "timestamp", ""), reverse=True)
    elif sort == "Más sobresalientes":
        filtered.sort(key=lambda item: (item["stats"]["aprob_pct"], item["stats"]["nivel_prom"], item["stats"]["confianza"]), reverse=True)
    elif sort == "Requieren revisión":
        filtered.sort(key=lambda item: (item["stats"]["aprob_pct"], item["stats"]["confianza"], item["stats"]["nivel_prom"]))
    else:
        filtered.sort(key=lambda item: item["report"].pdf_name.lower())

    if st.session_state.get("_action") == "preview_pdf":
        report_id_to_preview = st.session_state.get("selected_report_id")
        if report_id_to_preview:
            report_to_preview = load_report(report_id_to_preview)
            if report_to_preview:
                st.session_state.pop("_action", None)
                _show_pdf_preview_modal(report_to_preview, report_id_to_preview)

    if not filtered:
        st.info("No hay informes que coincidan con la búsqueda o filtro.")
        return

    for item in filtered:
        rid = item["rid"]
        report = item["report"]
        stats = item["stats"]
        
        st.markdown(_report_card_html(report, rid, stats, cohort_id), unsafe_allow_html=True)

    # Interceptar acción de preview PDF
    if st.session_state.get("_action") == "preview_pdf":
        report_id_to_preview = st.session_state.get("selected_report_id")
        if report_id_to_preview:
            report_to_preview = load_report(report_id_to_preview)
            if report_to_preview:
                st.session_state.pop("_action", None)
                _show_pdf_preview_modal(report_to_preview, report_id_to_preview)

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
