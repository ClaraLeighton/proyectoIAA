import re
import time
from typing import Any

SECTION_PATTERN = re.compile(
    r"^(?:(?P<number>\d+(?:\.\d+)*)\s+)?(?P<title>[A-Z][A-Za-z0-9/&,\-: ]{2,80})$"
)


def is_section_heading(line: str) -> bool:
    line = line.strip()
    match = SECTION_PATTERN.match(line)
    if not match:
        return False
    if line.lower().startswith(("image", "imagen", "table", "diagram", "figure")):
        return False
    if len(line.split()) > 8:
        return False
    return True


def _key_to_titles(key: str) -> list[str]:
    parts = key.split("_")
    candidates = []
    candidates.append(" ".join(p.capitalize() for p in parts))
    candidates.append(" ".join(parts))
    if len(parts) >= 3:
        candidates.append("/".join(p.capitalize() for p in parts))
        for i in range(1, len(parts)):
            left = "/".join(p.capitalize() for p in parts[:i])
            right = " ".join(p.capitalize() for p in parts[i:])
            candidates.append(f"{left} {right}")
        for skip_idx in range(len(parts)):
            subset = [p for i, p in enumerate(parts) if i != skip_idx]
            if len(subset) >= 2:
                candidates.append(" ".join(p.capitalize() for p in subset))
    if "challenge" in parts:
        alt = [("challenging" if p == "challenge" else p) for p in parts]
        candidates.append(" ".join(p.capitalize() for p in alt))
    seen = set()
    return [c for c in candidates if not (c in seen or seen.add(c))]


def _detect_headings(text: str) -> list[tuple[int, str, str]]:
    headings = []
    lines = text.split("\n")
    cum_pos = 0
    for line in lines:
        stripped = line.strip()
        if is_section_heading(stripped):
            match = SECTION_PATTERN.match(stripped)
            number = match.group("number") or ""
            title = match.group("title").strip()
            actual_pos = cum_pos + (len(line) - len(line.lstrip()))
            headings.append((actual_pos, number, title))
        cum_pos += len(line) + 1
    return headings


def _build_title_to_key_map(expected_keys: list[str]) -> dict[str, str]:
    mapping = {}
    for key in expected_keys:
        for candidate in _key_to_titles(key):
            mapping[candidate.lower()] = key
    return mapping


def _map_headings_to_keys(
    headings: list[tuple[int, str, str]],
    title_to_key: dict[str, str],
) -> list[tuple[int, str]]:
    matched = []
    for pos, number, title in headings:
        key = title_to_key.get(title.lower().strip())
        if key is not None:
            matched.append((pos, key))
    matched.sort(key=lambda x: x[0])
    seen = set()
    deduped = []
    for pos, key in matched:
        if key not in seen:
            seen.add(key)
            deduped.append((pos, key))
    return deduped


def _extract_sections(
    text: str,
    matched: list[tuple[int, str]],
) -> dict[str, str]:
    sections = {}
    for i, (pos, key) in enumerate(matched):
        end = matched[i + 1][0] if i + 1 < len(matched) else len(text)
        content = text[pos:end].strip()
        if len(content) > 20:
            sections[key] = content
    return sections


def _get_weight(entry: dict) -> float:
    for key in ("peso", "weight", "poids", "gewicht"):
        val = entry.get(key)
        if val is not None:
            return float(val)
    return 0.1


def _build_relevance_map(
    competencias: list[dict],
    detected_sections: list[str],
    config_activa: dict,
) -> dict[str, dict[str, str]]:
    weights = {}
    for sec in detected_sections:
        w = _get_section_weight(sec, config_activa)
        weights[sec] = w
    if not weights:
        return {}
    unique = sorted(set(weights.values()), reverse=True)
    max_w = unique[0]
    min_w = unique[-1]

    mapa: dict[str, dict[str, str]] = {}
    for comp in competencias:
        cid = comp["competencia_id"]
        mapa[cid] = {}
        for sec in detected_sections:
            w = weights.get(sec, 0.1)
            if w == max_w:
                mapa[cid][sec] = "principal"
            elif w == min_w:
                mapa[cid][sec] = "contextual"
            else:
                mapa[cid][sec] = "secundaria"
    return mapa


def _get_section_weight(sec_name: str, config_activa: dict) -> float:
    for section_name, section_data in config_activa.items():
        subsecciones = section_data.get("subsecciones") or section_data.get("subsections", {})
        if sec_name in subsecciones:
            return _get_weight(section_data)
        if sec_name == section_name:
            return _get_weight(section_data)
    return 0.1


def _get_expected_keys(config_activa: dict) -> list[str]:
    keys = []
    for section_name, section_data in config_activa.items():
        subsecciones = section_data.get("subsecciones") or section_data.get("subsections", {})
        if subsecciones:
            keys.extend(subsecciones.keys())
        else:
            keys.append(section_name)
    return keys


def _find_text_matches(
    text: str,
    expected_keys: list[str],
    matched_keys: set[str],
) -> list[tuple[int, str]]:
    unmatched = [k for k in expected_keys if k not in matched_keys]
    if not unmatched:
        return []
    matches = []
    for key in unmatched:
        titles = _key_to_titles(key)
        best = None
        for title in titles:
            for m in re.finditer(re.escape(title), text, re.IGNORECASE):
                if best is None or m.start() < best:
                    best = m.start()
        if best is not None:
            matches.append((best, key))
    return matches


def run(
    texto_completo: str,
    competencias_activas: list[dict],
    config_activa: dict,
    reporte_c1: dict | None = None,
) -> dict[str, Any]:
    t0 = time.time()

    expected_keys = _get_expected_keys(config_activa)
    title_to_key = _build_title_to_key_map(expected_keys)
    headings = _detect_headings(texto_completo)
    matched = _map_headings_to_keys(headings, title_to_key)

    matched_keys = {k for _, k in matched}
    text_matches = _find_text_matches(texto_completo, expected_keys, matched_keys)
    matched.extend(text_matches)
    matched.sort(key=lambda x: x[0])

    seen = set()
    deduped = []
    for pos, key in matched:
        if key not in seen:
            seen.add(key)
            deduped.append((pos, key))
    matched = deduped

    secciones = _extract_sections(texto_completo, matched)

    detected = list(secciones.keys())
    ausentes = [s for s in expected_keys if s not in detected]
    mapa_relevancia = _build_relevance_map(competencias_activas, detected, config_activa)
    secciones_con_pesos = {}
    for sec_name, sec_text in secciones.items():
        peso = _get_section_weight(sec_name, config_activa)
        secciones_con_pesos[sec_name] = {"texto": sec_text, "peso": peso}
    reporte = {
        "secciones_detectadas": detected,
        "heading_titles": [(h[2], h[0]) for h in headings],
        "secciones_ausentes": ausentes,
        "total_secciones": len(detected),
        "tiempo_c2_s": round(time.time() - t0, 3),
    }
    if reporte_c1:
        reporte.update(reporte_c1)
    return {
        "secciones_informe": secciones_con_pesos,
        "mapa_relevancia": mapa_relevancia,
        "reporte": reporte,
    }
