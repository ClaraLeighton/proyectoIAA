from dataclasses import dataclass, field
from typing import Any
import uuid
from datetime import datetime


@dataclass
class BatchConfig:
    max_workers: int = 10
    max_reports_per_batch: int = 10
    semaphore_limit: int = 5


@dataclass
class ReportResult:
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pdf_name: str = ""
    tipo_documento: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    pipeline_state: dict[str, Any] = field(default_factory=dict)
    estado: str = "pendiente"
    error: str | None = None

    @property
    def resultados_competencias(self) -> list[dict]:
        return self.pipeline_state.get("resultados_competencias", [])

    @property
    def c7(self) -> dict:
        return self.pipeline_state.get("c7", {})

    @property
    def reporte_procesamiento(self) -> dict:
        return self.c7.get("reporte_procesamiento", {})

    @property
    def vista_preliminar(self) -> list[dict]:
        return self.c7.get("vista_preliminar", {}).get("resultados_competencias", [])

    def to_index_entry(self) -> dict:
        preview = self.vista_preliminar
        trazabilidad = self.reporte_procesamiento.get("trazabilidad_competencias", [])
        jpc_values = [t.get("JPC", 0) for t in trazabilidad if t.get("JPC_aplicable")]
        nivel_dist = {}
        for r in preview:
            lvl = r.get("nivel", 0)
            nivel_dist[str(lvl)] = nivel_dist.get(str(lvl), 0) + 1
        return {
            "report_id": self.report_id,
            "pdf_name": self.pdf_name,
            "tipo_documento": self.tipo_documento,
            "timestamp": self.timestamp,
            "total_competencias": len(preview),
            "avg_jpc": round(sum(jpc_values) / len(jpc_values), 4) if jpc_values else 0.0,
            "avg_confianza": round(
                sum(r.get("confianza", 0) for r in preview) / len(preview), 4
            ) if preview else 0.0,
            "nivel_promedio": round(
                sum(r.get("nivel", 0) for r in preview) / len(preview), 1
            ) if preview else 0.0,
            "nivel_distribucion": nivel_dist,
            "estado": self.estado,
            "error": self.error,
        }

    def get_procesamiento_summary(self) -> dict:
        rp = self.reporte_procesamiento
        tiempos = rp.get("tiempos", {})
        trazabilidad = rp.get("trazabilidad_competencias", [])
        niveles = [t.get("nivel_asignado", 0) for t in trazabilidad]
        return {
            "total": len(trazabilidad),
            "tiempo_total_min": tiempos.get("T_procesamiento_automatico_min"),
            "historial_ajustes": rp.get("historial_ajustes", []),
            "distribucion_niveles": {str(n): niveles.count(n) for n in sorted(set(niveles))},
        }
