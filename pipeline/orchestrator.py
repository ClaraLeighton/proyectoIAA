import time
from typing import Any

from pipeline import c1_ingesta, c2_parser, c3_chunker, c4_embeddings, c5_retriever, c6_evaluador, c7_agregador
from pipeline.providers import SUPPORTED_PROVIDERS
from pipeline.router import clasificar


def ejecutar_pipeline_completo(
    pdf_bytes: bytes,
    api_key: str,
    csv_bytes: bytes | None = None,
    json_bytes: bytes | None = None,
    csv_path: str = "config/matriz.csv",
    json_path: str = "config/rubrica.json",
    embedding_model: str | None = None,
    llm_model: str | None = None,
    provider: str = "gemini",
    c6_provider: str | None = None,
    c6_api_key: str | None = None,
    use_pdf: bool = False,
    top_k: int = 5,
    umbral: float = 0.65,
    progress_callback: Any = None,
    output_callback: Any = None,
    tipo_documento: str | None = None,
) -> dict[str, Any]:
    t_inicio = time.time()
    estado = {"historial_ajustes": [], "contador_ajustes": 0}
    if progress_callback: progress_callback("C1", "Ingesta del PDF + matriz + rúbrica")
    c1 = c1_ingesta.run(
        pdf_bytes=pdf_bytes,
        csv_bytes=csv_bytes,
        json_bytes=json_bytes,
        csv_path=None if csv_bytes else csv_path,
        json_path=None if json_bytes else json_path,
        tipo_documento=tipo_documento,
    )
    if progress_callback: progress_callback("C2", "Parseo de secciones del documento")
    c2 = c2_parser.run(
        texto_completo=c1["texto_completo"],
        competencias_activas=c1["competencias_activas"],
        config_activa=c1["config_activa"],
        reporte_c1=c1["reporte"],
    )
    if progress_callback: progress_callback("C3", "Fragmentación (chunking) del texto")
    c3 = c3_chunker.run(
        secciones_informe=c2["secciones_informe"],
        reporte_c2=c2["reporte"],
    )
    t_c4 = time.time()
    if progress_callback: progress_callback("C4", "Generación de embeddings (+1 llamada API)")
    chunk_embeddings, comp_embeddings_c4, model_c4 = c4_embeddings.compute_embeddings(
        chunks=c3["chunks"],
        competencias_activas=c1["competencias_activas"],
        api_key=api_key,
        model=embedding_model,
        provider=provider,
    )
    provider_c4 = provider
    levels, _ = c6_evaluador._extract_levels(c1["config_activa"])
    resultados_competencias = []
    c5_results = []
    c6_results = []
    similarities_by_comp = {}
    trazabilidad_c4 = []
    n_comps = len(c1["competencias_activas"])
    c6_prov = c6_provider or provider
    for i, comp in enumerate(c1["competencias_activas"]):
        cid = comp["competencia_id"]

        if progress_callback: progress_callback("C4", f"Similitud coseno ({i+1}/{n_comps}) — {cid}")
        comp_vec = comp_embeddings_c4.get(cid, [])
        sims = c4_embeddings.compute_similarity(
            competencia=comp,
            chunks=c3["chunks"],
            chunk_embeddings=chunk_embeddings,
            comp_embedding=comp_vec,
        )
        similarities_by_comp[cid] = sims
        trazabilidad_c4.append({
            "competencia_id": cid,
            "embedding_generado": len(comp_vec) > 0,
            "similitud_calculada": True,
            "chunks_comparados": len(c3["chunks"]),
            "estado_capa_4": "OK" if len(comp_vec) > 0 else "ERROR",
        })

        if progress_callback: progress_callback("C5", f"Recuperación de evidencia ({i+1}/{n_comps}) — {cid}")
        c5 = c5_retriever.run(
            competencia=comp,
            similarities=sims,
            chunks=c3["chunks"],
            mapa_relevancia=c2["mapa_relevancia"],
            top_k=top_k,
            umbral=umbral,
        )
        c5_results.append(c5)

        if progress_callback: progress_callback("C6", f"Evaluación LLM ({i+1}/{n_comps}) — {cid}")
        c6_res = c6_evaluador.run(
            competencia=comp,
            evidencia_recuperada=c5["evidencia_recuperada"],
            api_key=c6_api_key or api_key,
            model=llm_model,
            provider=c6_prov,
            config_activa=c1["config_activa"],
            use_pdf=use_pdf,
        )
        c6_results.append(c6_res)
        if output_callback:
            output_callback("C6", c6_res.get("raw_response", ""))
        if progress_callback: progress_callback("C6", f"Evaluación LLM ({i+1}/{n_comps}) — {cid} ✓")
    embeddings_data = c4_embeddings.build_embeddings_data(c3["chunks"], chunk_embeddings)
    c4 = {
        "embeddings_data": embeddings_data,
        "comp_embeddings": comp_embeddings_c4,
        "similarities_by_comp": similarities_by_comp,
        "reporte": {
            "trazabilidad_competencias": trazabilidad_c4,
            "modelo_embeddings": model_c4,
            "proveedor": provider_c4,
            "tiempo_c4_s": round(time.time() - t_c4, 3),
        },
    }
    if c3["reporte"]:
        c4["reporte"].update(c3["reporte"])
    for i, c6 in enumerate(c6_results):
        c5 = c5_results[i] if i < len(c5_results) else None
        resultados_competencias.append({
            **c6,
            "evidencia_recuperada": c5["evidencia_recuperada"] if c5 else [],
            "r_similitud": c5["reporte"].get("R_similitud_promedio", 0.0) if c5 else 0.0,
        })
    reportes_por_competencia = [r.get("reporte", {}) for r in c6_results]
    c7 = c7_agregador.run(
        resultados_competencias=resultados_competencias,
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
        "resultados_competencias": resultados_competencias,
        "estado": estado,
        "provider": provider,
        "c6_provider": c6_provider or provider,
        "c6_api_key": c6_api_key,
    }
    return pipeline_state


def procesar_ajuste(
    pipeline_state: dict[str, Any],
    solicitud: str,
    competencia_id: str,
    api_key: str,
    llm_model: str | None = None,
) -> dict[str, Any]:
    t_ajuste = time.time()
    clasificacion = clasificar(solicitud)
    capa = clasificacion["capa_destino"]
    tipo = clasificacion["tipo"]
    idx = None
    for i, r in enumerate(pipeline_state["resultados_competencias"]):
        if r["competencia_id"] == competencia_id:
            idx = i
            break
    if idx is None:
        return pipeline_state
    capas_reprocesadas = []
    if capa == "C5" and tipo in ("cita_agregar", "cita_remover"):
        comp = next(c for c in pipeline_state["c1"]["competencias_activas"] if c["competencia_id"] == competencia_id)
        c5_result = c5_retriever.run(
            competencia=comp,
            similarities=pipeline_state["c4"]["similarities_by_comp"].get(competencia_id, {}),
            chunks=pipeline_state["c3"]["chunks"],
            mapa_relevancia=pipeline_state["c2"]["mapa_relevancia"],
        )
        pipeline_state["resultados_competencias"][idx].update({
            "evidencia_recuperada": c5_result["evidencia_recuperada"],
            "r_similitud": c5_result["reporte"].get("R_similitud_promedio", 0.0),
        })
        capas_reprocesadas.append("C5")
    if capa == "C6" or (capa == "C5" and capas_reprocesadas):
        comp = next(c for c in pipeline_state["c1"]["competencias_activas"] if c["competencia_id"] == competencia_id)
        evidencia = pipeline_state["resultados_competencias"][idx].get("evidencia_recuperada", [])
        c6_provider = pipeline_state.get("c6_provider") or pipeline_state.get("provider", "gemini")
        c6_api_key = pipeline_state.get("c6_api_key") or api_key
        if llm_model is None:
            llm_model = SUPPORTED_PROVIDERS.get(c6_provider, {}).get("llm_model", "models/gemini-2.5-flash")
        if c6_provider == "openrouter" and not c6_api_key:
            import os as _os
            c6_api_key = _os.getenv("OPENROUTER_API_KEY", "")
        c6_result = c6_evaluador.run(
            competencia=comp,
            evidencia_recuperada=evidencia,
            api_key=c6_api_key,
            model=llm_model,
            provider=c6_provider,
            config_activa=pipeline_state["c1"]["config_activa"],
        )
        if tipo == "nivel" and clasificacion["parametros"].get("nuevo_nivel") is not None:
            c6_result["nivel"] = clasificacion["parametros"]["nuevo_nivel"]
        pipeline_state["resultados_competencias"][idx].update({
            "nivel": c6_result["nivel"],
            "justificacion": c6_result["justificacion"],
            "citas": c6_result["citas"],
            "p": c6_result["p"],
        })
        capas_reprocesadas.append("C6")
    if capa == "C2":
        c2_result = c2_parser.run(
            texto_completo=pipeline_state["c1"]["texto_completo"],
            competencias_activas=pipeline_state["c1"]["competencias_activas"],
            config_activa=pipeline_state["c1"]["config_activa"],
        )
        pipeline_state["c2"] = c2_result
        capas_reprocesadas.append("C2")
    if capa == "C7" or capas_reprocesadas:
        levels, _ = c6_evaluador._extract_levels(pipeline_state["c1"]["config_activa"])
        c7_result = c7_agregador.run(
            resultados_competencias=pipeline_state["resultados_competencias"],
            mapa_relevancia=pipeline_state["c2"]["mapa_relevancia"],
            reportes_acumulados=[],
            tiempos=pipeline_state["c7"]["reporte_procesamiento"]["tiempos"],
            niveles_labels=levels,
        )
        pipeline_state["c7"] = c7_result
        capas_reprocesadas.append("C7")
    tiempo_ajuste_min = round((time.time() - t_ajuste) / 60, 2)
    pipeline_state["estado"]["contador_ajustes"] += 1
    ajuste_record = {
        "ajuste_id": f"ajuste_{pipeline_state['estado']['contador_ajustes']:02d}",
        "competencia_id": competencia_id,
        "solicitud_usuario": solicitud,
        "clasificacion": clasificacion,
        "capas_reprocesadas": capas_reprocesadas,
        "duracion_min": tiempo_ajuste_min,
        "resultado": "reporte_actualizado",
    }
    pipeline_state["estado"]["historial_ajustes"].append(ajuste_record)
    pipeline_state["c7"]["reporte_procesamiento"]["historial_ajustes"] = pipeline_state["estado"]["historial_ajustes"]
    tiempos = pipeline_state["c7"]["reporte_procesamiento"]["tiempos"]
    if tiempos.get("T_ajustes_min") is not None:
        tiempos["T_ajustes_min"] = round(tiempos["T_ajustes_min"] + tiempo_ajuste_min, 2)
    else:
        tiempos["T_ajustes_min"] = tiempo_ajuste_min
    if tiempos.get("T_revision_humana_min") is None:
        tiempos["T_revision_humana_min"] = 0.0
    total = sum(v for v in tiempos.values() if v is not None)
    tiempos["T_IA_total_min"] = round(total, 2)
    pipeline_state["c7"]["reporte_procesamiento"]["tiempos"] = tiempos
    return pipeline_state


def actualizar_competencia_manual(
    pipeline_state: dict[str, Any],
    competencia_id: str,
    campo: str,
    valor: Any,
) -> dict[str, Any]:
    for r in pipeline_state["c7"]["vista_preliminar"]["resultados_competencias"]:
        if r["competencia_id"] == competencia_id:
            r[campo] = valor
            break
    for r in pipeline_state["resultados_competencias"]:
        if r["competencia_id"] == competencia_id:
            r[campo] = valor
            break
    for tr in pipeline_state["c7"]["reporte_procesamiento"]["trazabilidad_competencias"]:
        if tr["competencia_id"] == competencia_id and campo in ("nivel",):
            tr["nivel_asignado"] = valor
            break
    if campo == "estado_final":
        for tr in pipeline_state["c7"]["reporte_procesamiento"]["trazabilidad_competencias"]:
            if tr["competencia_id"] == competencia_id:
                tr["estado_final"] = valor
                break
    return pipeline_state
