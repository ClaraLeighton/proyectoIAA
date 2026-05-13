import streamlit as st


def topbar_html():
    return """
    <div class="uandes-topbar">
        <div class="uandes-topbar-left">
            <button class="uandes-topbar-hamburger" onclick="var s=document.querySelector('section[data-testid=\'stSidebar\']');if(s){var c=s.style.width;s.style.width=c==='0px'||c===''?'230px':'0px';s.style.minWidth=s.style.width;s.style.overflow=c==='0px'||c===''?'visible':'hidden'}" title="Toggle sidebar">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round">
                    <line x1="4" y1="6" x2="20" y2="6"/>
                    <line x1="4" y1="12" x2="20" y2="12"/>
                    <line x1="4" y1="18" x2="20" y2="18"/>
                </svg>
            </button>
            <div class="uandes-topbar-logo">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
            </div>
            <span class="uandes-topbar-title">Evaluador de Perfil de Egreso</span>
        </div>
        <div class="uandes-topbar-right">Universidad de los Andes</div>
    </div>
    """


def sidebar_group(label):
    return f'<p class="sidebar-group-label">{label}</p>'


def page_hero(title, subtitle=None, meta_items=None, breadcrumb=None, back_target=None):
    html = '<div class="uandes-page-hero">'
    if breadcrumb:
        html += f'<div class="uande-hero-breadcrumb">{breadcrumb}</div>'
    html += '<div class="uandes-page-hero-row">'
    html += '<div class="uandes-page-hero-content">'
    html += f'<h1 class="uandes-hero-title">{title}</h1>'
    if subtitle:
        html += f'<p class="uandes-page-hero-subtitle">{subtitle}</p>'
    if meta_items:
        html += '<div class="uandes-page-hero-meta">'
        parts = []
        for item in meta_items:
            parts.append(f'<span class="uandes-page-hero-meta-item">{item}</span>')
        html += f'<span class="uandes-page-hero-meta-divider"></span>'.join(parts)
        html += '</div>'
    html += '</div>'
    html += '</div></div>'

    if back_target:
        cols = st.columns([5, 1])
        with cols[0]:
            st.markdown(html, unsafe_allow_html=True)
        with cols[1]:
            st.markdown('<div style="margin-top:6px">', unsafe_allow_html=True)
            if st.button("← Volver", key="back_btn", use_container_width=True):
                st.session_state["page"] = back_target
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown(html, unsafe_allow_html=True)


def section_card(title, actions=None):
    html = '<div class="uandes-section-card">'
    if title or actions:
        html += '<div class="uandes-section-card-header">'
        if title:
            html += f'<div class="uandes-section-card-title">{title}</div>'
        if actions:
            html += f'<div class="uandes-section-card-actions">{actions}</div>'
        html += '</div>'
    html += '<div class="uandes-section-card-body">'
    st.markdown(html, unsafe_allow_html=True)


def section_card_end():
    st.markdown('</div></div>', unsafe_allow_html=True)


def metric_grid(items):
    html = '<div class="uandes-metrics-grid">'
    for item in items:
        label = item[0]
        value = item[1]
        accent = item[2] if len(item) > 2 else False
        sub = item[3] if len(item) > 3 else None
        extra_cls = " accent" if accent else ""
        html += f'<div class="uandes-metric-card{extra_cls}">'
        html += f'<div class="uandes-metric-label">{label}</div>'
        html += f'<div class="uandes-metric-value">{value}</div>'
        if sub:
            html += f'<div class="uandes-metric-sub">{sub}</div>'
        html += "</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def badge(text, variant="gray"):
    return f'<span class="uandes-badge uandes-badge-{variant}">{text}</span>'


def action_tiles(tiles):
    html = '<div class="uandes-action-tiles">'
    for tile in tiles:
        icon_html = tile.get("icon", "")
        title = tile.get("title", "")
        desc = tile.get("desc", "")
        danger = tile.get("danger", False)
        icon_cls = "uandes-action-tile-icon" + (" danger" if danger else "")
        html += '<div class="uandes-action-tile">'
        html += f'<div class="{icon_cls}">{icon_html}</div>'
        html += f'<div class="uandes-action-tile-title">{title}</div>'
        html += f'<div class="uandes-action-tile-desc">{desc}</div>'
        html += '</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def report_card(name, report_id_short, nivel_html, comps_badge, status_badge, button_html):
    html = '<div class="uandes-report-card">'
    html += '<div class="uandes-report-left">'
    html += f'<div class="uandes-report-name">{name}</div>'
    html += f'<div class="uandes-report-id">ID: {report_id_short}</div>'
    html += '</div>'
    html += '<div class="uandes-report-right">'
    html += f'<span style="display:flex;align-items:center;gap:4px;font-size:14px;font-weight:600">{nivel_html}</span>'
    html += comps_badge
    html += status_badge
    html += button_html
    html += '</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def empty_state(title, message, icon_svg=None):
    icon_part = f'<div class="uandes-empty-icon">{icon_svg}</div>' if icon_svg else ""
    st.markdown(
        f'<div class="uandes-empty">{icon_part}<h3>{title}</h3><p>{message}</p></div>',
        unsafe_allow_html=True,
    )


def level_bar(dist, total, colors=None):
    if total == 0:
        return "<i>sin datos</i>"
    if colors is None:
        colors = {"0": "#ef4444", "1": "#f97316", "2": "#2e9cdb", "3": "#22c55e"}
    segments = []
    for lvl in ["0", "1", "2", "3"]:
        count = dist.get(lvl, 0)
        pct = count / total * 100
        if count > 0:
            segments.append(
                f'<div class="uandes-level-segment" style="width:{pct:.1f}%;background:{colors[lvl]}">'
                f"{count}</div>"
            )
    return f'<div class="uandes-level-bar">{"".join(segments)}</div>'


def level_legend(labels, colors, dist, total):
    items = []
    for lvl in ["0", "1", "2", "3"]:
        count = dist.get(lvl, 0)
        pct = count / total * 100 if total else 0
        items.append(
            f'<span class="uandes-level-legend-item">'
            f'<span class="uandes-level-dot" style="background:{colors[lvl]}"></span>'
            f"{labels[lvl]} {count} ({pct:.0f}%)</span>"
        )
    return f'<div class="uandes-level-legend">{"".join(items)}</div>'


def level_bar_panel(title, dist, total, colors, labels):
    html = '<div class="uandes-level-bar-wrap">'
    html += f'<div class="uandes-level-bar-title">{title}</div>'
    if total > 0:
        html += level_bar(dist, total, colors)
        html += level_legend(labels, colors, dist, total)
    else:
        html += '<p style="color:var(--uandes-text-muted);font-size:14px">Sin datos disponibles</p>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def form_section(title, content_func):
    st.markdown(f'<div class="uandes-form-section"><div class="uandes-form-section-title">{title}</div></div>', unsafe_allow_html=True)
    content_func()


def processing_panel(title, count_text, progress_pct, metrics_html, detail_html):
    html = '<div class="uandes-processing-panel">'
    html += f'<div class="uandes-processing-title">{title}</div>'
    html += f'<div class="uandes-processing-count">{count_text}</div>'
    if progress_pct is not None:
        html += '<div class="uandes-processing-progress">'
        html += f'<div class="stProgress"><div style="background:rgba(206,0,25,0.08);border-radius:6px;height:8px"><div style="width:{progress_pct*100:.1f}%;background:#CE0019;border-radius:6px;height:8px"></div></div></div>'
        html += '</div>'
    if metrics_html:
        html += f'<div class="uandes-processing-metrics">{metrics_html}</div>'
    html += '</div>'
    if detail_html:
        html += detail_html
    st.markdown(html, unsafe_allow_html=True)
