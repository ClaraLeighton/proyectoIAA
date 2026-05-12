from pipeline.c2_parser import (
    is_section_heading,
    _key_to_titles,
    _detect_headings,
    _build_title_to_key_map,
    _map_headings_to_keys,
    _extract_sections,
    _find_text_matches,
    _build_relevance_map,
)


def test_is_section_heading_valid():
    assert is_section_heading("1 Introduction")
    assert is_section_heading("1.1 Company Description")
    assert is_section_heading("2.1 General Activities")
    assert is_section_heading("2.2 Most Challenging Activity")
    assert is_section_heading("3 Company Analysis")
    assert is_section_heading("3.1 Company Analysis")
    assert is_section_heading("3.1 Company/Area Description")
    assert is_section_heading("10.11 Final Section Title")
    assert is_section_heading("Abstract")
    assert is_section_heading("Personal Reflection")


def test_is_section_heading_invalid():
    assert not is_section_heading("This is a paragraph of text that talks about activities in the company")
    assert not is_section_heading("Next, I will describe the four most challenging activities I faced")
    assert not is_section_heading("Image 2.1 Company Structure")
    assert not is_section_heading("Table 3.1 Results Data")
    assert not is_section_heading("Figure 1.1 Diagram")
    assert not is_section_heading("no number here")
    assert not is_section_heading("")
    assert not is_section_heading("   ")
    assert not is_section_heading("1 lower case start")
    assert not is_section_heading("1.2.3.4 Too many levels actually but still matches maybe")


def test_key_to_titles():
    titles = _key_to_titles("company_analysis")
    assert "Company Analysis" in titles

    titles = _key_to_titles("department_area_description")
    assert "Department Area Description" in titles
    assert "Department/Area Description" in titles
    assert "Department/Area/Description" in titles
    assert "Department Description" in titles
    assert "Area Description" in titles

    titles = _key_to_titles("most_challenge_activity")
    assert "Most Challenge Activity" in titles
    assert "Most Challenging Activity" in titles

    titles = _key_to_titles("personal_reflection")
    assert "Personal Reflection" in titles

    titles = _key_to_titles("abstract")
    assert "Abstract" in titles


def test_detect_headings():
    text = (
        "1 Introduction\n"
        "Some introductory text here that is long enough to pass.\n"
        "1.1 Company Description\n"
        "Details about the company and what it does in the business.\n"
        "This line is not a heading.\n"
        "2.1 General Activities\n"
        "Description of general activities performed during internship.\n"
    )
    headings = _detect_headings(text)
    assert len(headings) == 3
    numbers = [h[1] for h in headings]
    titles = [h[2] for h in headings]
    assert titles == ["Introduction", "Company Description", "General Activities"]
    assert numbers == ["1", "1.1", "2.1"]


def test_title_to_key_map():
    mapping = _build_title_to_key_map(["general_activities", "company_analysis"])
    assert mapping["general activities"] == "general_activities"
    assert mapping["company analysis"] == "company_analysis"


def test_map_headings_to_keys():
    title_to_key = _build_title_to_key_map(["general_activities", "company_analysis"])
    headings = [(10, "1", "General Activities"), (50, "2", "Company Analysis")]
    matched = _map_headings_to_keys(headings, title_to_key)
    assert matched == [(10, "general_activities"), (50, "company_analysis")]


def test_extract_sections():
    text = (
        "Company Analysis\n"
        "This section contains the analysis of the company and its internal "
        "processes. It is a fairly long section with enough content.\n"
        "General Activities\n"
        "Here we describe the general activities that were done during the "
        "internship period at the company location.\n"
    )
    matched = [(0, "company_analysis"), (len("Company Analysis\n"
        "This section contains the analysis of the company and its internal "
        "processes. It is a fairly long section with enough content.\n"), "general_activities")]
    sections = _extract_sections(text, matched)
    assert "company_analysis" in sections
    assert "general_activities" in sections
    assert len(sections["company_analysis"]) > 20


def test_integration_title_only():
    text = (
        "Abstract\n"
        "This is the abstract section with enough content to be valid.\n"
        "Personal Reflection\n"
        "My personal reflection on the internship experience and what I "
        "learned during my time at the company organization.\n"
    )
    config = {
        "abstract": {
            "peso": 0.1,
            "subsecciones": {
                "abstract": 0.1,
            },
        },
        "reflexion_personal": {
            "peso": 0.2,
            "subsecciones": {
                "personal_reflection": 0.2,
            },
        },
    }

    expected_keys = ["abstract", "personal_reflection"]
    title_to_key = _build_title_to_key_map(expected_keys)
    headings = _detect_headings(text)
    matched = _map_headings_to_keys(headings, title_to_key)
    sections = _extract_sections(text, matched)

    assert "abstract" in sections
    assert "personal_reflection" in sections


def test_find_text_matches_fallback():
    text = (
        "Abstract\n"
        "This is the abstract with some content.\n"
        "LoRa Communication\n"
        "The company analysis revealed important insights about the\n"
        "organization. My work analysis focused on the technical aspects.\n"
        "After careful consideration, my personal reflection on this\n"
        "internship experience has been very positive overall.\n"
    )
    expected_keys = ["abstract", "company_analysis", "work_analysis", "personal_reflection"]
    title_to_key = _build_title_to_key_map(expected_keys)
    headings = _detect_headings(text)
    matched = _map_headings_to_keys(headings, title_to_key)
    matched_keys = {k for _, k in matched}

    assert "abstract" in matched_keys
    assert "company_analysis" not in matched_keys
    assert "work_analysis" not in matched_keys
    assert "personal_reflection" not in matched_keys

    text_matches = _find_text_matches(text, expected_keys, matched_keys)
    text_keys = {k for _, k in text_matches}

    assert "company_analysis" in text_keys
    assert "work_analysis" in text_keys
    assert "personal_reflection" in text_keys


def test_relevance_map_dynamic():
    competencias = [{"competencia_id": "C1"}, {"competencia_id": "C2"}]
    config = {
        "high_weight": {"peso": 0.5},
        "medium_weight": {"peso": 0.2},
        "low_weight": {"peso": 0.05},
    }
    mapa = _build_relevance_map(competencias, ["high_weight", "medium_weight", "low_weight"], config)
    assert mapa["C1"]["high_weight"] == "principal"
    assert mapa["C1"]["low_weight"] in ("secundaria", "contextual")
