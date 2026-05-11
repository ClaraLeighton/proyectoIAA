import time
from typing import Any


PRIORITY_ORDER = {"principal": 0, "secundaria": 1, "contextual": 2}


def run(
    competencia: dict,
    similarities: dict[str, float],
    chunks: list[dict],
    mapa_relevancia: dict[str, dict[str, str]],
    top_k: int = 5,
    umbral: float = 0.65,
    min_principal: int = 2,
    reporte_c4: dict | None = None,
) -> dict[str, Any]:
    t0 = time.time()
    cid = competencia["competencia_id"]
    rel_map = mapa_relevancia.get(cid, {})
    ranked = []
    for chunk in chunks:
        chunk_id = chunk["chunk_id"]
        sim = similarities.get(chunk_id, 0.0)
        seccion = chunk["seccion"]
        tipo = rel_map.get(seccion, "contextual")
        priority_order = PRIORITY_ORDER.get(tipo, 99)
        ranked.append({
            "chunk_id": chunk_id,
            "texto": chunk["texto"],
            "seccion": seccion,
            "tipo_fuente": tipo,
            "similitud": sim,
            "peso": chunk.get("peso", 0.1),
            "_priority": priority_order,
        })
    ranked.sort(key=lambda x: (x["_priority"], -x["similitud"]))
    expanded = False
    selected = []
    principales = [r for r in ranked if r["_priority"] == 0 and r["similitud"] >= umbral]
    if len(principales) >= min_principal:
        selected = principales[:top_k]
    else:
        expanded = True
        candidates = [r for r in ranked if r["similitud"] >= umbral]
        candidates.sort(key=lambda x: (x["_priority"], -x["similitud"]))
        selected = candidates[:top_k]
        if len(selected) < min_principal:
            fallback = [r for r in ranked if r["similitud"] >= umbral * 0.8]
            for r in fallback:
                if r["chunk_id"] not in {s["chunk_id"] for s in selected}:
                    selected.append(r)
                if len(selected) >= top_k:
                    break
        if not selected and ranked:
            ranked.sort(key=lambda x: -x["similitud"])
            selected = ranked[:max(1, min(top_k, len(ranked)))]
            expanded = True
    similitudes = [s["similitud"] for s in selected] if selected else [0.0]
    r_metric = round(sum(similitudes) / len(similitudes), 4)
    reporte = {
        "competencia_id": cid,
        "recuperacion_ejecutada": True,
        "chunks_recuperados": len(selected),
        "expansion_fuentes": expanded,
        "estado_capa_5": "OK" if len(selected) > 0 else "SIN_EVIDENCIA",
        "R_similitud_promedio": r_metric,
        "tiempo_c5_s": round(time.time() - t0, 3),
    }
    if reporte_c4:
        reporte.update(reporte_c4)
    return {
        "competencia_id": cid,
        "competencia_nombre": competencia.get("nombre", ""),
        "evidencia_recuperada": selected,
        "reporte": reporte,
    }
