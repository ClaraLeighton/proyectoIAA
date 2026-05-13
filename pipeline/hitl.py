from typing import Any
from pipeline import c2_parser, c5_retriever, c6_evaluador, c7_agregador
from pipeline.providers import SUPPORTED_PROVIDERS
from pipeline.router import clasificar


def procesar_ajuste(
    pipeline_state: dict[str, Any],
    solicitud: str,
    competencia_id: str,
    api_key: str,
    llm_model: str | None = None,
) -> dict[str, Any]:
    import time
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
