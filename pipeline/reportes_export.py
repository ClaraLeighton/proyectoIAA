import io
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from pipeline.persistence import load_report


RESULTADOS_SHEET = "Resultados de Evaluación"
PROCESAMIENTO_SHEET = "Reporte de Procesamiento"
JPC_APROBACION_MIN = 0.60
TIEMPO_MANUAL_ESTIMADO_MIN = 180


def build_export_index(report_ids: list[str]) -> list[dict]:
    index = []
    for report_id in report_ids:
        report = load_report(report_id)
        if report:
            index.append(report.to_index_entry())
    return index


def _completed_reports(index: list[dict]):
    reports = []
    for entry in sorted(index, key=lambda e: e.get("timestamp", ""), reverse=True):
        report = load_report(entry["report_id"])
        if report and report.estado == "completado":
            reports.append(report)
    return reports


def _trace_by_competencia(report) -> dict[str, dict]:
    trazabilidad = report.reporte_procesamiento.get("trazabilidad_competencias", [])
    return {t.get("competencia_id", ""): t for t in trazabilidad}


def _display_estado_revision(resultado: dict, traza: dict) -> str:
    estado = str(resultado.get("estado_revision", "")).lower()
    nivel = resultado.get("nivel", traza.get("nivel_asignado", 0))
    jpc = traza.get("JPC", 0) or 0
    jpc_aplicable = traza.get("JPC_aplicable", True)

    if "no_aprob" in estado or nivel == 0 or not jpc_aplicable:
        return "No Aprobada"
    if "requiere" in estado or jpc < JPC_APROBACION_MIN:
        return "Requiere Revision"
    return "Respaldo Suficiente"


def _timestamp_validacion(resultado: dict, report) -> str:
    for key in ("timestamp_validacion", "validated_at", "updated_at"):
        if resultado.get(key):
            return str(resultado[key])[:19]
    return str(report.timestamp or datetime.now().isoformat())[:19]


def _resultados_rows(reports) -> tuple[list[str], list[list]]:
    include_report_cols = len(reports) > 1
    headers = [
        "ID",
        "Competencia_Nombre",
        "Nivel",
        "Justificación",
        "Cita_1",
        "Sección_Cita_1",
        "Cita_2",
        "Sección_Cita_2",
        "Cita_3",
        "Sección_Cita_3",
        "JPC_Porcentaje",
        "Estado_Revision",
        "Timestamp_Validación",
    ]
    if include_report_cols:
        headers = ["Reporte", "Report_ID"] + headers

    rows = []
    for report in reports:
        trazas = _trace_by_competencia(report)
        for resultado in report.vista_preliminar:
            cid = resultado.get("competencia_id", "")
            traza = trazas.get(cid, {})
            citas = list(resultado.get("citas", []))[:3]
            secciones = list(resultado.get("secciones_fuente", []))[:3]
            while len(citas) < 3:
                citas.append("")
            while len(secciones) < 3:
                secciones.append("")

            jpc = traza.get("JPC", 0) or 0
            row = [
                cid,
                resultado.get("competencia_nombre", ""),
                resultado.get("nivel", traza.get("nivel_asignado", 0)),
                resultado.get("justificacion", ""),
                citas[0],
                secciones[0],
                citas[1],
                secciones[1],
                citas[2],
                secciones[2],
                jpc,
                _display_estado_revision(resultado, traza),
                _timestamp_validacion(resultado, report),
            ]
            if include_report_cols:
                row = [report.pdf_name, report.report_id] + row
            rows.append(row)

    return headers, rows


def _num(value) -> float:
    return value if isinstance(value, (int, float)) else 0


def _format_minutes(value) -> str:
    if value is None:
        return ""
    return f"{value:g} minutos" if isinstance(value, (int, float)) else str(value)


def _processing_blocks(report) -> list[list]:
    state = report.pipeline_state
    c2 = state.get("c2", {})
    rp = report.reporte_procesamiento
    trazabilidad = rp.get("trazabilidad_competencias", [])
    tiempos = rp.get("tiempos", {})

    detectadas = c2.get("secciones_detectadas", [])
    ausentes = c2.get("secciones_ausentes", [])
    total_encontradas = c2.get("total_secciones", len(detectadas))
    total_esperadas = total_encontradas + len(ausentes)

    total_competencias = len(trazabilidad)
    aprobadas = sum(1 for t in trazabilidad if _num(t.get("JPC")) >= JPC_APROBACION_MIN and t.get("JPC_aplicable", True))
    no_aprobadas = total_competencias - aprobadas
    tasa_aprobacion = aprobadas / total_competencias if total_competencias else 0

    jpc_values = [_num(t.get("JPC")) for t in trazabilidad if t.get("JPC") is not None]
    jpc_promedio = sum(jpc_values) / len(jpc_values) if jpc_values else 0
    max_traza = max(trazabilidad, key=lambda t: _num(t.get("JPC")), default={})
    min_traza = min(trazabilidad, key=lambda t: _num(t.get("JPC")), default={})
    confianza_values = [_num(t.get("F_confianza")) for t in trazabilidad if t.get("F_confianza") is not None]
    similitud_values = [_num(t.get("R_similitud_promedio")) for t in trazabilidad if t.get("R_similitud_promedio") is not None]
    confianza_promedio = sum(confianza_values) / len(confianza_values) if confianza_values else 0
    similitud_promedio = sum(similitud_values) / len(similitud_values) if similitud_values else 0

    t_auto = tiempos.get("T_procesamiento_automatico_min")
    t_revision = tiempos.get("T_revision_humana_min")
    t_ajustes = tiempos.get("T_ajustes_min")
    t_total = tiempos.get("T_IA_total_min")
    if t_total is None:
        t_total = sum(_num(t) for t in [t_auto, t_revision, t_ajustes])
    reduccion = (TIEMPO_MANUAL_ESTIMADO_MIN - t_total) / TIEMPO_MANUAL_ESTIMADO_MIN if t_total else 0

    rows = [
        ["INFORME", report.pdf_name],
        ["Report ID", report.report_id],
        ["Tipo", report.tipo_documento],
        ["Fecha", str(report.timestamp)[:19]],
        [],
        ["ANÁLISIS DE SECCIONES", ""],
        ["Secciones Detectadas", ", ".join(detectadas) if detectadas else ""],
        ["Secciones Ausentes", ", ".join(ausentes) if ausentes else "(ninguna)"],
        ["Total Secciones Esperadas", total_esperadas],
        ["Total Secciones Encontradas", total_encontradas],
        [],
        ["ESTADÍSTICAS DE COBERTURA", ""],
        ["Total Competencias Evaluadas", total_competencias],
        [f"Competencias Aprobadas (JPC >= {JPC_APROBACION_MIN:.2f})", aprobadas],
        [f"Competencias No Aprobadas (JPC < {JPC_APROBACION_MIN:.2f})", no_aprobadas],
        ["Tasa de Aprobación", tasa_aprobacion],
        [],
        ["MÉTRICAS AGREGADAS", ""],
        ["JPC Promedio", round(jpc_promedio, 3)],
        ["JPC Máximo", f"{_num(max_traza.get('JPC')):.3f} ({max_traza.get('competencia_id', '')})" if max_traza else ""],
        ["JPC Mínimo", f"{_num(min_traza.get('JPC')):.3f} ({min_traza.get('competencia_id', '')})" if min_traza else ""],
        ["Confianza Promedio (F)", round(confianza_promedio, 3)],
        ["Similitud Promedio (R)", round(similitud_promedio, 3)],
        [],
        ["TIEMPOS (KPI 2)", ""],
        ["Tiempo Procesamiento Automático", _format_minutes(t_auto)],
        ["Tiempo Revisión Humana (HITL)", _format_minutes(t_revision)],
        ["Tiempo Ajustes", _format_minutes(t_ajustes)],
        ["Tiempo Total con IA", _format_minutes(t_total)],
        ["Tiempo Manual Estimado (Línea Base)", _format_minutes(TIEMPO_MANUAL_ESTIMADO_MIN)],
        ["Reducción de Tiempo (RTR)", reduccion],
        [],
        ["TRAZABILIDAD POR COMPETENCIA", ""],
        [
            "Competencia",
            "Embedding_Generado",
            "Similitud_Calculada",
            "Recuperación_Ejecutada",
            "Chunks_Recuperados",
            "Dictamen_Generado",
            "Estado_Final",
            "JPC_Aplicable",
        ],
    ]
    for traza in trazabilidad:
        rows.append([
            traza.get("competencia_id", ""),
            "✓" if traza.get("embedding_generado") else "",
            "✓" if traza.get("similitud_calculada") else "",
            "✓" if traza.get("recuperacion_ejecutada") else "",
            traza.get("chunks_recuperados", 0),
            "✓" if traza.get("dictamen_generado") else "",
            traza.get("estado_final", ""),
            "✓" if traza.get("JPC_aplicable") else "",
        ])

    ajustes = rp.get("historial_ajustes", [])
    if ajustes:
        rows.extend([[], ["HISTORIAL DE AJUSTES", ""], ["Ajuste_ID", "Competencia", "Solicitud", "Capas_Reprocesadas", "Duración_Min", "Resultado"]])
        for ajuste in ajustes:
            rows.append([
                ajuste.get("ajuste_id", ""),
                ajuste.get("competencia_id", ""),
                ajuste.get("solicitud_usuario", ""),
                ", ".join(ajuste.get("capas_reprocesadas", [])),
                ajuste.get("duracion_min", ""),
                ajuste.get("resultado", ""),
            ])
    return rows


def _write_resultados_sheet(ws, headers: list[str], rows: list[list]):
    ws.append(headers)
    for row in rows:
        ws.append(row)

    header_fill = PatternFill("solid", fgColor="E7E5E4")
    green = PatternFill("solid", fgColor="C6E0B4")
    yellow = PatternFill("solid", fgColor="FFE699")
    red = PatternFill("solid", fgColor="F4CCCC")

    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    estado_col = headers.index("Estado_Revision") + 1 if "Estado_Revision" in headers else None
    jpc_col = headers.index("JPC_Porcentaje") + 1 if "JPC_Porcentaje" in headers else None
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        if estado_col:
            estado = row[estado_col - 1].value
            fill = green if estado == "Respaldo Suficiente" else yellow if estado == "Requiere Revision" else red
            row[estado_col - 1].fill = fill
        if jpc_col:
            row[jpc_col - 1].number_format = "0.00%"
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    ws.freeze_panes = "A2"
    widths = {
        "ID": 10,
        "Competencia_Nombre": 36,
        "Nivel": 10,
        "Justificación": 48,
        "Cita_1": 48,
        "Sección_Cita_1": 16,
        "Cita_2": 48,
        "Sección_Cita_2": 16,
        "Cita_3": 48,
        "Sección_Cita_3": 16,
        "JPC_Porcentaje": 16,
        "Estado_Revision": 22,
        "Timestamp_Validación": 22,
        "Reporte": 30,
        "Report_ID": 38,
    }
    for idx, header in enumerate(headers, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = widths.get(header, 18)


def _write_processing_sheet(ws, reports):
    row_idx = 1
    section_fill = PatternFill("solid", fgColor="E7E5E4")
    for report in reports:
        for row in _processing_blocks(report):
            if row:
                for col_idx, value in enumerate(row, start=1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=value)
                    cell.alignment = Alignment(vertical="top", wrap_text=True)
                    if col_idx == 1 and isinstance(value, str) and value.isupper():
                        cell.font = Font(bold=True)
                        cell.fill = section_fill
                    elif row_idx == 1 or value in ("Competencia", "Ajuste_ID"):
                        cell.font = Font(bold=True)
            row_idx += 1
        row_idx += 2

    for col_idx in range(1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 28 if col_idx == 1 else 24

    for row in ws.iter_rows():
        if row and row[0].value in ("Tasa de Aprobación", "Reducción de Tiempo (RTR)"):
            row[1].number_format = "0.00%"


def exportar_excel_multi_hoja(index: list[dict]) -> io.BytesIO:
    output = io.BytesIO()
    wb = Workbook()
    ws_resultados = wb.active
    ws_resultados.title = RESULTADOS_SHEET
    ws_procesamiento = wb.create_sheet(PROCESAMIENTO_SHEET)

    reports = _completed_reports(index)
    if reports:
        headers, rows = _resultados_rows(reports)
        _write_resultados_sheet(ws_resultados, headers, rows)
        _write_processing_sheet(ws_procesamiento, reports)
    else:
        _write_resultados_sheet(ws_resultados, ["Mensaje"], [["No hay informes completados disponibles para exportar."]])
        ws_procesamiento.append(["Mensaje", "No hay informes completados disponibles para exportar."])

    wb.save(output)
    output.seek(0)
    return output


def exportar_reporte_individual(report_id: str) -> io.BytesIO:
    report = load_report(report_id)
    if not report:
        return io.BytesIO()
    index = [report.to_index_entry()]
    return exportar_excel_multi_hoja(index)
