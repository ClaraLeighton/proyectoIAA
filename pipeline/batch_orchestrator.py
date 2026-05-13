import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from pipeline.models import ReportResult, BatchConfig
from pipeline.report_runner import process_report
from pipeline.persistence import save_report


def _calc_batch_splits(n: int, max_per_batch: int = 10) -> list[int]:
    if n <= max_per_batch:
        return [n]
    num_groups = (n + max_per_batch - 1) // max_per_batch
    base = n // num_groups
    remainder = n % num_groups
    splits = []
    for i in range(num_groups):
        splits.append(base + (1 if i < remainder else 0))
    return splits


def run_batch(
    pending_reports: list[dict],
    llm_config: dict,
    batch_config: BatchConfig | None = None,
    progress: dict | None = None,
) -> list[ReportResult]:
    if batch_config is None:
        batch_config = BatchConfig()

    splits = _calc_batch_splits(len(pending_reports), batch_config.max_reports_per_batch)
    global_semaphore = threading.Semaphore(batch_config.semaphore_limit)
    llm_config["_semaphore"] = global_semaphore

    if progress is not None:
        progress["_lock"] = threading.Lock()
        progress["_total"] = len(pending_reports)
        progress["_done"] = 0
        progress["_errors"] = 0
        progress["_phase"] = "processing"

    all_results: list[ReportResult] = []
    offset = 0

    for batch_size in splits:
        batch = pending_reports[offset:offset + batch_size]
        offset += batch_size

        with ThreadPoolExecutor(max_workers=batch_config.max_workers) as executor:
            futures = {
                executor.submit(process_report, r, llm_config, batch_config, progress): r["report_id"]
                for r in batch
            }
            for future in as_completed(futures):
                report_id = futures[future]
                try:
                    result = future.result()
                    all_results.append(result)
                    if progress is not None:
                        with progress["_lock"]:
                            progress["_done"] = progress.get("_done", 0) + 1
                except Exception as e:
                    pdf_name = next(
                        (r.get("pdf_name", "") for r in pending_reports if r["report_id"] == report_id),
                        "",
                    )
                    error_result = ReportResult(
                        report_id=report_id,
                        pdf_name=pdf_name or report_id,
                        estado="error",
                        error=str(e),
                    )
                    all_results.append(error_result)
                    if progress is not None:
                        with progress["_lock"]:
                            progress["_errors"] = progress.get("_errors", 0) + 1
                            progress["_done"] = progress.get("_done", 0) + 1

    for result in all_results:
        try:
            save_report(result)
        except Exception:
            pass

    if progress is not None:
        with progress["_lock"]:
            progress["_phase"] = "done"
    return all_results
