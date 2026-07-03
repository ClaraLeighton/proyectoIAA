import streamlit as st
from html import escape
from textwrap import dedent

from pipeline.cohorts import list_cohorts, compute_cohort_macro
from ui.components import page_hero, empty_state


LEVEL_COLORS = {"0": "#ef4444", "1": "#f97316", "2": "#2e9cdb", "3": "#22c55e"}
COHORT_PALETTE = ["#CE0019", "#2563eb", "#d97706", "#16a34a"]


def _clasificar_competencia(tasa_aprobacion: float) -> str:
    if tasa_aprobacion >= 0.70:
        return "Evidenciada"
    if tasa_aprobacion >= 0.50:
        return "Parcialmente evidenciada"
    return "Escasa evidencia"


def _nivel_logro(pct: float) -> str:
    if pct >= 70:
        return "alta"
    if pct >= 50:
        return "media"
    return "baja"


def _sort_cid(cid: str):
    digits = "".join(ch for ch in cid if ch.isdigit())
    return int(digits) if digits else cid


def _cid_label(cid: str, macros: list) -> str:
    nombre = ""
    for _, macro in macros:
        d = macro["competencias"].get(cid)
        if d and d.get("nombre"):
            nombre = d["nombre"]
            break
    if nombre:
        return f"{cid}: {nombre}"
    return cid


def _html_block(template: str) -> str:
    return "".join(line.strip() for line in dedent(template).splitlines())


def _build_summary_html(macros: list) -> str:
    cards = []
    for idx, (cohort, macro) in enumerate(macros):
        g = macro["global"]
        comps = macro["competencias"]
        color = COHORT_PALETTE[idx % len(COHORT_PALETTE)]
        evid = sum(1 for c in comps.values() if _clasificar_competencia(c.get("tasa_aprobacion", 0)) == "Evidenciada")
        parcial = sum(1 for c in comps.values() if "Parcialmente" in _clasificar_competencia(c.get("tasa_aprobacion", 0)))
        escasa = sum(1 for c in comps.values() if _clasificar_competencia(c.get("tasa_aprobacion", 0)) == "Escasa evidencia")
        nivel = g["nivel_promedio_global"]

        cards.append(f"""
        <div class="comp-cohort-card" style="--accent:{color}">
          <div class="comp-cohort-name">{escape(cohort["name"])}</div>
          <div class="comp-cohort-stats">
            <span><b>{g["total_reportes"]}</b> informes</span>
            <span><b>{evid}</b> evidenciadas</span>
            <span><b>{parcial}</b> parciales</span>
            <span><b>{escasa}</b> escasa evidencia</span>
            <span><b>{nivel:.2f}/3</b> nivel promedio</span>
          </div>
        </div>""")

    return _html_block(f"""
    <div class="comp-summary-grid">
      {"".join(cards)}
    </div>""")


def _build_bars_html(macros: list) -> str:
    all_cids = set()
    for _, macro in macros:
        all_cids.update(macro["competencias"].keys())
    if not all_cids:
        return ""

    cid_avg = {}
    for cid in all_cids:
        vals = []
        for _, macro in macros:
            d = macro["competencias"].get(cid)
            if d:
                vals.append(d.get("score_pct", 0) * 100)
        cid_avg[cid] = sum(vals) / len(vals) if vals else 0

    sorted_cids = sorted(all_cids, key=lambda c: cid_avg[c], reverse=True)

    legend = "".join(
        f'<span><i style="background:{COHORT_PALETTE[i]}"></i>{escape(cohort["name"])}</span>'
        for i, (cohort, _) in enumerate(macros)
    )

    rows_html = []
    for cid in sorted_cids:
        bars = []
        label = escape(_cid_label(cid, macros))
        for gi, (_, macro) in enumerate(macros):
            data = macro["competencias"].get(cid)
            pct = data.get("score_pct", 0) * 100 if data else 0
            color = COHORT_PALETTE[gi % len(COHORT_PALETTE)]
            bars.append(
                f'<div class="comp-bar-track">'
                f'  <div class="comp-bar-fill" style="width:{pct}%;background:{color}">'
                f'    <span class="comp-bar-pct">{pct:.0f}%</span>'
                f'  </div>'
                f'</div>'
            )
        rows_html.append(
            f'<div class="comp-hbar-row">'
            f'  <div class="comp-hbar-cid">{label}</div>'
            f'  <div class="comp-hbar-bars">{"".join(bars)}</div>'
            f'</div>'
        )

    return _html_block(f"""
    <div class="comp-section">
      <div class="comp-section-title">Desempeño por competencia</div>
      <p class="comp-section-desc">
        Las competencias están ordenadas de mejor a peor desempeño promedio entre las cohortes seleccionadas.
        Cada barra representa el porcentaje de logro de una cohorte. Más larga = mejor resultado.
      </p>
      <div class="comp-chart-legend">{legend}</div>
      <div class="comp-hbar-grid">{"".join(rows_html)}</div>
    </div>""")


def _build_table_html(macros: list) -> str:
    all_cids = set()
    for _, macro in macros:
        all_cids.update(macro["competencias"].keys())
    sorted_cids = sorted(all_cids, key=_sort_cid)

    if not sorted_cids:
        return ""

    rows = []
    for cid in sorted_cids:
        cells = []
        label = escape(_cid_label(cid, macros))
        for _, macro in macros:
            data = macro["competencias"].get(cid)
            if data:
                tasa = data.get("tasa_aprobacion", 0)
                score_pct = data.get("score_pct", 0) * 100
                clasif = _clasificar_competencia(tasa)
                nivel = _nivel_logro(score_pct)
                cells.append(
                    f'<td class="comp-dtl-cell {nivel}">'
                    f'  <div class="comp-dtl-inner">'
                    f'    <span class="comp-dtl-pct">{score_pct:.0f}%</span>'
                    f'    <span class="comp-dtl-cls">{clasif.split()[0]}</span>'
                    f'  </div>'
                    f'</td>'
                )
            else:
                cells.append('<td class="comp-dtl-cell comp-dtl-na">—</td>')
        rows.append(
            f'<tr>'
            f'  <td class="comp-dtl-cid"><strong>{label}</strong></td>'
            f'  {"".join(cells)}'
            f'</tr>'
        )

    col_headers = "".join(f'<th>{escape(cohort["name"])}</th>' for cohort, _ in macros)

    return _html_block(f"""
    <div class="comp-section">
      <div class="comp-section-title">Resultados detallados por competencia</div>
      <p class="comp-section-desc">
        Cada celda muestra el porcentaje de logro y la clasificación resumida.
        <span class="comp-legend-pill comp-pill-alta">● Alto (≥70%)</span>
        <span class="comp-legend-pill comp-pill-media">● Medio (50-69%)</span>
        <span class="comp-legend-pill comp-pill-baja">● Bajo (&lt;50%)</span>
        <span class="comp-legend-pill comp-pill-na">● Sin datos</span>
      </p>
      <div class="comp-table-wrap">
        <table class="comp-table comp-detail-table">
          <thead><tr><th>Competencia</th>{col_headers}</tr></thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
      </div>
    </div>""")


def _build_evolution_html(macros: list) -> str:
    all_cids = set()
    for _, macro in macros:
        all_cids.update(macro["competencias"].keys())
    sorted_cids = sorted(all_cids, key=_sort_cid)

    if len(macros) < 2 or not sorted_cids:
        return ""

    cohort_names = [escape(cohort["name"]) for cohort, _ in macros]

    rows = []
    for cid in sorted_cids:
        prev_pct = None
        cells = []
        label = escape(_cid_label(cid, macros))
        for gi, (_, macro) in enumerate(macros):
            data = macro["competencias"].get(cid)
            pct = round(data.get("score_pct", 0) * 100) if data else None
            arrow = ""
            if prev_pct is not None and pct is not None:
                diff = pct - prev_pct
                if diff > 3:
                    arrow = f' <span class="comp-arrow up">▲ +{diff}</span>'
                elif diff < -3:
                    arrow = f' <span class="comp-arrow down">▼ {diff}</span>'
                else:
                    arrow = f' <span class="comp-arrow flat">→ {diff:+d}</span>'
            cells.append(f"<td>{pct if pct is not None else '—'}%{arrow}</td>")
            prev_pct = pct
        joined = "".join(cells)
        rows.append(f"<tr><td class=\"comp-dtl-cid\"><strong>{label}</strong></td>{joined}</tr>")

    col_h = "".join(f"<th>{n}</th>" for n in cohort_names)

    return _html_block(f"""
    <div class="comp-section">
      <div class="comp-section-title">Evolución entre cohortes (orden cronológico)</div>
      <p class="comp-section-desc">
        Variación del porcentaje de logro entre cohortes consecutivas.
        <span class="comp-legend-pill comp-pill-alta">▲ Mejora (≥4 pts)</span>
        <span class="comp-legend-pill comp-pill-baja">▼ Baja (≥4 pts)</span>
        <span class="comp-legend-pill" style="background:#f3f4f6;color:#6b7280">→ Sin cambio</span>
        Útil para identificar si los resultados mejoran, empeoran o se mantienen estables a lo largo del tiempo.
      </p>
      <div class="comp-table-wrap">
        <table class="comp-table comp-evol-table">
          <thead><tr><th>Competencia</th>{col_h}</tr></thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
      </div>
    </div>""")


def _build_comparison_html(macros: list) -> str:
    return _html_block(f"""
    <div class="comp-dashboard">
      {_build_summary_html(macros)}
      {_build_bars_html(macros)}
      {_build_table_html(macros)}
      {_build_evolution_html(macros)}
    </div>""")


def render_comparison():
    cohorts = list_cohorts()

    page_hero(
        "Comparación de Cohortes",
        subtitle="Selecciona entre 2 y 4 cohortes para comparar sus resultados macro.",
    )

    if not cohorts:
        empty_state("Sin cohortes", "Aún no hay cohortes creadas. Crea una para comenzar.")
        return

    selected_names = st.multiselect(
        "Cohortes a comparar",
        options=[c["name"] for c in cohorts],
        max_selections=4,
        placeholder="Elige 2 a 4 cohortes…",
    )

    if len(selected_names) < 2:
        st.info("Selecciona al menos 2 cohortes para ver la comparación.", icon="ℹ️")
        return

    selected = [c for c in cohorts if c["name"] in selected_names]

    macros = []
    for c in selected:
        macro = compute_cohort_macro(c["cohort_id"])
        if macro["global"]["total_reportes"] == 0:
            st.warning(f"La cohorte **{c['name']}** no tiene informes procesados.", icon="⚠️")
            return
        macros.append((c, macro))

    st.markdown(_build_comparison_html(macros), unsafe_allow_html=True)
