import uuid
from typing import Any, Callable

from pipeline.db import (
    init_db, guardar_reporte, actualizar_estado_reporte,
    guardar_resultados_competencia, log_reporte,
)
from pipeline.orchestrator import ejecutar_pipeline_completo
from pipeline.c8_macro import computar_macro


BATCH_SIZE = 10


def _procesar_un_reporte(
    reporte_id: str,
    nombre: str,
    pdf_bytes: bytes,
    tipo: str,
    api_key: str,
    csv_bytes: bytes | None,
    json_bytes: bytes | None,
    provider: str,
    c6_provider: str,
    c6_api_key: str | None,
    use_pdf: bool,
    top_k: int,
    umbral: float,
    embedding_model: str | None,
    llm_model: str | None,
    progress_callback: Callable | None,
    output_callback: Callable | None,
) -> dict:
    log_reporte(reporte_id, "Iniciando pipeline C1-C7")
    try:
        pipeline_state = ejecutar_pipeline_completo(
            pdf_bytes=pdf_bytes,
            api_key=api_key,
            csv_bytes=csv_bytes,
            json_bytes=json_bytes,
            provider=provider,
            c6_provider=c6_provider,
            c6_api_key=c6_api_key,
            use_pdf=use_pdf,
            top_k=top_k,
            umbral=umbral,
            embedding_model=embedding_model,
            llm_model=llm_model,
            tipo_documento=tipo,
            progress_callback=progress_callback,
            output_callback=output_callback,
        )
        resultados = pipeline_state["resultados_competencias"]
        preview = pipeline_state["c7"]["vista_preliminar"]["resultados_competencias"]

        for rc, prv in zip(resultados, preview):
            rc["reporte_id"] = reporte_id
            rc["jpc"] = prv.get("jpc", 0.0)
            rc["c_cobertura_citas"] = prv.get("c_cobertura_citas", 0.0)
            rc["s_pertinencia_seccion"] = prv.get("s_pertinencia_seccion", 0.0)
            rc["r_similitud_promedio"] = prv.get("r_similitud_promedio", 0.0)
            rc["f_confianza"] = prv.get("f_confianza", 0.0)
            rc["nivel_label"] = prv.get("nivel_label", "")
            rc["estado_revision"] = prv.get("estado_revision", "sin_evidencia")
            rc["estado_final"] = prv.get("estado_final", "pendiente")
            rc["secciones_fuente"] = prv.get("secciones_fuente", [])
            rc["confianza"] = prv.get("confianza", 0.0)

        guardar_resultados_competencia(reporte_id, resultados)
        actualizar_estado_reporte(reporte_id, "completado")
        log_reporte(reporte_id, "Pipeline completado exitosamente")

        return {
            "id": reporte_id,
            "nombre": nombre,
            "tipo": tipo,
            "exito": True,
            "total_competencias": len(resultados),
        }
    except Exception as e:
        actualizar_estado_reporte(reporte_id, "error", str(e))
        log_reporte(reporte_id, f"Error: {e}")
        return {
            "id": reporte_id,
            "nombre": nombre,
            "tipo": tipo,
            "exito": False,
            "error": str(e),
        }


def procesar_lote(
    reportes: list[dict],
    api_key: str,
    csv_bytes: bytes | None = None,
    json_bytes: bytes | None = None,
    provider: str = "gemini",
    c6_provider: str = "gemini",
    c6_api_key: str | None = None,
    use_pdf: bool = False,
    top_k: int = 5,
    umbral: float = 0.65,
    embedding_model: str | None = None,
    llm_model: str | None = None,
    batch_size: int = BATCH_SIZE,
    progress_callback: Callable | None = None,
    output_callback: Callable | None = None,
    on_batch_complete: Callable | None = None,
) -> dict[str, Any]:
    init_db()
    total = len(reportes)
    resultados_finales = []
    errores = []

    for batch_start in range(0, total, batch_size):
        batch = reportes[batch_start:batch_start + batch_size]

        if progress_callback:
            progress_callback("BATCH", f"Procesando informe... (0/{total})")

        for r in batch:
            guardar_reporte(r["id"], r["nombre"], r["tipo"], "procesando")

        for r in batch:
            if progress_callback:
                idx = len(resultados_finales) + len(errores) + 1
                progress_callback("BATCH", f"Procesando: {r['nombre']} ({idx}/{total})")

            res = _procesar_un_reporte(
                r["id"], r["nombre"], r["bytes"], r["tipo"],
                api_key, csv_bytes, json_bytes,
                provider, c6_provider, c6_api_key, use_pdf,
                top_k, umbral, embedding_model, llm_model,
                progress_callback, output_callback,
            )
            if res["exito"]:
                resultados_finales.append(res)
            else:
                errores.append(res)

            if progress_callback:
                completados = len(resultados_finales)
                progress_callback("BATCH", f"Completado: {r['nombre']} ({completados}/{total})")

        if on_batch_complete:
            on_batch_complete()

    return {
        "total": total,
        "exitosos": len(resultados_finales),
        "errores": len(errores),
        "resultados": resultados_finales,
        "detalle_errores": errores,
    }


def recalcular_macro() -> dict:
    init_db()
    resultados_db = obtener_todos_los_resultados()
    from pipeline import c1_ingesta
    import json
    grouped: dict[str, list[dict]] = {}
    for rc in resultados_db:
        rc_dict = dict(rc) if hasattr(rc, "__getitem__") else rc
        tipo = rc_dict.get("tipo", "")
        if tipo not in grouped:
            grouped[tipo] = []
        grouped[tipo].append(rc_dict)

    wrapped = []
    for tipo, res_list in grouped.items():
        reporte_ids = set(r.get("reporte_id", "") for r in res_list)
        for rid in reporte_ids:
            comps = [r for r in res_list if r.get("reporte_id") == rid]
            wrapped.append({
                "tipo": tipo,
                "reporte_id": rid,
                "resultados_competencias": comps,
            })

    macro = computar_macro(wrapped)
    return macro
