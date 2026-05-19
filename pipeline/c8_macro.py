from typing import Any

NIVEL_MAX = 3


def computar_macro(resultados: list[dict]) -> dict[str, Any]:
    if not resultados:
        return {"pre_professional_practice": _vacio(), "professional_practice": _vacio()}

    tipos = set(r.get("tipo", "") for r in resultados)
    macro = {}
    for t in tipos:
        reportes_tipo = [r for r in resultados if r.get("tipo") == t]
        macro[t] = _computar_por_tipo(reportes_tipo)
    for t in ("pre_professional_practice", "professional_practice"):
        if t not in macro:
            macro[t] = _vacio()
    return macro


def _vacio() -> dict:
    return {
        "competencias": {},
        "global": {
            "total_reportes": 0,
            "total_competencias": 0,
            "score_actual": 0,
            "score_max": 0,
            "score_pct": 0.0,
            "tasa_aprobacion_global": 0.0,
            "nivel_promedio_global": 0.0,
        },
    }


def _computar_por_tipo(resultados: list[dict]) -> dict:
    resultados_competencias = []
    for r in resultados:
        rc = r.get("resultados_competencias", [])
        if rc:
            resultados_competencias.extend(rc)

    if not resultados_competencias:
        return _vacio()

    comp_ids = sorted(set(
        rc["competencia_id"] for rc in resultados_competencias
        if isinstance(rc, dict) and "competencia_id" in rc
    ))

    competencias = {}
    score_total = 0
    score_max_total = 0
    n_reportes_unicos = len(set(
        rc.get("reporte_id", "")
        for rc in resultados_competencias
        if isinstance(rc, dict) and rc.get("reporte_id")
    ))
    if n_reportes_unicos == 0:
        n_reportes_unicos = len(resultados)

    for cid in comp_ids:
        niveles = []
        jpcs = []
        for rc in resultados_competencias:
            if not isinstance(rc, dict):
                continue
            if rc.get("competencia_id") == cid:
                nivel = rc.get("nivel", 0)
                if isinstance(nivel, (int, float)):
                    niveles.append(nivel)
                jpc = rc.get("jpc", rc.get("JPC", 0.0))
                if isinstance(jpc, (int, float)):
                    jpcs.append(jpc)

        if not niveles:
            continue

        n_total = len(niveles)
        score_actual = sum(niveles)
        score_max = n_total * NIVEL_MAX
        nivel_promedio = round(score_actual / n_total, 2)
        score_pct = round(score_actual / score_max, 4) if score_max > 0 else 0.0
        aprobadas = sum(1 for n in niveles if n >= 2)
        tasa_aprobacion = round(aprobadas / n_total, 4) if n_total > 0 else 0.0
        jpc_promedio = round(sum(jpcs) / len(jpcs), 4) if jpcs else 0.0

        distribucion = {0: 0, 1: 0, 2: 0, 3: 0}
        for n in niveles:
            n_int = int(n) if not isinstance(n, int) else n
            distribucion[n_int] = distribucion.get(n_int, 0) + 1

        competencias[cid] = {
            "nivel_promedio": nivel_promedio,
            "score": f"{score_actual}/{score_max}",
            "score_actual": score_actual,
            "score_max": score_max,
            "score_pct": score_pct,
            "tasa_aprobacion": tasa_aprobacion,
            "aprobadas": aprobadas,
            "total_reportes": n_total,
            "distribucion": {str(k): v for k, v in distribucion.items()},
            "jpc_promedio": jpc_promedio,
        }
        score_total += score_actual
        score_max_total += score_max

    global_score_pct = round(score_total / score_max_total, 4) if score_max_total > 0 else 0.0
    nivel_prom_global = round(score_total / (len(competencias) * n_reportes_unicos), 2) if competencias and n_reportes_unicos else 0.0

    total_aprobadas = sum(c["aprobadas"] for c in competencias.values())
    total_eval = sum(c["total_reportes"] for c in competencias.values())
    tasa_global = round(total_aprobadas / total_eval, 4) if total_eval > 0 else 0.0

    return {
        "competencias": competencias,
        "global": {
            "total_reportes": n_reportes_unicos,
            "total_competencias": len(competencias),
            "score_actual": score_total,
            "score_max": score_max_total,
            "score_pct": global_score_pct,
            "tasa_aprobacion_global": tasa_global,
            "nivel_promedio_global": nivel_prom_global,
        },
    }
