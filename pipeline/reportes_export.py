import io
import pandas as pd
from typing import Any
from pipeline.persistence import load_report


def _build_resumen_competencias(index: list[dict]) -> pd.DataFrame:
    rows = []
    for entry in index:
        report = load_report(entry["report_id"])
        if not report or report.estado != "completado":
            continue
        trazabilidad = report.reporte_procesamiento.get("trazabilidad_competencias", [])
        for t in trazabilidad:
            rows.append({
                "Reporte": report.pdf_name,
                "Report ID": report.report_id,
                "Competencia": t.get("competencia_id", ""),
                "Nivel Asignado": t.get("nivel_asignado", 0),
                "Estado Final": t.get("estado_final", "pendiente"),
                "JPC": t.get("JPC", 0),
                "Cobertura": t.get("C_cobertura_citas", 0),
                "Pertinencia": t.get("S_pertinencia_seccion", 0),
                "Similitud": t.get("R_similitud_promedio", 0),
                "Confianza": t.get("F_confianza", 0),
                "JPC Aplicable": t.get("JPC_aplicable", False),
            })
    return pd.DataFrame(rows)


def _build_detalle_informes(index: list[dict]) -> pd.DataFrame:
    rows = []
    for entry in sorted(index, key=lambda e: e.get("timestamp", ""), reverse=True):
        report = load_report(entry["report_id"])
        if not report or report.estado != "completado":
            rows.append({
                "Reporte": entry.get("pdf_name", entry["report_id"][:8]),
                "Report ID": entry["report_id"],
                "Estado": entry.get("estado", "error"),
                "Error": entry.get("error", ""),
            })
            continue
        preview = report.vista_preliminar
        comp_niveles = [f"{r['competencia_id']}:{r['nivel']}" for r in preview]
        summary = report.get_procesamiento_summary()
        rows.append({
            "Reporte": report.pdf_name,
            "Report ID": report.report_id,
            "Tipo": report.tipo_documento,
            "Fecha": report.timestamp[:19],
            "Total Competencias": summary["total"],
            "Distribución Niveles": str(summary["distribucion_niveles"]),
            "Tiempo Total (min)": summary["tiempo_total_min"],
            "Competencias": "; ".join(comp_niveles),
            "Estado": "completado",
        })
    return pd.DataFrame(rows)


def _build_metadatos(index: list[dict]) -> pd.DataFrame:
    rows = []
    for entry in index:
        report = load_report(entry["report_id"])
        if not report:
            continue
        rp = report.reporte_procesamiento
        tiempos = rp.get("tiempos", {})
        rows.append({
            "Reporte": report.pdf_name,
            "Report ID": report.report_id,
            "Tipo": report.tipo_documento,
            "Fecha": report.timestamp[:19],
            "Estado": entry.get("estado", ""),
            "T_procesamiento_auto_min": tiempos.get("T_procesamiento_automatico_min"),
            "T_revision_humana_min": tiempos.get("T_revision_humana_min"),
            "T_ajustes_min": tiempos.get("T_ajustes_min"),
            "T_IA_total_min": tiempos.get("T_IA_total_min"),
            "Total Ajustes": len(rp.get("historial_ajustes", [])),
        })
    return pd.DataFrame(rows)


def exportar_excel_multi_hoja(index: list[dict]) -> io.BytesIO:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_resumen = _build_resumen_competencias(index)
        if not df_resumen.empty:
            df_resumen.to_excel(writer, sheet_name="Resumen por Competencia", index=False)

        df_detalle = _build_detalle_informes(index)
        if not df_detalle.empty:
            df_detalle.to_excel(writer, sheet_name="Detalle por Informe", index=False)

        df_meta = _build_metadatos(index)
        if not df_meta.empty:
            df_meta.to_excel(writer, sheet_name="Metadatos", index=False)

    output.seek(0)
    return output


def exportar_reporte_individual(report_id: str) -> io.BytesIO:
    report = load_report(report_id)
    if not report:
        return io.BytesIO()
    index = [report.to_index_entry()]
    return exportar_excel_multi_hoja(index)
