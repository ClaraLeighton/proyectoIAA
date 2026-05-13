_RED = "#CE0019"
_DARK = "#17212B"
_MUTED = "#8E98A3"

def _svg(view_box, path, w=20, h=20, color=_DARK):
    return f'<svg width="{w}" height="{h}" viewBox="{view_box}" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="{path}" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'

def _svg_filled(view_box, path, w=20, h=20, color=_DARK):
    return f'<svg width="{w}" height="{h}" viewBox="{view_box}" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="{path}" fill="{color}"/></svg>'

def folder(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M3 7v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-6l-2-2H5a2 2 0 0 0-2 2z", w, h, color)

def folder_plus(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M3 7v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-6l-2-2H5a2 2 0 0 0-2 2z M12 12v4 M10 14h4", w, h, color)

def upload(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M21 15v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-3 M17 9l-5-5-5 5 M12 4v12", w, h, color)

def list_icon(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M8 6h13 M8 12h13 M8 18h13 M3 6h.01 M3 12h.01 M3 18h.01", w, h, color)

def play(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M5 3l14 9-14 9V3z", w, h, color)

def check(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M20 6L9 17l-5-5", w, h, color)

def search(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z M21 21l-4.35-4.35", w, h, color)

def cut(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M23 4L9 18 M6 10l4 4 M6 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6z M18 14a3 3 0 1 0 0 6 3 3 0 0 0 0-6z", w, h, color)

def brain(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M12 3a6 6 0 0 0-6 6c0 2.5 1.5 4.5 3 5.5V21l3-2 3 2v-6.5c1.5-1 3-3 3-5.5a6 6 0 0 0-6-6z M12 7v4 M10 9h4", w, h, color)

def clip(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48", w, h, color)

def cpu(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M9 3v2 M15 3v2 M9 19v2 M15 19v2 M5 9H3 M5 15H3 M21 9h-2 M21 15h-2 M7 7h10v10H7V7z", w, h, color)

def chart(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M18 20V10 M12 20V4 M6 20v-6", w, h, color)

def xmark(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M18 6L6 18 M6 6l12 12", w, h, color)

def clock(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z M12 6v6l4 2", w, h, color)

def doc(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z M14 2v6h6 M16 13H8 M16 17H8 M10 9H8", w, h, color)

def settings(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z", w, h, color)

def trash(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M3 6h18 M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6 M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2 M10 11v6 M14 11v6", w, h, color)

def arrow_left(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M19 12H5 M12 5l-7 7 7 7", w, h, color)

def download(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M21 15v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-3 M7 10l5 5 5-5 M12 15V3", w, h, color)

def info(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z M12 16v-4 M12 8h.01", w, h, color)

def alert(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M12 2L2 19h20L12 2z M12 10v4 M12 16h.01", w, h, color)

def circle_green(w=14, h=14):
    return _svg_filled("0 0 24 24", "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z", w, h, "#16A34A")

def circle_yellow(w=14, h=14):
    return _svg_filled("0 0 24 24", "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z", w, h, "#D97706")

def circle_red(w=14, h=14):
    return _svg_filled("0 0 24 24", "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z", w, h, "#CE0019")

def spinner(w=24, h=24):
    return f'''<svg width="{w}" height="{h}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <style>
        @keyframes uandes-spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
        .uandes-spinner {{ animation: uandes-spin 1.5s linear infinite; transform-origin: center; }}
    </style>
    <circle class="uandes-spinner" cx="12" cy="12" r="10" stroke="#CE0019" stroke-width="2.5" stroke-dasharray="31.4 15.7" stroke-linecap="round" fill="none"/>
</svg>'''

def html_icon(icon_fn, text="", size=20, color=_DARK):
    svg = icon_fn(size, size, color)
    if text:
        return f'<span style="display:inline-flex;align-items:center;gap:6px">{svg}<span>{text}</span></span>'
    return svg

# New icons for the redesign
def layers(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5", w, h, color)

def bar_chart(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M4 20h16M6 16V9m4 7v-6m4 6V7m4 9v-4", w, h, color)

def users(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2 M9 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8z M23 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75", w, h, color)

def chevron_right(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M9 18l6-6-6-6", w, h, color)

def file_text(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6 M16 13H8 M16 17H8 M10 9H8", w, h, color)

def grid(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M3 3h7v7H3V3z M14 3h7v7h-7V3z M14 14h7v7h-7v-7z M3 14h7v7H3v-7z", w, h, color)

def percent(w=20, h=20, color=_DARK):
    return _svg("0 0 24 24", "M19 5L5 19 M7 7h.01 M17 17h.01", w, h, color)
