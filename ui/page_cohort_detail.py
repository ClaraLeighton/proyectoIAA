import streamlit as st
from html import escape
from textwrap import dedent

from pipeline.cohorts import get_cohort, compute_cohort_macro
from pipeline.reportes_export import build_export_index, exportar_excel_multi_hoja
from ui.components import page_hero, empty_state, badge


LEVEL_COLORS = {"0": "#ef4444", "1": "#f97316", "2": "#2e9cdb", "3": "#22c55e"}
LEVEL_LABELS = {"0": "Sin evidencia", "1": "No aplica", "2": "Uso concreto", "3": "Dominio técnico"}
LEVEL_SHORT = {"0": "SE", "1": "NA", "2": "UC", "3": "DT"}


def _formatear_tipo(tipo: str) -> str:
    nombre = tipo.replace("_", " ").title()
    nombre = nombre.replace("Pre ", "Pre-")
    nombre = nombre.replace("Practica", "Práctica")
    return nombre


def _sort_competencia_id(cid: str):
    digits = "".join(ch for ch in cid if ch.isdigit())
    return int(digits) if digits else cid


def _clamp_pct(value: float) -> float:
    return max(0, min(100, value))


def _estado_competencia(tasa_aprobacion: float) -> tuple[str, str, str]:
    if tasa_aprobacion >= 0.70:
        return "Consolidada", "ok", ">= 70% de evaluaciones en nivel 2 o 3"
    if tasa_aprobacion >= 0.50:
        return "En desarrollo", "mid", "50% a 69% de evaluaciones en nivel 2 o 3"
    return "Brecha prioritaria", "risk", "< 50% de evaluaciones en nivel 2 o 3"


def _build_stacked_bar(dist: dict, total: int) -> str:
    if total <= 0:
        return '<div class="macro-stack empty"></div>'
    segments = []
    for lvl in ["0", "1", "2", "3"]:
        count = dist.get(lvl, 0)
        pct = count / total * 100
        if count:
            segments.append(
                f'<span title="{LEVEL_LABELS[lvl]}: {count}" '
                f'style="width:{pct:.1f}%;background:{LEVEL_COLORS[lvl]}">{count}</span>'
            )
    return f'<div class="macro-stack">{"".join(segments)}</div>'


def _legend_html(nivel_dist: dict, total: int) -> str:
    items = []
    for lvl in ["0", "1", "2", "3"]:
        count = nivel_dist.get(lvl, 0)
        pct = count / total * 100 if total else 0
        items.append(
            f'<span><i style="background:{LEVEL_COLORS[lvl]}"></i>'
            f'{LEVEL_LABELS[lvl]} <strong>{count}</strong> ({pct:.0f}%)</span>'
        )
    return f'<div class="macro-legend">{"".join(items)}</div>'


def _build_line_chart(comp_list: list[tuple[str, dict]]) -> str:
    if not comp_list:
        return '<div class="macro-line-empty">Sin datos para graficar.</div>'

    width = 680
    height = 260
    pad_x = 42
    pad_top = 28
    pad_bottom = 46
    plot_w = width - pad_x * 2
    plot_h = height - pad_top - pad_bottom
    denom = max(1, len(comp_list) - 1)

    def points_for(metric: str) -> list[tuple[float, float, str, float]]:
        pts = []
        for idx, (cid, data) in enumerate(comp_list):
            value = data.get(metric, 0) * 100
            x = pad_x + (idx / denom) * plot_w
            y = pad_top + (1 - value / 100) * plot_h
            pts.append((x, y, cid, value))
        return pts

    score_pts = points_for("score_pct")
    aprob_pts = points_for("tasa_aprobacion")
    score_attr = " ".join(f"{x:.1f},{y:.1f}" for x, y, _, _ in score_pts)
    aprob_attr = " ".join(f"{x:.1f},{y:.1f}" for x, y, _, _ in aprob_pts)
    area_attr = f"{pad_x},{height - pad_bottom} {score_attr} {width - pad_x},{height - pad_bottom}"

    score_dots = []
    aprob_dots = []
    labels = []
    for x, y, cid, value in score_pts:
        score_dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5"><title>{escape(cid)} score: {value:.0f}%</title></circle>')
        labels.append(f'<text x="{x:.1f}" y="{height - 19}" text-anchor="middle">{escape(cid)}</text>')
    for x, y, cid, value in aprob_pts:
        aprob_dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.8"><title>{escape(cid)} aprobación: {value:.0f}%</title></circle>')

    grid = []
    for pct in [0, 25, 50, 75, 100]:
        y = pad_top + (1 - pct / 100) * plot_h
        grid.append(
            f'<line x1="{pad_x}" y1="{y:.1f}" x2="{width - pad_x}" y2="{y:.1f}"></line>'
            f'<text x="10" y="{y + 4:.1f}">{pct}%</text>'
        )

    return (
        '<div class="macro-line-chart">'
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Evolución por competencia">'
        '<defs><linearGradient id="macroScoreFill" x1="0" x2="0" y1="0" y2="1">'
        '<stop offset="0%" stop-color="#CE0019" stop-opacity="0.24"></stop>'
        '<stop offset="100%" stop-color="#CE0019" stop-opacity="0.02"></stop>'
        '</linearGradient></defs>'
        f'<g class="macro-chart-grid-lines">{"".join(grid)}</g>'
        f'<polygon class="macro-area" points="{area_attr}"></polygon>'
        f'<polyline class="macro-score-line" points="{score_attr}"></polyline>'
        f'<polyline class="macro-aprob-line" points="{aprob_attr}"></polyline>'
        f'<g class="macro-score-dots">{"".join(score_dots)}</g>'
        f'<g class="macro-aprob-dots">{"".join(aprob_dots)}</g>'
        f'<g class="macro-chart-labels">{"".join(labels)}</g>'
        '</svg>'
        '</div>'
    )


def _build_bar_chart(comp_list: list[tuple[str, dict]]) -> str:
    if not comp_list:
        return '<div class="macro-line-empty">Sin datos para graficar.</div>'

    ordered = sorted(comp_list, key=lambda item: _sort_competencia_id(item[0]))
    max_items = ordered
    max_value = max((data.get("tasa_aprobacion", 0) for _, data in max_items), default=1)
    max_value = max(max_value, 0.01)
    bars = []
    for cid, data in max_items:
        aprob = data.get("tasa_aprobacion", 0) * 100
        estado, estado_cls, _ = _estado_competencia(data.get("tasa_aprobacion", 0))
        height = 22 + (data.get("tasa_aprobacion", 0) / max_value) * 92
        bars.append(
            f'<div class="macro-mini-bar {estado_cls}" title="{escape(cid)} · {estado} · {aprob:.0f}% aprobación">'
            f'<i style="height:{height:.1f}px"></i><strong>{aprob:.0f}%</strong><span>{escape(cid)}</span></div>'
        )
    return f'<div class="macro-mini-bars">{"".join(bars)}</div>'


def _html_block(template: str) -> str:
    return "".join(line.strip() for line in dedent(template).splitlines())


def _macro_dashboard_html(cohort, tipo_label, g, nivel_dist, total_comps, competencias):
    score_pct = _clamp_pct(g["score_pct"] * 100)
    aprob_pct = _clamp_pct(g["tasa_aprobacion_global"] * 100)
    nivel_pct = _clamp_pct((g["nivel_promedio_global"] / 3) * 100 if g["nivel_promedio_global"] else 0)
    comp_list = sorted(competencias.items(), key=lambda item: _sort_competencia_id(item[0]))
    cumplidas = sum(1 for _, c in comp_list if c.get("tasa_aprobacion", 0) >= 0.70)
    desarrollo = sum(1 for _, c in comp_list if 0.50 <= c.get("tasa_aprobacion", 0) < 0.70)
    brecha = sum(1 for _, c in comp_list if c.get("tasa_aprobacion", 0) < 0.50)
    perfil_pct = cumplidas / len(comp_list) * 100 if comp_list else 0

    sorted_by_score = sorted(comp_list, key=lambda item: item[1].get("score_pct", 0), reverse=True)
    line_chart = _build_line_chart(comp_list)
    bar_chart = _build_bar_chart(comp_list)
    top_rows = []
    for cid, data in sorted_by_score[:4]:
        pct = data.get("score_pct", 0) * 100
        top_rows.append(
            f'<div class="macro-rank-row">'
            f'<strong>{escape(cid)}</strong>'
            f'<span>{escape(data.get("nombre", "")[:52])}</span>'
            f'<em>{pct:.0f}%</em>'
            f'</div>'
        )

    weak_rows = []
    sorted_by_approval = sorted(comp_list, key=lambda item: item[1].get("tasa_aprobacion", 0))
    for cid, data in sorted_by_approval[:3]:
        pct = data.get("tasa_aprobacion", 0) * 100
        weak_rows.append(
            f'<div class="macro-gap-row">'
            f'<div><strong>{escape(cid)}</strong><span>{escape(data.get("nombre", "")[:48])}</span></div>'
            f'<em>{pct:.0f}% aprueba</em>'
            f'</div>'
        )

    tiles = []
    for cid, data in comp_list:
        aprob = data.get("tasa_aprobacion", 0) * 100
        score = data.get("score_pct", 0) * 100
        estado, estado_cls, _ = _estado_competencia(data.get("tasa_aprobacion", 0))
        tiles.append(
            f'<div class="macro-comp-tile {estado_cls}">'
            f'<div class="macro-comp-top"><strong>{escape(cid)}</strong><span>{estado}</span></div>'
            f'<p>{escape(data.get("nombre", ""))}</p>'
            f'<div class="macro-comp-meter"><i style="width:{_clamp_pct(aprob):.1f}%"></i></div>'
            f'<div class="macro-comp-foot"><span>{aprob:.0f}% aprobación</span><b>{score:.0f}% score</b></div>'
            f'</div>'
        )

    matrix_rows = []
    for cid, data in comp_list:
        dist = data.get("distribucion", {})
        total = data.get("total_reportes", 0)
        aprob = data.get("tasa_aprobacion", 0) * 100
        score = data.get("score_pct", 0) * 100
        estado, estado_cls, estado_hint = _estado_competencia(data.get("tasa_aprobacion", 0))
        cells = []
        for lvl in ["0", "1", "2", "3"]:
            count = dist.get(lvl, 0)
            intensity = count / total if total else 0
            cells.append(
                f'<td><span class="macro-heat-cell" '
                f'style="--heat:{0.16 + intensity * 0.78:.2f};background:{LEVEL_COLORS[lvl]}">'
                f'{count}</span></td>'
            )
        matrix_rows.append(
            f'<tr>'
            f'<td><strong>{escape(cid)}</strong><small>{escape(data.get("nombre", ""))}</small></td>'
            f'<td>{data.get("nivel_promedio", 0):.2f}/3</td>'
            f'<td><div class="macro-table-meter"><i style="width:{_clamp_pct(aprob):.1f}%"></i></div><b>{aprob:.0f}%</b></td>'
            f'<td>{_build_stacked_bar(dist, total)}</td>'
            f'{"".join(cells)}'
            f'<td><span class="macro-status {estado_cls}" title="{estado_hint}">{estado}</span></td>'
            f'<td>{score:.0f}%</td>'
            f'</tr>'
        )

    return _html_block(f"""
    <div class="macro-dashboard">
      <section class="macro-hero-panel">
        <div class="macro-hero-copy">
          <div class="macro-eyebrow">{escape(tipo_label)} · Cohorte · {g["total_reportes"]} informes</div>
          <h2>{escape(cohort["name"])}</h2>
          <p>Lectura del perfil de egreso a nivel cohorte: qué competencias se están cumpliendo, cuáles requieren refuerzo y con qué nivel de evidencia.</p>
          <div class="macro-hero-stats">
            <div><strong>{cumplidas}/{len(comp_list)}</strong><span>competencias consolidadas</span></div>
            <div><strong>{g["nivel_promedio_global"]:.2f}/3</strong><span>nivel promedio</span></div>
            <div><strong>{total_comps}</strong><span>evaluaciones acumuladas</span></div>
          </div>
        </div>
        <div class="macro-donut-card">
          <div class="macro-donut" style="--score:{score_pct:.1f}">
            <div><strong>{score_pct:.0f}%</strong><span>score global</span></div>
          </div>
          <p>Score = puntos obtenidos sobre el máximo posible de la cohorte.</p>
        </div>
      </section>

      <section class="macro-dashboard-grid">
        <div class="macro-color-card red">
          <span>Aprobación global</span>
          <strong>{aprob_pct:.1f}%</strong>
          <div class="macro-mini-track"><div style="width:{aprob_pct:.1f}%"></div></div>
          <small>Nivel 2 o 3 cuenta como cumplimiento.</small>
        </div>
        <div class="macro-color-card yellow">
          <span>Perfil de egreso</span>
          <strong>{perfil_pct:.0f}%</strong>
          <div class="macro-mini-track"><div style="width:{perfil_pct:.1f}%"></div></div>
          <small>{cumplidas} consolidadas · {desarrollo} en desarrollo · {brecha} brecha</small>
        </div>
        <div class="macro-color-card blue">
          <span>Nivel promedio</span>
          <strong>{g["nivel_promedio_global"]:.2f}/3</strong>
          <div class="macro-mini-track"><div style="width:{nivel_pct:.1f}%"></div></div>
          <small>Escala 0: sin evidencia a 3: dominio técnico.</small>
        </div>
        <div class="macro-mini-card">
          <span>Lectura rápida</span>
          <strong>{brecha}</strong>
          <p>competencias bajo 50% de aprobación requieren revisión de evidencia o reforzamiento.</p>
        </div>
      </section>

      <section class="macro-analytics-grid">
        <div class="macro-panel macro-chart-card macro-bars-card">
          <div class="macro-panel-head">
            <div>
              <div class="macro-panel-title">Aprobación por competencia</div>
              <p>Competencias en orden numérico. Más alta significa que más informes cumplen esa competencia.</p>
            </div>
          </div>
          {bar_chart}
        </div>
        <div class="macro-panel macro-chart-card macro-line-panel">
          <div class="macro-panel-head">
            <div>
              <div class="macro-panel-title">Qué tan bien se cumple cada competencia</div>
              <p>Azul = cuántos informes cumplen la competencia. Rojo = qué tan alto fue el nivel logrado. Si ambas líneas están altas, la competencia está fuerte; si azul alta y roja más baja, se cumple pero con menor profundidad.</p>
            </div>
            <div class="macro-chart-legend">
              <span><i class="score"></i>Nivel logrado</span>
              <span><i class="aprob"></i>Informes que cumplen</span>
            </div>
          </div>
          {line_chart}
          <div class="macro-line-help">
            <span>Ambas altas = competencia sólida</span>
            <span>Azul alta y roja media = se cumple, pero falta dominio</span>
            <span>Ambas bajas = brecha prioritaria</span>
          </div>
        </div>
        <div class="macro-panel macro-distribution-card">
          <div class="macro-panel-title">Distribución de niveles</div>
          <div class="macro-pie-wrap">
            <div class="macro-ring" style="--n0:{nivel_dist.get("0", 0) / total_comps * 100 if total_comps else 0:.1f};--n1:{nivel_dist.get("1", 0) / total_comps * 100 if total_comps else 0:.1f};--n2:{nivel_dist.get("2", 0) / total_comps * 100 if total_comps else 0:.1f};--n3:{nivel_dist.get("3", 0) / total_comps * 100 if total_comps else 0:.1f}">
              <div><strong>{total_comps}</strong><span>evaluaciones</span></div>
            </div>
          </div>
          {_legend_html(nivel_dist, total_comps)}
        </div>
      </section>

      <section class="macro-panel macro-wide-panel">
        <div class="macro-panel-head">
          <div>
            <div class="macro-panel-title">Mapa de cumplimiento por competencia</div>
            <p>Cada tarjeta muestra aprobación acumulada por competencia. El color identifica estado, no “bueno/malo” absoluto.</p>
          </div>
          <div class="macro-status-legend">
            <span><i class="ok"></i>Consolidada: >= 70%</span>
            <span><i class="mid"></i>En desarrollo: 50-69%</span>
            <span><i class="risk"></i>Brecha: < 50%</span>
          </div>
        </div>
        <div class="macro-comp-grid">{"".join(tiles)}</div>
      </section>

      <section class="macro-bottom-grid">
        <div class="macro-panel">
          <div class="macro-panel-title">Competencias mejor logradas</div>
          <p class="macro-panel-note">Ordenadas por score acumulado sobre el máximo esperado.</p>
          {''.join(top_rows) if top_rows else '<p>Sin competencias disponibles.</p>'}
        </div>
        <div class="macro-panel macro-gap-panel">
          <div class="macro-panel-title">Focos de mejora</div>
          <p class="macro-panel-note">Menor proporción de evaluaciones en nivel 2 o 3.</p>
          {''.join(weak_rows) if weak_rows else '<p>Sin brechas disponibles.</p>'}
        </div>
      </section>

      <section class="macro-panel macro-table-panel">
        <div class="macro-panel-head">
          <div>
            <div class="macro-panel-title">Matriz cohortal de perfil de egreso</div>
            <p>Tabla interpretativa por competencia. Las columnas SE, NA, UC y DT muestran conteos por nivel; barras y colores explican cumplimiento.</p>
          </div>
          <div class="macro-level-codes">
            <span>SE: sin evidencia</span><span>NA: no aplica</span><span>UC: uso concreto</span><span>DT: dominio técnico</span>
          </div>
        </div>
        <div class="macro-table-scroll">
          <table class="macro-matrix-table">
            <thead>
              <tr>
                <th>Competencia</th>
                <th>Nivel</th>
                <th>Aprobación</th>
                <th>Distribución</th>
                <th>{LEVEL_SHORT["0"]}</th>
                <th>{LEVEL_SHORT["1"]}</th>
                <th>{LEVEL_SHORT["2"]}</th>
                <th>{LEVEL_SHORT["3"]}</th>
                <th>Estado</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>{"".join(matrix_rows)}</tbody>
          </table>
        </div>
      </section>
    </div>
    """)


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
