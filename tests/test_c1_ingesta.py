import pytest
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def test_c1_ingesta_pdf_vacio():
    from pipeline.c1_ingesta import run
    with pytest.raises(ValueError, match="No se proporcionó ningún PDF"):
        run(pdf_bytes=b"")


def test_c1_detectar_tipo():
    from pipeline.c1_ingesta import _detect_document_type
    rubric = {
        "tipo_a": {"sec1": {"peso": 0.5}, "sec2": {"peso": 0.5}},
        "tipo_b": {"other_section": {"peso": 1.0}},
    }
    text = "This is about sec1 and sec2 content"
    result = _detect_document_type(text, rubric)
    assert result == "tipo_a"


def test_c1_detectar_tipo_solo_uno():
    from pipeline.c1_ingesta import _detect_document_type
    rubric = {"unico_tipo": {"seccion": {"peso": 1.0}}}
    result = _detect_document_type("anything", rubric)
    assert result == "unico_tipo"


def test_c1_cargar_matriz():
    from pipeline.c1_ingesta import _load_competency_matrix, _detect_matrix_format, _parse_matrix_legacy, _filter_matrix_by_type
    csv_path = str(BASE / "config" / "matriz.csv")
    df = _load_competency_matrix(None, csv_path)
    fmt = _detect_matrix_format(df)
    assert fmt == "legacy"
    parsed = _parse_matrix_legacy(df)
    assert "competencia_id" in parsed.columns
    assert "descripcion" in parsed.columns
    pre = _filter_matrix_by_type(parsed, "pre_professional_practice")
    pro = _filter_matrix_by_type(parsed, "professional_practice")
    assert len(pro) > 0


def test_c1_detectar_formato_standard():
    import pandas as pd
    import io
    from pipeline.c1_ingesta import _detect_matrix_format
    csv_data = "competencia_id,nombre,descripcion,tipo_a\nC1,Test,Description,TRUE"
    df = pd.read_csv(io.StringIO(csv_data), header=None)
    fmt = _detect_matrix_format(df)
    assert fmt == "standard"


def test_c1_parse_matrix_standard():
    import pandas as pd
    import io
    from pipeline.c1_ingesta import _parse_matrix_standard
    csv_data = "competencia_id,nombre,descripcion,mi_tipo\nC1,Test,Description,TRUE\nC2,Test2,Desc2,FALSE"
    df = pd.read_csv(io.StringIO(csv_data), header=None)
    parsed = _parse_matrix_standard(df, ["mi_tipo"])
    assert len(parsed) == 2
    assert "mi_tipo" in parsed.columns
    assert parsed.iloc[0]["mi_tipo"] == True


def test_c1_filter_dynamic_type():
    import pandas as pd
    from pipeline.c1_ingesta import _filter_matrix_by_type
    df = pd.DataFrame([
        {"competencia_id": "C1", "nombre": "A", "descripcion": "D1", "mi_tipo_doc": True},
        {"competencia_id": "C2", "nombre": "B", "descripcion": "D2", "mi_tipo_doc": False},
    ])
    filtered = _filter_matrix_by_type(df, "mi_tipo_doc")
    assert len(filtered) == 1
    assert filtered[0]["competencia_id"] == "C1"


def test_c1_normalize_type_name():
    from pipeline.c1_ingesta import _normalize_type_name
    assert _normalize_type_name("Pre-Professional Practice") == "pre_professional_practice"
    assert _normalize_type_name("Mi Tipo De Documento") == "mi_tipo_de_documento"


def test_c1_cargar_rubrica():
    from pipeline.c1_ingesta import _load_rubric
    json_path = str(BASE / "config" / "rubrica.json")
    rubrica = _load_rubric(None, json_path)
    assert len(rubrica) > 0
