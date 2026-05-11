import time
import math
from typing import Any


def _entropy(p: list[float]) -> float:
    eps = 1e-12
    return -sum(pi * math.log2(pi + eps) for pi in p)


def _max_probability(p: list[float]) -> float:
    return max(p)


def _calc_jpc(c_cobertura: float, s_pertinencia: float, r_similitud: float, f_confianza: float) -> float:
    return round((min(c_cobertura, 1.0) + min(s_pertinencia, 1.0) + min(r_similitud, 1.0) + min(f_confianza, 1.0)) / 4, 4)


def _calc_seccion_score(secciones_fuente: list[str], mapa_relevancia: dict, competencia_id: str) -> float:
    if not secciones_fuente:
        return 0.0
    tipo_score = {"principal": 1.0, "secundaria": 0.7, "contextual": 0.4}
    rel_map = mapa_relevancia.get(competencia_id, {})
    score = 0.0
    for sec in set(secciones_fuente):
        tipo = rel_map.get(sec, "contextual")
        score += tipo_score.get(tipo, 0.4)
    return round(score / len(set(secciones_fuente)), 4) if secciones_fuente else 0.0


def run(
    resultados_competencias: list[dict],
    mapa_relevancia: dict[str, dict[str, str]],
    reportes_acumulados: list[dict],
    tiempos: dict | None = None,
    niveles_labels: dict[int, str] | None = None,
) -> dict[str, Any]:
    t0 = time.time()
    if niveles_labels is None:
        niveles_labels = {0: "Sin Evidencia", 1: "Bajo", 2: "Medio", 3: "Alto"}
    preview_results = []
    trazabilidad = []
    for res in resultados_competencias:
        cid = res["competencia_id"]
        nivel = res.get("nivel", 0)
        p = res.get("p", [0.25, 0.25, 0.25, 0.25])
        citas = res.get("citas", [])
        evidencia = res.get("evidencia_recuperada", [])
        justificacion = res.get("justificacion", "")
        secciones_fuente = [e.get("seccion", "") for e in evidencia]
        r_similitud = res.get("r_similitud", 0.0)
        if r_similitud == 0.0 and evidencia:
            sims = [e.get("similitud", 0.0) for e in evidencia]
            r_similitud = round(sum(sims) / len(sims), 4)
        confianza = _max_probability(p)
        entropy = round(_entropy(p), 4)
        c_cobertura = round(min(len(citas) / 3.0, 1.0), 4)
        s_pertinencia = _calc_seccion_score(secciones_fuente, mapa_relevancia, cid)
        f_confianza = round(confianza, 4)
        jpc = _calc_jpc(c_cobertura, s_pertinencia, r_similitud, f_confianza)
        estado_revision = "respaldo_suficiente"
        if nivel == 0:
            estado_revision = "sin_evidencia"
        elif len(evidencia) < 2 or jpc < 0.5:
            estado_revision = "requiere_revision"
        elif jpc >= 0.7:
            estado_revision = "respaldo_suficiente"
        preview_results.append({
            "competencia_id": cid,
            "competencia_nombre": res.get("competencia_nombre", ""),
            "nivel": nivel,
            "nivel_label": niveles_labels.get(nivel, f"Nivel {nivel}"),
            "secciones_fuente": list(set(secciones_fuente)),
            "citas": citas,
            "justificacion": justificacion,
            "estado_revision": estado_revision,
            "estado_final": "pendiente",
            "p": p,
            "confianza": confianza,
            "entropy": entropy,
            "raw_response": res.get("raw_response", ""),
        })
        reporte_comp = {
            "competencia_id": cid,
            "embedding_generado": True,
            "similitud_calculada": True,
            "recuperacion_ejecutada": len(evidencia) > 0,
            "chunks_recuperados": len(evidencia),
            "dictamen_generado": nivel > 0 or len(citas) > 0,
            "estado_cobertura": "procesada" if (nivel > 0 or len(citas) > 0) else "sin_evidencia",
            "estado_final": "pendiente",
            "nivel_asignado": nivel,
        }
        for i, prob in enumerate(p):
            reporte_comp[f"p{i}"] = prob
        reporte_comp["C_cobertura_citas"] = c_cobertura
        reporte_comp["S_pertinencia_seccion"] = s_pertinencia
        reporte_comp["R_similitud_promedio"] = r_similitud
        reporte_comp["F_confianza"] = f_confianza
        reporte_comp["JPC"] = jpc
        reporte_comp["JPC_aplicable"] = estado_revision in ("respaldo_suficiente",)
        trazabilidad.append(reporte_comp)
    if tiempos is None:
        tiempos = {
            "T_procesamiento_automatico_min": None,
            "T_revision_humana_min": None,
            "T_ajustes_min": None,
            "T_IA_total_min": None,
        }
    reporte_procesamiento = {
        "trazabilidad_competencias": trazabilidad,
        "tiempos": tiempos,
        "historial_ajustes": [],
    }
    if reportes_acumulados:
        for r in reportes_acumulados:
            if isinstance(r, dict):
                for k, v in r.items():
                    if k not in ("trazabilidad_competencias", "tiempos", "historial_ajustes"):
                        continue
                    if k == "trazabilidad_competencias" and isinstance(v, list):
                        existing = {tr["competencia_id"] for tr in reporte_procesamiento["trazabilidad_competencias"]}
                        for entry in v:
                            if entry.get("competencia_id") not in existing:
                                reporte_procesamiento["trazabilidad_competencias"].append(entry)
                    elif k == "tiempos" and isinstance(v, dict):
                        reporte_procesamiento["tiempos"].update(v)
        reporte_procesamiento["tiempo_c7_s"] = round(time.time() - t0, 3)
    return {
        "vista_preliminar": {
            "resultados_competencias": preview_results,
        },
        "reporte_procesamiento": reporte_procesamiento,
    }
