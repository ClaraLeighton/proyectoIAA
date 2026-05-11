from pipeline.c2_parser import _build_section_patterns, _split_into_sections, _build_relevance_map


def test_c2_section_patterns_dynamic():
    config = {
        "my_custom_section": {"peso": 0.5, "subsecciones": {"detail_part": 0.3, "summary_part": 0.2}},
        "another_section": {"peso": 0.5},
    }
    patterns = _build_section_patterns(config)
    names = [p[0] for p in patterns]
    assert "detail_part" in names
    assert "summary_part" in names
    assert "another_section" in names


def test_c2_split_sections():
    patterns = [
        ("abstract", ["abstract"]),
        ("work_done", ["work"]),
    ]
    text = "abstract\nThis is a long abstract section with enough content to exceed the minimum threshold of fifty characters for section detection in the parser module.\nwork done\nMain work content area with detailed description of activities performed during the internship period at the company.\n"
    result = _split_into_sections(text, patterns)
    assert "abstract" in result
    assert "work_done" in result


def test_c2_relevance_map_dynamic():
    competencias = [{"competencia_id": "C1"}, {"competencia_id": "C2"}]
    config = {
        "high_weight": {"peso": 0.5},
        "medium_weight": {"peso": 0.2},
        "low_weight": {"peso": 0.05},
    }
    mapa = _build_relevance_map(competencias, ["high_weight", "medium_weight", "low_weight"], config)
    assert mapa["C1"]["high_weight"] == "principal"
    assert mapa["C1"]["low_weight"] in ("secundaria", "contextual")
