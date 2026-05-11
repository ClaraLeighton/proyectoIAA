import re
from typing import Any


TIPO_MODIFICACION = {
    "nivel": "C6",
    "justificacion": "C6",
    "cita_agregar": "C5",
    "cita_remover": "C5",
    "seccion_prioridad": "C2",
    "metricas": "C7",
}


PATRONES = [
    (r"cambi[aeo]r?\s*(el\s+)?nivel\s+(a\s+)?(\d)", "nivel", {"nuevo_nivel": 3}),
    (r"(asignar|poner|establecer)\s+nivel\s+(\d)", "nivel", {"nuevo_nivel": 2}),
    (r"el\s+nivel\s+(deber[ií]a\s+)?ser\s+(\d)", "nivel", {"nuevo_nivel": 2}),
    (r"modificar\s+(el\s+)?nivel\s+(a\s+)?(\d)", "nivel", {"nuevo_nivel": 3}),
    (r"bajar\s+(el\s+)?nivel\s+(a\s+)?(\d)", "nivel", {"nuevo_nivel": 3}),
    (r"subir\s+(el\s+)?nivel\s+(a\s+)?(\d)", "nivel", {"nuevo_nivel": 3}),
    (r"agreg[ae]r?\s+(la\s+)?(siguiente\s+)?cita", "cita_agregar", {}),
    (r"a[ñn]adir\s+(la\s+)?cita", "cita_agregar", {}),
    (r"incluir\s+(esta\s+)?cita", "cita_agregar", {}),
    (r"(quitar|eliminar|remover|borrar)\s+(la\s+)?cita", "cita_remover", {}),
    (r"cambi[aeo]r?\s+(la\s+)?justificaci[oó]n", "justificacion", {}),
    (r"editar\s+justificaci[oó]n", "justificacion", {}),
    (r"([aá]rea|secci[oó]n)\s+(deber[ií]a\s+)?ser\s+(principal|secundaria|contextual)", "seccion_prioridad", {"nueva_prioridad": 3}),
    (r"actualizar\s+(m[eé]tricas|jpc|confianza)", "metricas", {}),
    (r"recalcular\s+(m[eé]tricas|jpc|confianza)", "metricas", {}),
]


def clasificar(solicitud: str) -> dict[str, Any]:
    solicitud_lower = solicitud.lower().strip()
    for patron, tipo, params_template in PATRONES:
        m = re.search(patron, solicitud_lower)
        if m:
            params = {}
            if "nuevo_nivel" in params_template:
                try:
                    params["nuevo_nivel"] = int(m.group(params_template["nuevo_nivel"]))
                except (IndexError, ValueError):
                    params["nuevo_nivel"] = None
            if "nueva_prioridad" in params_template:
                try:
                    params["nueva_prioridad"] = m.group(params_template["nueva_prioridad"])
                except IndexError:
                    params["nueva_prioridad"] = None
            capa_destino = TIPO_MODIFICACION.get(tipo, "C7")
            return {
                "tipo": tipo,
                "capa_destino": capa_destino,
                "parametros": params,
                "solicitud_original": solicitud,
                "clasificacion": "automatica",
            }
    if len(solicitud_lava := solicitud_lower) > 10:
        if any(w in solicitud_lava for w in ["nivel", "puntaje", "nota"]):
            return {
                "tipo": "nivel",
                "capa_destino": "C6",
                "parametros": {},
                "solicitud_original": solicitud,
                "clasificacion": "aproximada",
            }
        if any(w in solicitud_lava for w in ["cita", "evidencia", "fragmento", "texto"]):
            return {
                "tipo": "cita_agregar",
                "capa_destino": "C5",
                "parametros": {},
                "solicitud_original": solicitud,
                "clasificacion": "aproximada",
            }
        if any(w in solicitud_lava for w in ["justificaci", "razón", "razon", "motivo"]):
            return {
                "tipo": "justificacion",
                "capa_destino": "C6",
                "parametros": {},
                "solicitud_original": solicitud,
                "clasificacion": "aproximada",
            }
        if any(w in solicitud_lava for w in ["secci", "estructura", "mapa"]):
            return {
                "tipo": "seccion_prioridad",
                "capa_destino": "C2",
                "parametros": {},
                "solicitud_original": solicitud,
                "clasificacion": "aproximada",
            }
    return {
        "tipo": "desconocido",
        "capa_destino": "C7",
        "parametros": {},
        "solicitud_original": solicitud,
        "clasificacion": "no_clasificada",
    }
