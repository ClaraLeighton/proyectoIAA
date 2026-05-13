import json
import os
import uuid
from datetime import datetime
from typing import Any

from pipeline.persistence import DATA_DIR, load_report, load_index

COHORTS_PATH = os.path.join(DATA_DIR, "cohorts.json")

NIVEL_MAX = 3


def _ensure_cohorts_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(COHORTS_PATH):
        with open(COHORTS_PATH, "w") as f:
            json.dump([], f)


def _load_cohorts() -> list[dict]:
    _ensure_cohorts_file()
    with open(COHORTS_PATH, "r") as f:
        content = f.read()
        if not content.strip():
            return []
        return json.loads(content)


def _save_cohorts(cohorts: list[dict]):
    with open(COHORTS_PATH, "w") as f:
        json.dump(cohorts, f, indent=2, ensure_ascii=False)


def list_cohorts() -> list[dict]:
    return _load_cohorts()


def get_cohort(cohort_id: str) -> dict | None:
    for c in _load_cohorts():
        if c["cohort_id"] == cohort_id:
            return c
    return None


def create_cohort(name: str, tipo_documento: str) -> dict:
    cohort = {
        "cohort_id": str(uuid.uuid4()),
        "name": name,
        "tipo_documento": tipo_documento,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "report_ids": [],
    }
    cohorts = _load_cohorts()
    cohorts.append(cohort)
    _save_cohorts(cohorts)
    return cohort


def delete_cohort(cohort_id: str) -> int:
    from pipeline.persistence import delete_report
    cohorts = _load_cohorts()
    cohort = next((c for c in cohorts if c["cohort_id"] == cohort_id), None)
    if not cohort:
        return 0
    n_reports = len(cohort["report_ids"])
    for rid in cohort["report_ids"]:
        delete_report(rid)
    cohorts = [c for c in cohorts if c["cohort_id"] != cohort_id]
    _save_cohorts(cohorts)
    return n_reports


def update_cohort_name(cohort_id: str, new_name: str) -> bool:
    cohorts = _load_cohorts()
    for c in cohorts:
        if c["cohort_id"] == cohort_id:
            c["name"] = new_name
            c["updated_at"] = datetime.now().isoformat()
            _save_cohorts(cohorts)
            return True
    return False


def add_reports_to_cohort(cohort_id: str, report_ids: list[str]):
    cohorts = _load_cohorts()
    for c in cohorts:
        if c["cohort_id"] == cohort_id:
            existing = set(c["report_ids"])
            new_ids = [rid for rid in report_ids if rid not in existing]
            c["report_ids"].extend(new_ids)
            c["updated_at"] = datetime.now().isoformat()
            break
    _save_cohorts(cohorts)


def remove_report_from_cohort(cohort_id: str, report_id: str):
    from pipeline.persistence import delete_report
    cohorts = _load_cohorts()
    for c in cohorts:
        if c["cohort_id"] == cohort_id:
            if report_id in c["report_ids"]:
                c["report_ids"].remove(report_id)
                c["updated_at"] = datetime.now().isoformat()
            break
    _save_cohorts(cohorts)
    delete_report(report_id)


def compute_cohort_macro(cohort_id: str) -> dict:
    cohort = get_cohort(cohort_id)
    if not cohort:
        return _empty_macro()

    tipo = cohort["tipo_documento"]
    all_results = []

    for rid in cohort["report_ids"]:
        report = load_report(rid)
        if not report or report.estado != "completado":
            continue
        preview = report.vista_preliminar
        if not preview:
            continue
        report_entry = {
            "tipo": tipo,
            "resultados_competencias": [],
        }
        for r in preview:
            entry = {
                "competencia_id": r.get("competencia_id", ""),
                "competencia_nombre": r.get("competencia_nombre", ""),
                "nivel": r.get("nivel", 0),
                "jpc": r.get("JPC", r.get("jpc", 0)),
                "confianza": r.get("confianza", 0),
                "reporte_id": rid,
                "reporte_nombre": report.pdf_name,
            }
            report_entry["resultados_competencias"].append(entry)
        all_results.append(report_entry)

    return _aggregate_macro(all_results, tipo)


def _empty_macro() -> dict:
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


def _aggregate_macro(resultados: list[dict], tipo: str) -> dict:
    resultados_competencias = []
    for r in resultados:
        rc = r.get("resultados_competencias", [])
        if rc:
            resultados_competencias.extend(rc)

    if not resultados_competencias:
        return _empty_macro()

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
        confianzas = []
        nombres = set()
        for rc in resultados_competencias:
            if not isinstance(rc, dict):
                continue
            if rc.get("competencia_id") == cid:
                nivel = rc.get("nivel", 0)
                if isinstance(nivel, (int, float)):
                    niveles.append(nivel)
                jpc = rc.get("jpc", 0.0)
                if isinstance(jpc, (int, float)):
                    jpcs.append(jpc)
                conf = rc.get("confianza", 0.0)
                if isinstance(conf, (int, float)):
                    confianzas.append(conf)
                if rc.get("competencia_nombre"):
                    nombres.add(rc["competencia_nombre"])

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
        confianza_promedio = round(sum(confianzas) / len(confianzas), 4) if confianzas else 0.0

        distribucion = {"0": 0, "1": 0, "2": 0, "3": 0}
        for n in niveles:
            n_int = int(n) if not isinstance(n, int) else n
            distribucion[str(n_int)] = distribucion.get(str(n_int), 0) + 1

        competencias[cid] = {
            "nombre": next(iter(nombres), ""),
            "nivel_promedio": nivel_promedio,
            "score": f"{score_actual}/{score_max}",
            "score_actual": score_actual,
            "score_max": score_max,
            "score_pct": score_pct,
            "tasa_aprobacion": tasa_aprobacion,
            "aprobadas": aprobadas,
            "total_reportes": n_total,
            "distribucion": distribucion,
            "jpc_promedio": jpc_promedio,
            "confianza_promedio": confianza_promedio,
        }
        score_total += score_actual
        score_max_total += score_max

    global_score_pct = round(score_total / score_max_total, 4) if score_max_total > 0 else 0.0
    total_niveles = sum(len([rc for rc in resultados_competencias if rc.get("competencia_id") == cid and isinstance(rc.get("nivel"), (int, float))]) for cid in comp_ids)
    nivel_prom_global = round(score_total / total_niveles, 2) if total_niveles > 0 else 0.0

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
        "tipo_documento": tipo,
    }
