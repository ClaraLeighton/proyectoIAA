import re
import time
from typing import Any


def _name_to_keywords(name: str) -> list[str]:
    parts = re.split(r'[_\-\s]+', name)
    return [p for p in parts if len(p) > 2]


def _build_section_patterns(config_activa: dict) -> list[tuple[str, list[str]]]:
    patterns = []
    for section_name, section_data in config_activa.items():
        subsecciones = section_data.get("subsecciones") or section_data.get("subsections", {})
        if subsecciones:
            for sub_name in subsecciones:
                keywords = _name_to_keywords(sub_name)
                if not keywords:
                    keywords = [sub_name.lower()]
                patterns.append((sub_name, keywords))
        else:
            keywords = _name_to_keywords(section_name)
            if not keywords:
                keywords = [section_name.lower()]
            patterns.append((section_name, keywords))
    return patterns


def _split_into_sections(text: str, patterns: list[tuple[str, list[str]]]) -> dict[str, str]:
    sections: dict[str, str] = {}
    text_lower = text.lower()
    matches = []
    for sec_name, keywords in patterns:
        for kw in keywords:
            for m in re.finditer(re.escape(kw), text_lower):
                matches.append((m.start(), sec_name))
    matches.sort(key=lambda x: x[0])
    merged = []
    for start, sec_name in matches:
        if merged and merged[-1][1] == sec_name:
            continue
        if merged and abs(start - merged[-1][0]) < 20:
            continue
        merged.append((start, sec_name))
    for i, (start, sec_name) in enumerate(merged):
        end = merged[i + 1][0] if i + 1 < len(merged) else len(text)
        chunk = text[start:end].strip()
        if len(chunk) > 50:
            if sec_name not in sections:
                sections[sec_name] = chunk
            else:
                sections[sec_name] += "\n" + chunk
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
    sorted_weights = sorted(set(weights.values()), reverse=True)
    if len(sorted_weights) < 3:
        thresholds = [None, None]
        for s in detected_sections:
            w = weights.get(s, 0.1)
        primary_set = {s for s in detected_sections if weights.get(s, 0.1) >= 0.2}
        contextual_set = {s for s in detected_sections if weights.get(s, 0.1) < 0.1}
    else:
        n = len(sorted_weights)
        t1 = sorted_weights[n // 3]
        t2 = sorted_weights[2 * n // 3]
        primary_set = {s for s in detected_sections if weights.get(s, 0.1) >= t1}
        contextual_set = {s for s in detected_sections if weights.get(s, 0.1) < t2}

    mapa: dict[str, dict[str, str]] = {}
    for comp in competencias:
        cid = comp["competencia_id"]
        mapa[cid] = {}
        for sec in detected_sections:
            if sec in primary_set:
                mapa[cid][sec] = "principal"
            elif sec in contextual_set:
                mapa[cid][sec] = "contextual"
            else:
                mapa[cid][sec] = "secundaria"
    return mapa


def _get_section_weight(sec_name: str, config_activa: dict) -> float:
    for section_name, section_data in config_activa.items():
        subsecciones = section_data.get("subsecciones") or section_data.get("subsections", {})
        if sec_name in subsecciones:
            return float(subsecciones[sec_name])
        if sec_name == section_name:
            return _get_weight(section_data)
    return 0.1


def run(
    texto_completo: str,
    competencias_activas: list[dict],
    config_activa: dict,
    reporte_c1: dict | None = None,
) -> dict[str, Any]:
    t0 = time.time()
    patterns = _build_section_patterns(config_activa)
    secciones = _split_into_sections(texto_completo, patterns)
    detected = list(secciones.keys())
    expected = set()
    for section_name, section_data in config_activa.items():
        subsecciones = section_data.get("subsecciones") or section_data.get("subsections", {})
        if subsecciones:
            expected.update(subsecciones.keys())
        else:
            expected.add(section_name)
    ausentes = [s for s in expected if s not in detected]
    mapa_relevancia = _build_relevance_map(competencias_activas, detected, config_activa)
    secciones_con_pesos = {}
    for sec_name, sec_text in secciones.items():
        peso = _get_section_weight(sec_name, config_activa)
        secciones_con_pesos[sec_name] = {"texto": sec_text, "peso": peso}
    reporte = {
        "secciones_detectadas": detected,
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
