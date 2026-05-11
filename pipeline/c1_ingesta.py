import fitz
import json
import re
import time
import io
from typing import Any
import pandas as pd


def _extract_text_pymupdf(pdf_bytes: bytes) -> tuple[str, dict]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages_text = []
    for page in doc:
        pages_text.append(page.get_text())
    full_text = "\n".join(pages_text)
    metadata = doc.metadata or {}
    doc.close()
    return full_text, metadata


def _extract_all_section_names(config: dict) -> list[str]:
    names = []
    for section_name, section_data in config.items():
        subsecciones = section_data.get("subsecciones") or section_data.get("subsections", {})
        if subsecciones:
            names.extend(subsecciones.keys())
        else:
            names.append(section_name)
    return names


def _name_to_keywords(name: str) -> list[str]:
    parts = re.split(r'[_\-\s]+', name)
    return [p for p in parts if len(p) > 2]


def _appears_in_text(text: str, section_name: str) -> bool:
    keywords = _name_to_keywords(section_name)
    if not keywords:
        return section_name.lower() in text.lower()
    text_lower = text.lower()
    matches = sum(1 for kw in keywords if kw.lower() in text_lower)
    return matches >= max(1, len(keywords) // 2)


def _detect_document_type(text: str, rubric: dict) -> str:
    types = list(rubric.keys())
    if not types:
        raise ValueError("La rúbrica no contiene ningún tipo de documento.")
    if len(types) == 1:
        return types[0]
    best_type = types[0]
    best_score = 0
    for doc_type in types:
        config = rubric.get(doc_type, {})
        sections = _extract_all_section_names(config)
        score = sum(1 for s in sections if _appears_in_text(text, s))
        if score > best_score:
            best_score = score
            best_type = doc_type
    return best_type


def _get_weight(entry: dict) -> float:
    for key in ("peso", "weight", "poids", "gewicht"):
        val = entry.get(key)
        if val is not None:
            return float(val)
    return 0.1


def _is_truthy(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in ("x", "yes", "1", "true", "sí", "si", "v", "t", "y")


def _normalize_type_name(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', name.strip().lower()).strip('_')


def _load_competency_matrix(csv_bytes: bytes | None, csv_path: str | None) -> pd.DataFrame:
    if csv_bytes is not None:
        df = pd.read_csv(io.BytesIO(csv_bytes), header=None)
    elif csv_path is not None:
        df = pd.read_csv(csv_path, header=None)
    else:
        raise ValueError("Se requiere csv_bytes o csv_path para cargar la matriz.")
    return df


def _detect_matrix_format(df_raw: pd.DataFrame) -> str:
    first_row = [str(v).strip().lower() for v in df_raw.iloc[0].tolist() if pd.notna(v)]
    joined = " ".join(first_row)
    if re.search(r'\b(competencia_id|competencia|nombre|descripcion)\b', joined):
        return "standard"
    return "legacy"


def _parse_matrix_standard(df_raw: pd.DataFrame, rubric_types: list[str]) -> pd.DataFrame:
    df = df_raw.copy()
    df.columns = [str(c).strip().lower() for c in df.iloc[0]]
    df = df.iloc[1:].reset_index(drop=True)
    id_col = None
    name_col = None
    desc_col = None
    type_cols = []
    for col in df.columns:
        cl = col.lower()
        if any(k in cl for k in ("competencia_id", "id", "code", "código", "codigo")):
            id_col = col
        elif any(k in cl for k in ("nombre", "name", "titulo", "título")):
            name_col = col
        elif any(k in cl for k in ("descripcion", "description", "desc")):
            desc_col = col
        else:
            for rt in rubric_types:
                if _normalize_type_name(cl) == _normalize_type_name(rt):
                    type_cols.append((col, rt))
                    break
    if not id_col:
        df["competencia_id"] = [f"C{i+1}" for i in range(len(df))]
        id_col = "competencia_id"
    if not name_col:
        name_col = id_col
    if not desc_col:
        df["descripcion"] = df[name_col]
        desc_col = "descripcion"
    rows = []
    for _, row in df.iterrows():
        entry = {
            "competencia_id": str(row.get(id_col, "")),
            "nombre": str(row.get(name_col, "")),
            "descripcion": str(row.get(desc_col, "")),
        }
        for csv_col, doc_type in type_cols:
            val = row.get(csv_col, False)
            entry[doc_type] = _is_truthy(val)
        rows.append(entry)
    return pd.DataFrame(rows)


def _parse_matrix_legacy(df_raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if df_raw.shape[0] < 3:
        return pd.DataFrame(columns=["competencia_id", "nombre", "descripcion"])
    type_names_raw = [str(df_raw.iloc[i, 0]).strip() for i in range(2, df_raw.shape[0]) if pd.notna(df_raw.iloc[i, 0])]
    type_names = [_normalize_type_name(t) for t in type_names_raw]
    for col_idx in range(1, df_raw.shape[1]):
        desc = str(df_raw.iloc[1, col_idx]) if pd.notna(df_raw.iloc[1, col_idx]) else ""
        if not desc:
            continue
        short = desc.split(",")[0].strip() if "," in desc else desc[:80].strip()
        entry = {
            "competencia_id": f"C{col_idx}",
            "nombre": short,
            "descripcion": desc,
        }
        for i, tname in enumerate(type_names):
            row_idx = 2 + i
            if row_idx < df_raw.shape[0]:
                val = df_raw.iloc[row_idx, col_idx]
                entry[tname] = _is_truthy(val)
            else:
                entry[tname] = False
        rows.append(entry)
    return pd.DataFrame(rows)


def _filter_matrix_by_type(df: pd.DataFrame, doc_type: str) -> list[dict]:
    norm_doc = _normalize_type_name(doc_type)
    matching_cols = [c for c in df.columns if _normalize_type_name(c) == norm_doc]
    if not matching_cols:
        return df[["competencia_id", "nombre", "descripcion"]].to_dict("records")
    col = matching_cols[0]
    mask = df[col] == True
    filtered = df[mask][["competencia_id", "nombre", "descripcion"]].copy()
    return filtered.to_dict("records")


def _load_rubric(json_bytes: bytes | None, json_path: str | None) -> dict:
    if json_bytes is not None:
        return json.loads(json_bytes.decode("utf-8"))
    elif json_path is not None:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        raise ValueError("Se requiere json_bytes o json_path para cargar la rúbrica.")


def run(
    pdf_bytes: bytes,
    csv_bytes: bytes | None = None,
    json_bytes: bytes | None = None,
    csv_path: str | None = None,
    json_path: str | None = None,
) -> dict[str, Any]:
    t0 = time.time()
    errors: list[str] = []

    if not pdf_bytes:
        raise ValueError("No se proporcionó ningún PDF.")
    texto, metadatos = _extract_text_pymupdf(pdf_bytes)
    if len(texto.strip()) < 100:
        errors.append("El PDF tiene muy poco texto extraíble (posiblemente escaneado).")

    rubrica = _load_rubric(json_bytes, json_path)
    tipo_documento = _detect_document_type(texto, rubrica)
    config_activa = rubrica.get(tipo_documento, {})

    df_raw = _load_competency_matrix(csv_bytes, csv_path)
    fmt = _detect_matrix_format(df_raw)
    if fmt == "standard":
        df_parsed = _parse_matrix_standard(df_raw, list(rubrica.keys()))
    else:
        df_parsed = _parse_matrix_legacy(df_raw)
    competencias_activas = _filter_matrix_by_type(df_parsed, tipo_documento)

    reporte = {
        "tipo_documento": tipo_documento,
        "formato_matriz": fmt,
        "metadatos_pdf": metadatos,
        "competencias_esperadas": [c["competencia_id"] for c in competencias_activas],
        "total_competencias_esperadas": len(competencias_activas),
        "errores_c1": errors,
        "tiempo_c1_s": round(time.time() - t0, 3),
    }

    return {
        "texto_completo": texto,
        "metadatos": metadatos,
        "tipo_documento": tipo_documento,
        "competencias_activas": competencias_activas,
        "rubrica": rubrica,
        "config_activa": config_activa,
        "reporte": reporte,
    }
