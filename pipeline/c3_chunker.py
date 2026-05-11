import time
from typing import Any


def _split_text(text: str, max_chars: int = 500) -> list[str]:
    if len(text) <= max_chars:
        return [text.strip()]
    chunks = []
    sentences = text.replace("\n", " ").split(". ")
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if not sentence.endswith("."):
            sentence += "."
        if len(current) + len(sentence) + 1 <= max_chars:
            current = (current + " " + sentence).strip() if current else sentence
        else:
            if current:
                chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks


def run(
    secciones_informe: dict[str, dict],
    reporte_c2: dict | None = None,
) -> dict[str, Any]:
    t0 = time.time()
    chunks = []
    chunk_id_counter = 1
    for sec_name, sec_data in secciones_informe.items():
        texto = sec_data.get("texto", "")
        peso = sec_data.get("peso", 0.1)
        fragmentos = _split_text(texto, max_chars=500)
        for pos, frag in enumerate(fragmentos):
            chunks.append({
                "chunk_id": f"c{chunk_id_counter:03d}",
                "texto": frag,
                "seccion": sec_name,
                "peso": peso,
                "posicion": pos,
            })
            chunk_id_counter += 1
    reporte = {
        "total_chunks": len(chunks),
        "tiempo_c3_s": round(time.time() - t0, 3),
    }
    if reporte_c2:
        reporte.update(reporte_c2)
    return {
        "chunks": chunks,
        "reporte": reporte,
    }
