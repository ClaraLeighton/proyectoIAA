from pipeline.c6_evaluador import _extract_levels, _build_user_prompt, _build_user_prompt_sin_evidencia, _parse_batch_response, _extract_json, FALLBACK_MODELS


def test_extract_levels_default():
    levels, details = _extract_levels({})
    assert len(levels) == 4
    assert levels[0] == "Sin evidencia"
    assert levels[3] == "Dominio técnico con reflexión e impacto"


def test_extract_levels_from_config():
    config = {
        "niveles_evaluacion": [
            {"nivel": 0, "etiqueta": "Nada", "descripcion": ["Sin evidencia en absoluto"]},
            {"nivel": 1, "etiqueta": "Poco", "descripcion": ["Evidencia mínima"]},
            {"nivel": 2, "etiqueta": "Suficiente", "descripcion": ["Evidencia adecuada"]},
        ]
    }
    levels, details = _extract_levels(config)
    assert len(levels) == 3
    assert levels[0] == "Nada"
    assert levels[2] == "Suficiente"
    assert details[1] == ["Evidencia mínima"]


def test_build_user_prompt():
    levels = {0: "None", 1: "Basic", 2: "Advanced"}
    details = {0: ["No evidence"], 1: ["Some mention"], 2: ["Full mastery"]}
    comp = {"competencia_id": "C1", "nombre": "Test", "descripcion": "Test desc"}
    evidencia = []
    prompt = _build_user_prompt(comp, evidencia, levels, details, 2)
    assert "None" in prompt
    assert "Basic" in prompt
    assert "Advanced" in prompt
    assert "C1" in prompt
    assert "Sin evidencia disponible" in prompt
    assert "INSTRUCCIONES ESTRICTAS" in prompt
    assert "EXACTAMENTE" in prompt


def test_build_user_prompt_sin_evidencia():
    levels = {0: "None", 1: "Basic", 2: "Advanced"}
    details = {0: ["No evidence"], 1: ["Some mention"], 2: ["Full mastery"]}
    comp = {"competencia_id": "C1", "nombre": "Test", "descripcion": "Test desc"}
    prompt = _build_user_prompt_sin_evidencia(comp, levels, details, 2)
    assert "None" in prompt
    assert "Basic" in prompt
    assert "PDF adjunto" in prompt
    assert "C1" in prompt
    assert "INSTRUCCIONES ESTRICTAS" in prompt
    assert "EXACTAMENTE" in prompt


def test_parse_batch_response():
    raw = '{"evaluaciones": [{"competencia_id": "C1", "nivel": 2, "justificacion": "Bien", "citas": ["cita1"], "p": [0.1, 0.2, 0.6, 0.1]}]}'
    result = _parse_batch_response(raw, 4)
    assert result is not None
    assert len(result) == 1
    assert result[0]["competencia_id"] == "C1"
    assert result[0]["nivel"] == 2


def test_parse_batch_response_markdown():
    raw = '```json\n{"evaluaciones": [{"competencia_id": "C1", "nivel": 1, "justificacion": "Ok", "citas": [], "p": [0.5, 0.3, 0.1, 0.1]}]}\n```'
    result = _parse_batch_response(raw, 4)
    assert result is not None
    assert result[0]["nivel"] == 1


def test_parse_batch_response_with_extra_text():
    raw = 'Aquí está el JSON:\n{"evaluaciones": [{"competencia_id": "C1", "nivel": 2, "justificacion": "Bien", "citas": ["cita"], "p": [0.1, 0.2, 0.6, 0.1]}]}\n\nEspero que sea útil.'
    result = _parse_batch_response(raw, 4)
    assert result is not None
    assert result[0]["nivel"] == 2


def test_parse_batch_response_empty():
    result = _parse_batch_response("", 4)
    assert result is None


def test_parse_batch_response_no_json():
    result = _parse_batch_response("Esto no es JSON en absoluto.", 4)
    assert result is None


def test_parse_batch_response_markdown_no_lang():
    raw = '```\n{"evaluaciones": [{"competencia_id": "C1", "nivel": 1, "justificacion": "Ok", "citas": [], "p": [0.5, 0.3, 0.1, 0.1]}]}\n```'
    result = _parse_batch_response(raw, 4)
    assert result is not None
    assert result[0]["nivel"] == 1


def test_extract_json_simple():
    result = _extract_json('{"key": "value"}')
    assert result == '{"key": "value"}'


def test_extract_json_with_fix():
    result = _extract_json('{"nivel": 2, "tiene_justificacion": true')
    assert result is not None
    import json
    parsed = json.loads(result)
    assert parsed["nivel"] == 2
    assert parsed["tiene_justificacion"] is True


def test_extract_json_markdown():
    result = _extract_json('```json\n{"key": "value"}\n```')
    assert result == '{"key": "value"}'


def test_extract_json_no_braces():
    result = _extract_json("hello world")
    assert result is None


def test_extract_json_empty():
    result = _extract_json("")
    assert result is None


def test_fallback_models_defined():
    assert len(FALLBACK_MODELS) > 0
    assert "google/gemini-2.5-flash" in FALLBACK_MODELS
