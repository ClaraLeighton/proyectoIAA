from pipeline.router import clasificar


def test_clasificar_nivel():
    r = clasificar("cambiar nivel a 2")
    assert r["tipo"] == "nivel"
    assert r["capa_destino"] == "C6"
    assert r["parametros"].get("nuevo_nivel") == 2


def test_clasificar_cita():
    r = clasificar("agregar la siguiente cita")
    assert r["tipo"] == "cita_agregar"
    assert r["capa_destino"] == "C5"


def test_clasificar_justificacion():
    r = clasificar("editar justificación")
    assert r["tipo"] == "justificacion"
    assert r["capa_destino"] == "C6"


def test_clasificar_desconocido():
    r = clasificar("hola mundo")
    assert r["tipo"] != "desconocido" or r["clasificacion"] == "no_clasificada"
