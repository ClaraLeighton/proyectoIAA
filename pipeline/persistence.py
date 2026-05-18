import json
import os
import hashlib
import shutil
import tempfile
from typing import Any
from pipeline.models import ReportResult

DATA_DIR = "data"
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
INDEX_PATH = os.path.join(DATA_DIR, "index.json")


def compute_file_hash(pdf_bytes: bytes) -> str:
    return hashlib.sha256(pdf_bytes).hexdigest()


def find_duplicates_within_batch(pending: list[dict]) -> dict[str, list[dict]]:
    by_hash: dict[str, list[dict]] = {}
    for p in pending:
        file_hash = p.get("file_hash", "")
        if not file_hash:
            continue
        by_hash.setdefault(file_hash, []).append(p)
    return {h: items for h, items in by_hash.items() if len(items) > 1}


def find_duplicate_files(pending: list[dict], existing_report_ids: set[str] | None = None) -> dict[str, dict]:
    index = load_index()
    if existing_report_ids is not None:
        index = [e for e in index if e["report_id"] in existing_report_ids]
    existing_by_name = {e["pdf_name"]: e for e in index}
    existing_by_hash = {e.get("file_hash"): e for e in index if e.get("file_hash")}

    duplicates = {}
    for p in pending:
        pdf_name = p.get("pdf_name", "")
        file_hash = p.get("file_hash", "")

        if file_hash and file_hash in existing_by_hash:
            existing = existing_by_hash[file_hash]
            key = f"{file_hash}:{pdf_name}"
            duplicates[key] = {
                "pdf_name": pdf_name,
                "report_id": existing["report_id"],
                "reason": "hash",
                "existing_name": existing["pdf_name"],
            }
        elif pdf_name in existing_by_name:
            existing = existing_by_name[pdf_name]
            key = f"name:{pdf_name}"
            duplicates[key] = {
                "pdf_name": pdf_name,
                "report_id": existing["report_id"],
                "reason": "name",
                "existing_name": existing["pdf_name"],
            }

    return duplicates


def _ensure_dirs():
    os.makedirs(REPORTS_DIR, exist_ok=True)


def _report_dir(report_id: str) -> str:
    return os.path.join(REPORTS_DIR, report_id)


def save_report(result: ReportResult, pdf_bytes: bytes | None = None):
    _ensure_dirs()
    rdir = _report_dir(result.report_id)
    os.makedirs(rdir, exist_ok=True)

    if pdf_bytes is not None:
        pdf_path = os.path.join(rdir, "report.pdf")
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

    state_path = os.path.join(rdir, "state.json")
    state_copy = dict(result.pipeline_state)
    state_copy.pop("c6_api_key", None)
    tmp_state = state_path + ".tmp"
    with open(tmp_state, "w", encoding="utf-8") as f:
        json.dump(state_copy, f, ensure_ascii=False, indent=2, default=str)
    os.replace(tmp_state, state_path)

    index = load_index()
    entry = result.to_index_entry()
    index = [e for e in index if e["report_id"] != result.report_id]
    index.append(entry)
    tmp_index = INDEX_PATH + ".tmp"
    with open(tmp_index, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    os.replace(tmp_index, INDEX_PATH)


def load_report(report_id: str) -> ReportResult | None:
    state_path = os.path.join(_report_dir(report_id), "state.json")
    if not os.path.exists(state_path):
        return None
    with open(state_path, "r", encoding="utf-8") as f:
        pipeline_state = json.load(f)
    index = load_index()
    entry = next((e for e in index if e["report_id"] == report_id), {})
    return ReportResult(
        report_id=report_id,
        pdf_name=entry.get("pdf_name", ""),
        tipo_documento=entry.get("tipo_documento", ""),
        timestamp=entry.get("timestamp", ""),
        pipeline_state=pipeline_state,
        estado=entry.get("estado", "completado"),
        error=entry.get("error"),
    )


def load_index() -> list[dict]:
    if not os.path.exists(INDEX_PATH):
        return []
    try:
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            content = f.read()
            if not content.strip():
                return []
            return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return []


def delete_report(report_id: str):
    rdir = _report_dir(report_id)
    if os.path.exists(rdir):
        shutil.rmtree(rdir)
    index = [e for e in load_index() if e["report_id"] != report_id]
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def get_report_count_by_status() -> dict[str, int]:
    index = load_index()
    counts = {}
    for e in index:
        s = e.get("estado", "desconocido")
        counts[s] = counts.get(s, 0) + 1
    return counts


def get_global_stats() -> dict[str, Any]:
    index = load_index()
    if not index:
        return {}
    total = len(index)
    completados = [e for e in index if e.get("estado") == "completado"]
    jpc_vals = [e.get("avg_jpc", 0) for e in completados]
    conf_vals = [e.get("avg_confianza", 0) for e in completados]
    nivel_vals = [e.get("nivel_promedio", 0) for e in completados]
    nivel_dist_global = {}
    total_comps = 0
    for e in completados:
        nd = e.get("nivel_distribucion", {})
        for lvl, count in nd.items():
            nivel_dist_global[lvl] = nivel_dist_global.get(lvl, 0) + count
            total_comps += count
    return {
        "total_reports": total,
        "completados": len(completados),
        "errores": sum(1 for e in index if e.get("estado") == "error"),
        "avg_jpc_global": round(sum(jpc_vals) / len(jpc_vals), 4) if jpc_vals else 0.0,
        "avg_confianza_global": round(sum(conf_vals) / len(conf_vals), 4) if conf_vals else 0.0,
        "avg_nivel_global": round(sum(nivel_vals) / len(nivel_vals), 1) if nivel_vals else 0.0,
        "nivel_distribucion_global": nivel_dist_global,
        "total_competencias_global": total_comps,
    }
