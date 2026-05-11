import time
import numpy as np
from typing import Any
from pipeline.providers import get_embeddings, SUPPORTED_PROVIDERS


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    a = np.array(vec_a, dtype=np.float64)
    b = np.array(vec_b, dtype=np.float64)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def compute_embeddings(
    chunks: list[dict],
    competencias_activas: list[dict],
    api_key: str,
    model: str | None = None,
    provider: str = "gemini",
) -> tuple[list[list[float]], dict[str, list[float]], str]:
    m = model or SUPPORTED_PROVIDERS.get(provider, {}).get("embedding_model", "models/gemini-embedding-2")
    chunk_texts = [c["texto"] for c in chunks]
    chunk_embeddings = get_embeddings(chunk_texts, provider, api_key, m)
    comp_texts = [c["descripcion"] for c in competencias_activas]
    comp_embeds = get_embeddings(comp_texts, provider, api_key, m)
    comp_embeddings: dict[str, list[float]] = {}
    for i, comp in enumerate(competencias_activas):
        comp_embeddings[comp["competencia_id"]] = comp_embeds[i] if i < len(comp_embeds) else []
    return chunk_embeddings, comp_embeddings, m


def compute_similarity(
    competencia: dict,
    chunks: list[dict],
    chunk_embeddings: list[list[float]],
    comp_embedding: list[float],
) -> dict[str, float]:
    sims: dict[str, float] = {}
    for j, chunk in enumerate(chunks):
        sim = _cosine_similarity(comp_embedding, chunk_embeddings[j]) if j < len(chunk_embeddings) else 0.0
        sims[chunk["chunk_id"]] = sim
    return sims


def build_embeddings_data(
    chunks: list[dict],
    chunk_embeddings: list[list[float]],
) -> list[dict]:
    return [
        {"chunk_id": chunks[j]["chunk_id"], "embedding": chunk_embeddings[j],
         "texto": chunks[j]["texto"], "seccion": chunks[j]["seccion"], "peso": chunks[j]["peso"]}
        for j in range(min(len(chunks), len(chunk_embeddings)))
    ]


def run(
    chunks: list[dict],
    competencias_activas: list[dict],
    api_key: str,
    model: str | None = None,
    provider: str = "gemini",
    reporte_c3: dict | None = None,
) -> dict[str, Any]:
    t0 = time.time()
    chunk_embeddings, comp_embeddings, m = compute_embeddings(chunks, competencias_activas, api_key, model, provider)
    trazabilidad = []
    for comp in competencias_activas:
        cid = comp["competencia_id"]
        comp_vec = comp_embeddings.get(cid, [])
        sims = compute_similarity(comp, chunks, chunk_embeddings, comp_vec)
        trazabilidad.append({
            "competencia_id": cid,
            "embedding_generado": len(comp_vec) > 0,
            "similitud_calculada": True,
            "chunks_comparados": len(chunks),
            "estado_capa_4": "OK" if len(comp_vec) > 0 else "ERROR",
        })
    embeddings_data = build_embeddings_data(chunks, chunk_embeddings)
    reporte = {
        "trazabilidad_competencias": trazabilidad,
        "modelo_embeddings": m,
        "proveedor": provider,
        "tiempo_c4_s": round(time.time() - t0, 3),
    }
    if reporte_c3:
        reporte.update(reporte_c3)
    return {
        "embeddings_data": embeddings_data,
        "comp_embeddings": comp_embeddings,
        "similarities_by_comp": {},
        "reporte": reporte,
    }
