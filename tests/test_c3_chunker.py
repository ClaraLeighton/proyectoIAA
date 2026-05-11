from pipeline.c3_chunker import _split_text


def test_split_text_short():
    result = _split_text("Texto corto.", max_chars=500)
    assert len(result) == 1
    assert result[0] == "Texto corto."


def test_split_text_long():
    texto = ". ".join(["Esta es la oración número " + str(i) for i in range(50)])
    result = _split_text(texto, max_chars=500)
    assert len(result) > 1
    assert all(len(c) <= 500 for c in result)
