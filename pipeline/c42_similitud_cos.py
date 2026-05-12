import numpy as np


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    a = np.array(vec_a, dtype=np.float64)
    b = np.array(vec_b, dtype=np.float64)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def compute_similarity(
    comp_embedding: list[float],
    chunk_embeddings: list[list[float]],
    chunks: list[dict],
) -> dict[str, float]:
    """Calcula similitud coseno entre una competencia y todos los chunks."""
    sims: dict[str, float] = {}
    for j, chunk in enumerate(chunks):
        sim = (
            _cosine_similarity(comp_embedding, chunk_embeddings[j])
            if j < len(chunk_embeddings)
            else 0.0
        )
        sims[chunk["chunk_id"]] = sim
    return sims
