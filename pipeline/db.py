import sqlite3
import json
import os
import threading
from typing import Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "evaluaciones.db")
_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


def init_db():
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS reportes (
            id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            tipo TEXT NOT NULL,
            estado TEXT DEFAULT 'pendiente',
            error TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS resultados_competencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporte_id TEXT NOT NULL,
            competencia_id TEXT NOT NULL,
            competencia_nombre TEXT DEFAULT '',
            nivel INTEGER DEFAULT 0,
            nivel_label TEXT DEFAULT '',
            justificacion TEXT DEFAULT '',
            citas TEXT DEFAULT '[]',
            p TEXT DEFAULT '[]',
            confianza REAL DEFAULT 0.0,
            jpc REAL DEFAULT 0.0,
            c_cobertura_citas REAL DEFAULT 0.0,
            s_pertinencia_seccion REAL DEFAULT 0.0,
            r_similitud_promedio REAL DEFAULT 0.0,
            f_confianza REAL DEFAULT 0.0,
            estado_revision TEXT DEFAULT 'sin_evidencia',
            estado_final TEXT DEFAULT 'pendiente',
            secciones_fuente TEXT DEFAULT '[]',
            raw_response TEXT DEFAULT '',
            procesado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (reporte_id) REFERENCES reportes(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS reporte_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporte_id TEXT NOT NULL,
            mensaje TEXT NOT NULL,
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (reporte_id) REFERENCES reportes(id) ON DELETE CASCADE
        );
    """)
    conn.commit()


def guardar_reporte(reporte_id: str, nombre: str, tipo: str, estado: str = "pendiente"):
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO reportes (id, nombre, tipo, estado) VALUES (?, ?, ?, ?)",
        (reporte_id, nombre, tipo, estado),
    )
    conn.commit()


def actualizar_estado_reporte(reporte_id: str, estado: str, error: str | None = None):
    conn = _get_conn()
    if error:
        conn.execute("UPDATE reportes SET estado = ?, error = ? WHERE id = ?", (estado, error, reporte_id))
    else:
        conn.execute("UPDATE reportes SET estado = ? WHERE id = ?", (estado, reporte_id))
    conn.commit()


def guardar_resultados_competencia(reporte_id: str, resultados: list[dict]):
    conn = _get_conn()
    for r in resultados:
        conn.execute(
            """INSERT OR REPLACE INTO resultados_competencias
            (reporte_id, competencia_id, competencia_nombre, nivel, nivel_label,
             justificacion, citas, p, confianza, jpc,
             c_cobertura_citas, s_pertinencia_seccion, r_similitud_promedio, f_confianza,
             estado_revision, estado_final, secciones_fuente, raw_response)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                reporte_id,
                r["competencia_id"],
                r.get("competencia_nombre", ""),
                r.get("nivel", 0),
                r.get("nivel_label", ""),
                r.get("justificacion", ""),
                json.dumps(r.get("citas", [])),
                json.dumps(r.get("p", [])),
                r.get("confianza", 0.0),
                r.get("jpc", 0.0),
                r.get("c_cobertura_citas", 0.0),
                r.get("s_pertinencia_seccion", 0.0),
                r.get("r_similitud_promedio", 0.0),
                r.get("f_confianza", 0.0),
                r.get("estado_revision", "sin_evidencia"),
                r.get("estado_final", "pendiente"),
                json.dumps(r.get("secciones_fuente", [])),
                r.get("raw_response", ""),
            ),
        )
    conn.commit()


def obtener_resultados_por_reporte(reporte_id: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM resultados_competencias WHERE reporte_id = ? ORDER BY competencia_id",
        (reporte_id,),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    for field in ("citas", "p", "secciones_fuente"):
        if isinstance(d.get(field), str):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


def obtener_todos_los_reportes() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM reportes ORDER BY fecha_creacion DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def obtener_reportes_por_tipo(tipo: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM reportes WHERE tipo = ? AND estado = 'completado' ORDER BY fecha_creacion",
        (tipo,),
    ).fetchall()
    return [dict(r) for r in rows]


def obtener_todos_los_resultados(tipo: str | None = None) -> list[dict]:
    conn = _get_conn()
    if tipo:
        rows = conn.execute(
            """SELECT rc.* FROM resultados_competencias rc
            JOIN reportes r ON r.id = rc.reporte_id
            WHERE r.tipo = ? AND r.estado = 'completado'
            ORDER BY rc.reporte_id, rc.competencia_id""",
            (tipo,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT rc.* FROM resultados_competencias rc
            JOIN reportes r ON r.id = rc.reporte_id
            WHERE r.estado = 'completado'
            ORDER BY rc.reporte_id, rc.competencia_id"""
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def actualizar_resultado_individual(
    reporte_id: str, competencia_id: str, campo: str, valor: Any
):
    campos_permitidos = {
        "nivel", "justificacion", "estado_final", "citas", "p",
        "confianza", "jpc", "nivel_label", "estado_revision",
    }
    if campo not in campos_permitidos:
        return
    conn = _get_conn()
    if campo in ("citas", "p", "secciones_fuente") and not isinstance(valor, str):
        valor = json.dumps(valor)
    conn.execute(
        f"UPDATE resultados_competencias SET {campo} = ? WHERE reporte_id = ? AND competencia_id = ?",
        (valor, reporte_id, competencia_id),
    )
    conn.commit()


def eliminar_reporte(reporte_id: str):
    conn = _get_conn()
    conn.execute("DELETE FROM reportes WHERE id = ?", (reporte_id,))
    conn.commit()


def contar_reportes_por_estado() -> dict[str, int]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT estado, COUNT(*) as cnt FROM reportes GROUP BY estado"
    ).fetchall()
    return {r["estado"]: r["cnt"] for r in rows}


def log_reporte(reporte_id: str, mensaje: str):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO reporte_log (reporte_id, mensaje) VALUES (?, ?)",
        (reporte_id, mensaje),
    )
    conn.commit()
