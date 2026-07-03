import streamlit as st
from html import escape
from textwrap import dedent
from pipeline.persistence import load_report
from pipeline.reportes_export import exportar_reporte_individual
from ui.components import page_hero, badge
from ui.icons import search, file_text


LEVEL_LABELS = {0: "Sin evidencia", 1: "Solo teoría", 2: "Uso concreto", 3: "Dominio técnico"}
LEVEL_VARIANTS = {0: "red", 1: "yellow", 2: "blue", 3: "green"}
LEVEL_COLORS = {0: "#ef4444", 1: "#f97316", 2: "#2e9cdb", 3: "#22c55e"}


def _nivel_badge_html(nivel: int) -> str:
    label = LEVEL_LABELS.get(nivel, f"Nivel {nivel}")
    variant = LEVEL_VARIANTS.get(nivel, "gray")
    return badge(f"Nivel {nivel}: {label}", variant)


def _html_block(template: str) -> str:
    return "".join(line.strip() for line in dedent(template).splitlines())


def _sort_competencia_id(cid: str):
    digits = "".join(ch for ch in cid if ch.isdigit())
    return int(digits) if digits else cid


def _estado_comp(nivel: int, confianza: float) -> tuple[str, str]:
    if nivel >= 2 and confianza >= 0.55:
        return "Cumple", "ok"
    if nivel >= 2:
        return "Cumple con baja confianza", "mid"
    if confianza < 0.45:
        return "Revisar evidencia", "risk"
    return "No cumple", "risk"


def _micro_detail_chart(preview: list[dict]) -> str:
    ordered = sorted(preview, key=lambda r: _sort_competencia_id(r.get("competencia_id", "")))
    max_nivel = max((int(r.get("nivel", 0)) for r in preview), default=3)
    max_nivel = max(max_nivel, 1)
    bars = []
    for r in ordered:
        cid = r.get("competencia_id", "")
        nivel = int(r.get("nivel", 0))
        confianza = r.get("confianza", 0)
        estado, cls = _estado_comp(nivel, confianza)
        height = 22 + (nivel / max_nivel) * 92
        bars.append(
            f'<div class="macro-mini-bar {cls}" title="{escape(cid)} · Nivel {nivel} · {estado}">'
            f'<i style="height:{height:.1f}px;background:{LEVEL_COLORS.get(nivel, "#8E98A3")}"></i>'
            f'<strong>N{nivel}</strong><span>{escape(cid)}</span></div>'
        )
    return f'<div class="macro-mini-bars">{"".join(bars)}</div>'


def _micro_detail_html(report, preview: list[dict], total: int, aprobadas: int, no_aprobadas: int, nivel_prom: float) -> str:
    aprob_pct = aprobadas / total * 100 if total else 0
    confianza_prom = sum(r.get("confianza", 0) for r in preview) / total if total else 0
    dist = {0: 0, 1: 0, 2: 0, 3: 0}
    for r in preview:
        dist[int(r.get("nivel", 0))] = dist.get(int(r.get("nivel", 0)), 0) + 1

    pie_vars = ";".join(f"--n{k}:{(dist.get(k, 0) / total * 100 if total else 0):.1f}" for k in [0, 1, 2, 3])
    legend = "".join(
        f'<span><i style="background:{LEVEL_COLORS[lvl]}"></i>'
        f'{LEVEL_LABELS[lvl]} <strong>{dist.get(lvl, 0)}</strong></span>'
        for lvl, label in LEVEL_LABELS.items()
    )

    return _html_block(f"""
    <div class="micro-detail-dashboard">
      <section class="micro-detail-hero">
        <div>
          <span class="uandes-badge-tipo">Informe individual</span>
          <h2>{escape(report.pdf_name)}</h2>
          <p>Lectura micro del perfil de egreso: nivel alcanzado por competencia, evidencia usada y confianza del evaluador.</p>
        </div>
        <div class="micro-detail-score">
          <strong>{aprob_pct:.0f}%</strong>
          <span>competencias aprobadas</span>
        </div>
      </section>
      <section class="micro-detail-metrics">
        <div><strong>{total}</strong><span>competencias evaluadas</span></div>
        <div><strong>{aprobadas}</strong><span>aprobadas</span></div>
        <div><strong>{no_aprobadas}</strong><span>por revisar</span></div>
        <div><strong>{nivel_prom:.2f}/3</strong><span>nivel promedio</span></div>
        <div><strong>{confianza_prom * 100:.0f}%</strong><span>confianza promedio</span></div>
      </section>
      <section class="micro-detail-analytics compact">
        <div class="macro-panel macro-bars-card">
          <div class="macro-panel-head">
            <div><h3>Resumen por competencia</h3><p>Cada barra es una competencia. Más alta significa mayor nivel logrado.</p></div>
          </div>
          {_micro_detail_chart(preview)}
        </div>
        <div class="macro-panel macro-distribution-card">
          <h3>Distribución por niveles</h3>
          <div class="macro-ring" style="{pie_vars}">
            <div><strong>{total}</strong><span>competencias</span></div>
          </div>
          <div class="macro-legend">{legend}</div>
        </div>
      </section>
      <section class="micro-comp-section">
        <div class="micro-panel-head">
          <div><h3>Competencias del informe</h3><p>Resumen en cuadrícula. Abre una competencia para ver justificación, secciones y citas.</p></div>
        </div>
      </section>
    </div>
    """)


def _competency_summary_html(r: dict) -> str:
    cid = r.get("competencia_id", "")
    nivel = int(r.get("nivel", 0))
    nombre = r.get("competencia_nombre", "")
    confianza = r.get("confianza", 0)
    justificacion = r.get("justificacion", "Sin justificación")
    secciones = r.get("secciones_fuente", [])
    citas = r.get("citas", [])
    es_error = "Error al procesar" in justificacion or "Error al procesar" in justificacion
    estado, cls = _estado_comp(nivel, confianza)
    if es_error:
        cls = "risk"
        estado = "Error"
    
    badge_variant = "green" if cls == "ok" else ("yellow" if cls == "mid" else "red")
    citas_html = "".join(f"<li>{escape(cita)}</li>" for cita in citas[:5]) if citas else "<li>Sin citas detectadas.</li>"
    label = f"Nivel {nivel}" if not es_error else "Error"
    pct = min(100, max(0, nivel / 3 * 100)) if not es_error else 0
    confianza_text = f"{confianza * 100:.0f}% confianza" if not es_error else ""
    
    return _html_block(f"""
    <div class="micro-comp-tile-detail {cls}">
      <div class="micro-comp-tile-top">
        <strong class="comp-id">{escape(cid)}</strong>
        <span class="comp-status-badge">{badge(escape(estado), badge_variant)}</span>
      </div>
      <h5>{escape(nombre)}</h5>
      <div class="micro-comp-tile-meter"><i style="width:{pct:.1f}%"></i></div>
      <div class="micro-comp-tile-foot">
        <span>{label}</span>
        <span>{confianza_text}</span>
      </div>
      <details class="micro-comp-inline-detail">
        <summary>Ver detalle</summary>
        <div>
          <p><b>Nivel:</b> {escape(LEVEL_LABELS.get(nivel, "")) if not es_error else "Error"}</p>
          <p><b>Justificación:</b> {escape(justificacion)}</p>
          <p><b>Secciones fuente:</b> {escape(", ".join(secciones) if secciones else "Sin secciones")}</p>
          <p><b>Citas:</b></p>
          <ol>{citas_html}</ol>
        </div>
      </details>
    </div>
    """)


def _re_evaluar_competencia(report, competencia_id: str) -> bool:
    from pipeline import c6_evaluador
    from pipeline.c7_agregador import run as c7_run
    from pipeline.persistence import save_report

    pipeline = report.pipeline_state
    c1 = pipeline.get("c1", {})
    competencias = c1.get("competencias_activas", [])
    config_activa = c1.get("config_activa", {})

    comp = next((c for c in competencias if c["competencia_id"] == competencia_id), None)
    if not comp:
        st.error(f"No se encontró la competencia {competencia_id} en la configuración.")
        return False

    resultados = pipeline.get("resultados_competencias", [])
    resultado = next((r for r in resultados if r["competencia_id"] == competencia_id), None)
    if not resultado:
        st.error(f"No se encontraron resultados para {competencia_id}.")
        return False

    evidencia = resultado.get("evidencia_recuperada", [])
    c6_api_key = pipeline.get("c6_api_key") or st.session_state.get("openrouter_key_input") or ""
    c6_provider = pipeline.get("c6_provider", "openrouter")

    nuevo_resultado = c6_evaluador.run(
        competencia=comp,
        evidencia_recuperada=evidencia,
        api_key=c6_api_key,
        model=None,
        provider=c6_provider,
        config_activa=config_activa,
    )

    nuevo_resultado["evidencia_recuperada"] = evidencia
    nuevo_resultado["r_similitud"] = resultado.get("r_similitud", 0.0)

    for i, r in enumerate(resultados):
        if r["competencia_id"] == competencia_id:
            resultados[i] = nuevo_resultado
            break

    levels, _ = c6_evaluador._extract_levels(config_activa)
    c7 = pipeline.get("c7", {})
    nuevo_c7 = c7_run(
        resultados_competencias=resultados,
        mapa_relevancia=pipeline.get("c2", {}).get("mapa_relevancia", {}),
        reportes_acumulados=[r.get("reporte", {}) for r in resultados],
        niveles_labels=levels,
    )
    pipeline["c7"] = nuevo_c7
    pipeline["resultados_competencias"] = resultados
    report.pipeline_state = pipeline
    save_report(report)
    return True


def render():
    report_id = st.session_state.get("selected_report_id")
    report = load_report(report_id) if report_id else None

    if not report:
        st.warning("No se encontró el informe seleccionado.")
        return

    preview = report.vista_preliminar
    pipeline_results = report.pipeline_state.get("resultados_competencias", [])
    resultados_map = {r["competencia_id"]: r for r in pipeline_results} if pipeline_results else {}
    tipo = report.tipo_documento.replace("_", " ").title()
    timestamp = report.timestamp[:19] if hasattr(report, "timestamp") and report.timestamp else ""

    meta_items = [badge(tipo, "outline"), timestamp]

    page_hero(
        report.pdf_name,
        subtitle="Evaluación detallada por competencia del informe.",
        meta_items=meta_items,
        back_target="cohort_reports",
    )

    if not preview:
        st.subheader("Resultados")
        st.info("Este informe no tiene resultados de competencias.")
        return

    total = len(preview)
    aprobadas = sum(1 for r in preview if r["nivel"] >= 2)
    no_aprobadas = total - aprobadas
    nivel_prom = sum(r["nivel"] for r in preview) / total if total else 0

    st.markdown(
        _micro_detail_html(report, preview, total, aprobadas, no_aprobadas, nivel_prom),
        unsafe_allow_html=True,
    )

    has_errors = any(
        resultados_map.get(r["competencia_id"], {}).get("reporte", {}).get("estado_capa_6") == "ERROR"
        for r in preview
    )
    if has_errors:
        st.warning("Algunas competencias tienen errores de evaluación. Usa los botones 'Re-evaluar' para reintentar.", icon="⚠️")

    ordered_preview = sorted(preview, key=lambda item: _sort_competencia_id(item.get("competencia_id", "")))
    for i in range(0, len(ordered_preview), 4):
        row = ordered_preview[i:i + 4]
        cols = st.columns(4)
        for j, r in enumerate(row):
            with cols[j]:
                cid = r.get("competencia_id", "")
                st.markdown(_competency_summary_html(r), unsafe_allow_html=True)
                resultado = resultados_map.get(cid, {})
                if resultado.get("reporte", {}).get("estado_capa_6") == "ERROR":
                    reintentos = resultado.get("reporte", {}).get("reintentos", 0)
                    label = "Re-evaluar"
                    if reintentos:
                        label += f" ({reintentos} intentos)"
                    if st.button(label, key=f"retry_{cid}", use_container_width=True):
                        with st.spinner(f"Re-evaluando {cid}..."):
                            ok = _re_evaluar_competencia(report, cid)
                            if ok:
                                st.success(f"{cid} re-evaluada correctamente.")
                                st.rerun()
                            else:
                                st.error(f"No se pudo re-evaluar {cid}.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Ver informe", use_container_width=True):
            from ui.page_cohort_reports import _show_pdf_preview_modal
            _show_pdf_preview_modal(report, report_id)
    with col2:
        buf = exportar_reporte_individual(report_id)
        if buf.getvalue():
            st.download_button(
                "Descargar .xlsx",
                data=buf,
                file_name=f"{report.pdf_name.replace('.pdf', '')}_evaluacion.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    with col3:
        if st.button("Volver a informes", use_container_width=True):
            st.session_state.pop("selected_report_id", None)
            st.session_state["page"] = "cohort_reports"
            st.rerun()
    with col4:
        if st.button("Volver a cohorte", use_container_width=True):
            st.session_state.pop("selected_report_id", None)
            st.session_state["page"] = "cohort_config"
            st.rerun()
