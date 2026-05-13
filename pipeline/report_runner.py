import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from pipeline import c1_ingesta, c2_parser, c3_chunker, c41_embeddings, c42_similitud_cos, c5_retriever, c6_evaluador, c7_agregador
from pipeline.models import ReportResult, BatchConfig
from pipeline.persistence import save_report


def _safe_progress(progress: dict | None, report_id: str, key: str, value: Any):
    if progress is not None:
        with progress.get("_lock", threading.Lock()):
            if report_id not in progress:
                progress[report_id] = {}
            progress[report_id][key] = value


def _run_competency(
    comp: dict,
    c1: dict,
    c2: dict,
    c3: dict,
    chunk_embeddings: dict,
    comp_embeddings: dict,
    llm_config: dict,
    semaphore: threading.Semaphore,
    top_k: int,
    umbral: float,
    use_pdf: bool,
) -> dict:
    cid = comp["competencia_id"]
    comp_vec = comp_embeddings[cid]
    sims = c42_similitud_cos.compute_similarity(
        comp_embedding=comp_vec,
        chunk_embeddings=chunk_embeddings,
        chunks=c3["chunks"],
    )
    c5 = c5_retriever.run(
        competencia=comp,
        similarities=sims,
        chunks=c3["chunks"],
        mapa_relevancia=c2["mapa_relevancia"],
        top_k=top_k,
        umbral=umbral,
    )
    with semaphore:
        c6_res = c6_evaluador.run(
            competencia=comp,
            evidencia_recuperada=c5["evidencia_recuperada"],
            api_key=llm_config["c6_api_key"],
            model=llm_config.get("llm_model"),
            provider=llm_config["c6_provider"],
            config_activa=c1["config_activa"],
            use_pdf=use_pdf,
        )
    return {
        **c6_res,
        "evidencia_recuperada": c5["evidencia_recuperada"],
        "r_similitud": c5["reporte"]["R_similitud_promedio"],
    }


def process_report(
    report_spec: dict,
    llm_config: dict,
    batch_config: BatchConfig,
    progress: dict | None = None,
) -> ReportResult:
    report_id = report_spec["report_id"]
    t_inicio = time.time()

    _safe_progress(progress, report_id, "stage", "C1")
    c1 = c1_ingesta.run(
        pdf_bytes=report_spec["pdf_bytes"],
        csv_bytes=report_spec.get("csv_bytes"),
        json_bytes=report_spec.get("json_bytes"),
        csv_path="config/matriz.csv",
        json_path="config/rubrica.json",
        tipo_documento=report_spec.get("tipo_documento"),
    )
    _safe_progress(progress, report_id, "stage", "C2")
    c2 = c2_parser.run(
        texto_completo=c1["texto_completo"],
        competencias_activas=c1["competencias_activas"],
        config_activa=c1["config_activa"],
        reporte_c1=c1["reporte"],
    )
    _safe_progress(progress, report_id, "stage", "C3")
    c3 = c3_chunker.run(
        secciones_informe=c2["secciones_informe"],
        reporte_c2=c2["reporte"],
    )
    _safe_progress(progress, report_id, "stage", "C41")
    c41 = c41_embeddings.run(
        chunks=c3["chunks"],
        competencias_activas=c1["competencias_activas"],
        api_key=llm_config["api_key"],
        model=llm_config.get("embedding_model"),
        provider=llm_config["provider"],
    )

    chunk_embeddings = c41["chunk_embeddings"]
    comp_embeddings = c41["comp_embeddings"]
    embeddings_data = c41["embeddings_data"]
    model_c4 = c41["reporte"]["modelo_embeddings"]
    provider_c4 = c41["reporte"]["proveedor"]

    competencies = c1["competencias_activas"]
    n_comps = len(competencies)
    _safe_progress(progress, report_id, "total_comps", n_comps)

    inner_workers = min(n_comps, batch_config.max_workers // 2 + 1)
    global_semaphore = llm_config.get("_semaphore", threading.Semaphore(batch_config.semaphore_limit))
    results = []

    _safe_progress(progress, report_id, "stage", "C42_C5_C6")
    _safe_progress(progress, report_id, "comps_done", 0)

    if n_comps == 1:
        res = _run_competency(
            competencies[0], c1, c2, c3, chunk_embeddings, comp_embeddings,
            llm_config, global_semaphore, report_spec.get("top_k", 5),
            report_spec.get("umbral", 0.65), report_spec.get("use_pdf", False),
        )
        results.append(res)
        _safe_progress(progress, report_id, "comps_done", 1)
    else:
        with ThreadPoolExecutor(max_workers=inner_workers) as executor:
            futures = {}
            for comp in competencies:
                f = executor.submit(
                    _run_competency, comp, c1, c2, c3, chunk_embeddings, comp_embeddings,
                    llm_config, global_semaphore, report_spec.get("top_k", 5),
                    report_spec.get("umbral", 0.65), report_spec.get("use_pdf", False),
                )
                futures[f] = comp["competencia_id"]

            for f in as_completed(futures):
                cid = futures[f]
                try:
                    results.append(f.result())
                    _safe_progress(progress, report_id, "last_comp_done", cid)
                    current_done = sum(1 for _ in futures if _.done())
                    _safe_progress(progress, report_id, "comps_done", current_done)
                except Exception as e:
                    err_result = {
                        "competencia_id": cid,
                        "competencia_nombre": "",
                        "nivel": 0,
                        "justificacion": f"Error: {e}",
                        "citas": [],
                        "p": [0.25, 0.25, 0.25, 0.25],
                        "max_nivel": 3,
                        "raw_response": "",
                        "evidencia_recuperada": [],
                        "r_similitud": 0.0,
                        "reporte": {"competencia_id": cid, "estado_capa_6": "ERROR", "error": str(e)},
                    }
                    results.append(err_result)
                    _safe_progress(progress, report_id, "last_error", cid)

    trazabilidad_c42 = []
    similarities_by_comp = {}
    for comp in competencies:
        cid = comp["competencia_id"]
        comp_vec = comp_embeddings[cid]
        sims = c42_similitud_cos.compute_similarity(
            comp_embedding=comp_vec,
            chunk_embeddings=chunk_embeddings,
            chunks=c3["chunks"],
        )
        similarities_by_comp[cid] = sims
        max_sim = round(max(sims.values()), 4) if sims else 0.0
        trazabilidad_c42.append({
            "competencia_id": cid,
            "embedding_generado": True,
            "similitud_calculada": True,
            "chunks_comparados": len(c3["chunks"]),
            "max_similitud": max_sim,
            "estado_capa_42": "OK" if max_sim > 0 else "SIN_COINCIDENCIA",
        })

    c4 = {
        "embeddings_data": embeddings_data,
        "comp_embeddings": comp_embeddings,
        "similarities_by_comp": similarities_by_comp,
        "reporte": {
            "trazabilidad_competencias": trazabilidad_c42,
            "modelo_embeddings": model_c4,
            "proveedor": provider_c4,
            "tiempo_c4_s": c41["reporte"]["tiempo_c4_s"],
        },
    }
    if c3["reporte"]:
        c4["reporte"].update(c3["reporte"])

    reportes_por_competencia = [r.get("reporte", {}) for r in results]
    levels, _ = c6_evaluador._extract_levels(c1["config_activa"])

    _safe_progress(progress, report_id, "stage", "C7")
    c7 = c7_agregador.run(
        resultados_competencias=results,
        mapa_relevancia=c2["mapa_relevancia"],
        reportes_acumulados=reportes_por_competencia,
        niveles_labels=levels,
    )
    tiempo_auto = round((time.time() - t_inicio) / 60, 2)
    c7["reporte_procesamiento"]["tiempos"]["T_procesamiento_automatico_min"] = tiempo_auto
    c7["reporte_procesamiento"]["historial_ajustes"] = []

    pipeline_state = {
        "c1": c1,
        "c2": c2,
        "c3": c3,
        "c4": c4,
        "c7": c7,
        "resultados_competencias": results,
        "estado": {"historial_ajustes": [], "contador_ajustes": 0},
        "provider": llm_config["provider"],
        "c6_provider": llm_config["c6_provider"],
        "c6_api_key": llm_config["c6_api_key"],
    }

    _safe_progress(progress, report_id, "stage", "done")
    return ReportResult(
        report_id=report_id,
        pdf_name=report_spec.get("pdf_name", ""),
        tipo_documento=report_spec.get("tipo_documento", ""),
        pipeline_state=pipeline_state,
        estado="completado",
    )
