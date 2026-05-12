import time
from typing import Any
from pipeline.providers import get_embeddings, SUPPORTED_PROVIDERS


def _embed_comp_texts(
    texts: list[str],
    provider: str,
    api_key: str,
    model: str,
) -> list[list[float]]:
    """Obtiene embeddings para textos de competencias con reintento individual.

    Primero intenta batch. Si la API devuelve menos resultados de los esperados,
    reintenta cada texto faltante de forma individual.
    """
    if provider == "gemini":
        from google import genai

        client = genai.Client(api_key=api_key)
        all_embeds: list[list[float]] = []

        for i in range(0, len(texts), 20):
            batch = texts[i : i + 20]
            result = client.models.embed_content(model=model, contents=batch)
            batch_embeds = [e.values for e in result.embeddings]

            if len(batch_embeds) == len(batch):
                all_embeds.extend(batch_embeds)
            else:
                for j, text in enumerate(batch):
                    if j < len(batch_embeds) and batch_embeds[j]:
                        all_embeds.append(batch_embeds[j])
                    else:
                        try:
                            single = client.models.embed_content(
                                model=model, contents=text
                            )
                            vec = single.embeddings[0].values
                            all_embeds.append(vec)
                        except Exception:
                            all_embeds.append([])
        return all_embeds

    elif provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        all_embeds: list[list[float]] = []

        for i in range(0, len(texts), 20):
            batch = texts[i : i + 20]
            resp = client.embeddings.create(input=batch, model=model)
            batch_embeds = [d.embedding for d in resp.data]

            if len(batch_embeds) == len(batch):
                all_embeds.extend(batch_embeds)
            else:
                for j, text in enumerate(batch):
                    if j < len(batch_embeds) and batch_embeds[j]:
                        all_embeds.append(batch_embeds[j])
                    else:
                        try:
                            single = client.embeddings.create(
                                input=text, model=model
                            )
                            vec = single.data[0].embedding
                            all_embeds.append(vec)
                        except Exception:
                            all_embeds.append([])
        return all_embeds

    else:
        raise ValueError(f"Provider no soportado para embeddings: {provider}")


def run(
    chunks: list[dict],
    competencias_activas: list[dict],
    api_key: str,
    model: str | None = None,
    provider: str = "gemini",
    reporte_c3: dict | None = None,
) -> dict[str, Any]:
    """Genera embeddings para chunks y competencias. Se ejecuta UNA SOLA VEZ."""
    t0 = time.time()
    m = model or SUPPORTED_PROVIDERS.get(provider, {}).get(
        "embedding_model", "models/gemini-embedding-2"
    )

    chunk_texts = [c["texto"] for c in chunks]
    chunk_embeddings = get_embeddings(chunk_texts, provider, api_key, m)

    comp_texts = [c["descripcion"] for c in competencias_activas]
    comp_embeds = _embed_comp_texts(comp_texts, provider, api_key, m)

    comp_embeddings: dict[str, list[float]] = {}
    for i, comp in enumerate(competencias_activas):
        comp_embeddings[comp["competencia_id"]] = (
            comp_embeds[i] if i < len(comp_embeds) else []
        )

    comps_sin_embedding = [
        cid for cid, vec in comp_embeddings.items() if not vec
    ]
    if comps_sin_embedding:
        raise RuntimeError(
            f"C41: {len(comps_sin_embedding)} competencias sin embedding incluso "
            f"después de reintento individual: {comps_sin_embedding}. "
            f"Verifica que la API de embeddings ({provider}) devolvió resultados para todas."
        )

    embeddings_data = [
        {
            "chunk_id": chunks[j]["chunk_id"],
            "embedding": chunk_embeddings[j],
            "texto": chunks[j]["texto"],
            "seccion": chunks[j]["seccion"],
            "peso": chunks[j]["peso"],
        }
        for j in range(min(len(chunks), len(chunk_embeddings)))
    ]

    reporte = {
        "modelo_embeddings": m,
        "proveedor": provider,
        "chunks_embeddings": len(chunk_embeddings),
        "competencias_embeddings": len(comp_embeddings),
        "tiempo_c4_s": round(time.time() - t0, 3),
    }
    if reporte_c3:
        reporte.update(reporte_c3)

    return {
        "embeddings_data": embeddings_data,
        "chunk_embeddings": chunk_embeddings,
        "comp_embeddings": comp_embeddings,
        "reporte": reporte,
    }
