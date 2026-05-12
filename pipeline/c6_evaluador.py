import json
import time
import re
from typing import Any
from pipeline.providers import evaluate_llm, SUPPORTED_PROVIDERS


DEFAULT_LEVELS = {
    0: "Sin evidencia",
    1: "No demuestra aplicación",
    2: "Uso concreto con resultados descritos",
    3: "Dominio técnico con reflexión e impacto",
}

DEFAULT_LEVEL_DETAILS = {
    0: [
        "No hay mención de la competencia en el documento.",
        "No se identifica ningún trabajo relacionado con la competencia.",
    ],
    1: [
        "El estudiante menciona herramientas, conceptos o actividades relacionados, pero sin demostrar aplicación práctica.",
        "Se describe una actividad sin profundidad técnica ni resultados tangibles.",
    ],
    2: [
        "El estudiante implementa soluciones con herramientas específicas.",
        "Se describen resultados tangibles (reducción de tiempo, mejora de funcionalidad, etc.).",
        "Hay evidencia de decisiones técnicas, pero sin reflexión profunda sobre alternativas.",
    ],
    3: [
        "El estudiante demuestra dominio técnico profundo: evalúa alternativas, justifica decisiones, considera trade-offs.",
        "Implementa soluciones con patrones de diseño, seguridad, escalabilidad o mantenibilidad.",
        "Reflexiona críticamente sobre las decisiones tomadas.",
        "Demuestra impacto cuantificable y cualitativo en el proyecto o equipo.",
    ],
}


def _extract_levels(config_activa: dict) -> tuple[dict[int, str], dict[int, list[str]]]:
    levels_def = config_activa.get("niveles_evaluacion") or config_activa.get("evaluation_levels")
    if levels_def:
        labels = {}
        details = {}
        for item in levels_def:
            nivel = item.get("nivel") or item.get("level", 0)
            label = item.get("etiqueta") or item.get("label", f"Nivel {nivel}")
            descs = item.get("descripcion") or item.get("description", [])
            if not isinstance(descs, list):
                descs = [str(descs)]
            labels[int(nivel)] = str(label)
            details[int(nivel)] = [str(d) for d in descs]
        if labels:
            return labels, details
    return DEFAULT_LEVELS, DEFAULT_LEVEL_DETAILS


def _build_system_prompt() -> str:
    return """Eres un evaluador académico especializado en evaluar competencias.
Tu tarea es evaluar el desempeño de un estudiante en una competencia basándote
ÚNICAMENTE en la evidencia textual proporcionada.
No debes hacer suposiciones ni inferencias más allá de lo que el texto explícitamente comunica."""


def _build_rubric_text(levels: dict[int, str], level_details: dict[int, list[str]]) -> str:
    lines = ["Criterios de evaluación:"]
    for nivel in sorted(levels.keys()):
        lines.append(f"\nNivel {nivel}: {levels[nivel]}")
        for detail in level_details.get(nivel, []):
            lines.append(f"- {detail}")
    return "\n".join(lines)


def _build_competency_text(
    competencia: dict,
    evidencia: list[dict],
) -> str:
    text = f"Competencia: {competencia.get('competencia_id', '')} - {competencia.get('nombre', '')}\n"
    text += f"Descripción: {competencia.get('descripcion', '')}\n\n"
    if evidencia:
        text += "Evidencia disponible:\n"
        for i, frag in enumerate(evidencia):
            text += f"  Fragmento {i+1} (ID: {frag['chunk_id']}, Similitud: {frag['similitud']:.2f}) \"{frag['texto']}\"\n"
    else:
        text += "  Sin evidencia disponible.\n"
    return text


def _build_user_prompt(
    competencia: dict,
    evidencia: list[dict],
    levels: dict[int, str],
    level_details: dict[int, list[str]],
    max_level: int,
) -> str:
    rubric_text = _build_rubric_text(levels, level_details)
    comp_text = _build_competency_text(competencia, evidencia)

    prompt = f"""RÚBRICA DE EVALUACIÓN
{rubric_text}

COMPETENCIA A EVALUAR
{comp_text}

FORMATO DE SALIDA
Debes responder ÚNICAMENTE con un objeto JSON válido, sin texto adicional.
El JSON debe tener esta estructura:
{{
  "evaluaciones": [
    {{
      "competencia_id": "<id de la competencia>",
      "nivel": <entero entre 0 y {max_level}>,
      "justificacion": "<string de máximo 2 oraciones>",
      "citas": ["<cita_1>", ...],
      "p": [<float>, <float>, ...]
    }}
  ]
}}

Reglas:
- Debes incluir UNA evaluación (un solo elemento en evaluaciones).
- "citas" debe contener fragmentos textuales exactos de la evidencia proporcionada (puede ser vacío si nivel=0).
- "p" es la distribución de probabilidad para niveles [0..{max_level}]. Debe sumar 1 y tener {max_level + 1} elementos.
- El nivel asignado debe ser coherente con p (el mayor valor de p debe corresponder al nivel asignado)."""
    return prompt


def _build_user_prompt_sin_evidencia(
    competencia: dict,
    levels: dict[int, str],
    level_details: dict[int, list[str]],
    max_level: int,
) -> str:
    """Prompt sin evidencia inline — solo rúbrica + nombre de competencia. La evidencia se adjunta como PDF."""
    rubric_text = _build_rubric_text(levels, level_details)
    prompt = f"""RÚBRICA DE EVALUACIÓN
{rubric_text}

COMPETENCIA A EVALUAR
Competencia: {competencia.get('competencia_id', '')} - {competencia.get('nombre', '')}
Descripción: {competencia.get('descripcion', '')}

La evidencia de esta competencia se encuentra en el PDF adjunto.

FORMATO DE SALIDA
Debes responder ÚNICAMENTE con un objeto JSON válido, sin texto adicional.
El JSON debe tener esta estructura:
{{
  "evaluaciones": [
    {{
      "competencia_id": "<id de la competencia>",
      "nivel": <entero entre 0 y {max_level}>,
      "justificacion": "<string de máximo 2 oraciones>",
      "citas": ["<cita_1>", ...],
      "p": [<float>, <float>, ...]
    }}
  ]
}}

Reglas:
- Debes incluir UNA evaluación (un solo elemento en evaluaciones).
- "citas" debe contener fragmentos textuales exactos de la evidencia del PDF adjunto (puede ser vacío si nivel=0).
- "p" es la distribución de probabilidad para niveles [0..{max_level}]. Debe sumar 1 y tener {max_level + 1} elementos.
- El nivel asignado debe ser coherente con p (el mayor valor de p debe corresponder al nivel asignado)."""
    return prompt


def _fix_json(raw: str) -> str | None:
    """Attempt to fix common LLM JSON formatting errors (mismatched/extra/missing closing brackets)."""
    stack = []
    chars = list(raw)
    for i, ch in enumerate(chars):
        if ch in "{[":
            stack.append((ch, i))
        elif ch == "}":
            if stack and stack[-1][0] == "{":
                stack.pop()
            elif stack and stack[-1][0] == "[":
                chars[i] = "]"
                stack.pop()
            else:
                chars[i] = ""
        elif ch == "]":
            if stack and stack[-1][0] == "[":
                stack.pop()
            elif stack and stack[-1][0] == "{":
                chars[i] = "}"
                stack.pop()
            else:
                chars[i] = ""

    fixed = "".join(chars)
    ob = fixed.count("{")
    cb = fixed.count("}")
    obr = fixed.count("[")
    cbr = fixed.count("]")
    if cb < ob:
        fixed += "}" * (ob - cb)
    if cbr < obr:
        fixed += "]" * (obr - cbr)
    return fixed


def _parse_batch_response(raw: str, num_levels: int) -> list[dict] | None:
    raw_clean = raw.strip()
    json_match = re.search(r"\{.*\}", raw_clean, re.DOTALL)
    if not json_match:
        return None

    data = None
    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError:
        fixed = _fix_json(json_match.group())
        if fixed:
            try:
                data = json.loads(fixed)
            except json.JSONDecodeError:
                return None
        else:
            return None

    evaluaciones = data.get("evaluaciones")
    if not isinstance(evaluaciones, list) or not evaluaciones:
        return None
    results = []
    for ev in evaluaciones:
        cid = ev.get("competencia_id", "")
        nivel = ev.get("nivel")
        if not isinstance(nivel, int):
            try:
                nivel = int(nivel)
            except (TypeError, ValueError):
                nivel = 0
        nivel = max(0, min(nivel, num_levels - 1))
        justificacion = str(ev.get("justificacion", ""))
        citas = ev.get("citas", [])
        if not isinstance(citas, list):
            citas = []
        p = ev.get("p")
        if not isinstance(p, list) or len(p) != num_levels:
            default_p = 1.0 / num_levels
            p = [default_p] * num_levels
        total = sum(p)
        if total > 0:
            p = [round(v / total, 4) for v in p]
        results.append({
            "competencia_id": cid,
            "nivel": nivel,
            "justificacion": justificacion,
            "citas": citas,
            "p": p,
        })
    return results


def _call_llm(
    system_prompt: str,
    user_prompt: str,
    provider: str,
    api_key: str,
    model: str,
    evidence_text: str | None = None,
) -> str:
    evidence_texts = [evidence_text] if evidence_text else None
    return evaluate_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        provider=provider,
        api_key=api_key,
        model=model,
        evidence_texts=evidence_texts,
    )


def run_batch(
    competencias_con_evidencia: list[tuple[dict, list[dict]]],
    api_key: str,
    model: str | None = None,
    provider: str = "gemini",
    config_activa: dict | None = None,
    use_pdf: bool = False,
) -> list[dict]:
    m = model or SUPPORTED_PROVIDERS.get(provider, {}).get("llm_model", "models/gemini-2.5-flash")
    cfg = config_activa or {}
    levels, level_details = _extract_levels(cfg)
    max_level = max(levels.keys())
    sys_prompt = _build_system_prompt()

    resultados = []
    use_pdf_effective = use_pdf
    for comp, evidencia in competencias_con_evidencia:
        t0 = time.time()
        error_msg = ""

        if use_pdf_effective:
            evidence_block = _build_competency_text(comp, evidencia)
            user_prompt = _build_user_prompt_sin_evidencia(comp, levels, level_details, max_level)
            raw = _call_llm(sys_prompt, user_prompt, provider, api_key, m, evidence_block)
        else:
            user_prompt = _build_user_prompt(comp, evidencia, levels, level_details, max_level)
            raw = _call_llm(sys_prompt, user_prompt, provider, api_key, m)

        if raw.startswith("__LLM_ERROR__"):
            error_msg = raw[len("__LLM_ERROR__"):]

        ev_result = None
        if not error_msg:
            parsed = _parse_batch_response(raw, max_level + 1)
            if parsed:
                ev_result = parsed[0]

        if ev_result:
            ev_result["competencia_nombre"] = comp.get("nombre", "")
            ev_result["max_nivel"] = max_level
            ev_result["raw_response"] = raw
            ev_result["reporte"] = {
                "competencia_id": comp["competencia_id"],
                "estado_capa_6": "OK" if ev_result["nivel"] > 0 else "OK_NIVEL0",
                "dictamen_generado": ev_result["nivel"] > 0 or ev_result["citas"],
                "formato_llm_ok": True,
                "citas_validas": True,
                "modelo_llm": m,
                "proveedor": provider,
                "uso_pdf": use_pdf_effective,
                "error": None,
                "tiempo_c6_s": round(time.time() - t0, 3),
            }
            resultados.append(ev_result)
        else:
            resultados.append({
                "competencia_id": comp["competencia_id"],
                "competencia_nombre": comp.get("nombre", ""),
                "nivel": 0,
                "justificacion": f"Error al procesar la respuesta del LLM. {error_msg}" if error_msg else "Error al procesar la respuesta del LLM.",
                "citas": [],
                "p": [1.0 / (max_level + 1)] * (max_level + 1),
                "max_nivel": max_level,
                "raw_response": raw,
                "reporte": {
                    "competencia_id": comp["competencia_id"],
                    "estado_capa_6": "ERROR",
                    "dictamen_generado": False,
                    "formato_llm_ok": False,
                    "citas_validas": False,
                    "modelo_llm": m,
                    "proveedor": provider,
                    "uso_pdf": use_pdf_effective,
                    "error": error_msg if error_msg else "Respuesta del LLM no válida",
                    "tiempo_c6_s": round(time.time() - t0, 3),
                },
            })
    return resultados


def run(
    competencia: dict,
    evidencia_recuperada: list[dict],
    api_key: str,
    model: str | None = None,
    provider: str = "gemini",
    config_activa: dict | None = None,
    use_pdf: bool = False,
    reporte_c5: dict | None = None,
) -> dict[str, Any]:
    resultados = run_batch(
        [(competencia, evidencia_recuperada)],
        api_key=api_key,
        model=model,
        provider=provider,
        config_activa=config_activa,
        use_pdf=use_pdf,
    )
    res = resultados[0] if resultados else {
        "competencia_id": competencia["competencia_id"],
        "competencia_nombre": competencia.get("nombre", ""),
        "nivel": 0,
        "justificacion": "Error interno en la evaluación.",
        "citas": [],
        "p": [0.25, 0.25, 0.25, 0.25],
        "max_nivel": 3,
        "raw_response": "",
        "reporte": {"competencia_id": competencia["competencia_id"], "estado_capa_6": "ERROR"},
    }
    if reporte_c5 and res.get("reporte"):
        res["reporte"].update(reporte_c5)
    return res
