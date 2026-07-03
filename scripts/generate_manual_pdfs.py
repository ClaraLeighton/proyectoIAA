from __future__ import annotations

from pathlib import Path
import textwrap

import fitz


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs"

PAGE_W = 595
PAGE_H = 842
MARGIN_X = 54
TOP = 66
BOTTOM = 58
RED = (0.78, 0.02, 0.12)
DARK = (0.09, 0.13, 0.17)
MUTED = (0.36, 0.41, 0.47)
LIGHT = (0.95, 0.96, 0.97)


def clean(text: str) -> str:
    return (
        text.replace("—", "-")
        .replace("–", "-")
        .replace("≥", ">=")
        .replace("→", "->")
        .replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
    )


class PdfManual:
    def __init__(self, title: str, subtitle: str):
        self.doc = fitz.open()
        self.title = title
        self.subtitle = subtitle
        self.page = None
        self.y = TOP
        self.page_no = 0
        self.new_page(cover=True)

    def new_page(self, cover: bool = False):
        self.page = self.doc.new_page(width=PAGE_W, height=PAGE_H)
        self.page_no += 1
        self.y = TOP
        if cover:
            self._cover()
        else:
            self._header()

    def _cover(self):
        assert self.page is not None
        self.page.draw_rect(fitz.Rect(0, 0, PAGE_W, PAGE_H), color=(1, 1, 1), fill=(1, 1, 1))
        self.page.draw_rect(fitz.Rect(0, 0, 20, PAGE_H), color=RED, fill=RED)
        self.page.insert_text((MARGIN_X, 145), clean(self.title), fontsize=26, fontname="hebo", color=DARK)
        self.page.insert_text((MARGIN_X, 184), clean(self.subtitle), fontsize=13, fontname="helv", color=MUTED)
        self.page.draw_line((MARGIN_X, 222), (PAGE_W - MARGIN_X, 222), color=RED, width=2)
        self.page.insert_text((MARGIN_X, 260), "Evaluador de Perfil de Egreso", fontsize=18, fontname="hebo", color=DARK)
        self.page.insert_text(
            (MARGIN_X, 290),
            "Sistema de evaluacion de informes de practica con apoyo de IA",
            fontsize=12,
            fontname="helv",
            color=MUTED,
        )
        self.page.insert_text((MARGIN_X, 705), "IA Aplicada - Entregable Final 2026", fontsize=10, fontname="helv", color=MUTED)
        self.page.insert_text((MARGIN_X, 724), "Universidad de los Andes", fontsize=10, fontname="helv", color=MUTED)
        self.y = 770
        self.footer()
        self.new_page()

    def _header(self):
        assert self.page is not None
        self.page.insert_text((MARGIN_X, 32), clean(self.title), fontsize=9, fontname="hebo", color=MUTED)
        self.page.draw_line((MARGIN_X, 44), (PAGE_W - MARGIN_X, 44), color=(0.86, 0.88, 0.90), width=0.8)

    def footer(self):
        assert self.page is not None
        self.page.draw_line((MARGIN_X, PAGE_H - 40), (PAGE_W - MARGIN_X, PAGE_H - 40), color=(0.86, 0.88, 0.90), width=0.6)
        self.page.insert_text((MARGIN_X, PAGE_H - 22), f"Pagina {self.page_no}", fontsize=8, fontname="helv", color=MUTED)

    def ensure(self, height: float):
        if self.y + height > PAGE_H - BOTTOM:
            self.footer()
            self.new_page()

    def text_width(self, text: str, size: int, font: str) -> float:
        return fitz.get_text_length(clean(text), fontname=font, fontsize=size)

    def wrap(self, text: str, size: int, font: str, width: float) -> list[str]:
        text = clean(text)
        words = text.split()
        lines: list[str] = []
        line = ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if self.text_width(candidate, size, font) <= width or not line:
                line = candidate
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        return lines or [""]

    def h1(self, text: str):
        self.ensure(54)
        self.y += 10
        self.page.insert_text((MARGIN_X, self.y), clean(text), fontsize=18, fontname="hebo", color=DARK)
        self.y += 18
        self.page.draw_line((MARGIN_X, self.y), (PAGE_W - MARGIN_X, self.y), color=RED, width=1.2)
        self.y += 18

    def h2(self, text: str):
        self.ensure(38)
        self.y += 8
        self.page.insert_text((MARGIN_X, self.y), clean(text), fontsize=13, fontname="hebo", color=DARK)
        self.y += 18

    def p(self, text: str, size: int = 10, gap: int = 8):
        width = PAGE_W - 2 * MARGIN_X
        lines = self.wrap(text, size, "helv", width)
        self.ensure(len(lines) * (size + 4) + gap)
        for line in lines:
            self.page.insert_text((MARGIN_X, self.y), line, fontsize=size, fontname="helv", color=DARK)
            self.y += size + 4
        self.y += gap

    def bullet(self, text: str, level: int = 0):
        size = 10
        x = MARGIN_X + level * 18
        bullet_x = x
        text_x = x + 14
        width = PAGE_W - MARGIN_X - text_x
        lines = self.wrap(text, size, "helv", width)
        self.ensure(len(lines) * 14 + 4)
        self.page.insert_text((bullet_x, self.y), "-", fontsize=size, fontname="hebo", color=RED)
        for i, line in enumerate(lines):
            self.page.insert_text((text_x, self.y), line, fontsize=size, fontname="helv", color=DARK)
            self.y += 14
        self.y += 2

    def code(self, lines: list[str]):
        size = 9
        box_h = len(lines) * 13 + 18
        self.ensure(box_h + 8)
        rect = fitz.Rect(MARGIN_X, self.y, PAGE_W - MARGIN_X, self.y + box_h)
        self.page.draw_rect(rect, color=(0.86, 0.88, 0.90), fill=LIGHT, width=0.7)
        y = self.y + 16
        for line in lines:
            self.page.insert_text((MARGIN_X + 12, y), clean(line), fontsize=size, fontname="cour", color=DARK)
            y += 13
        self.y += box_h + 10

    def table(self, headers: list[str], rows: list[list[str]], widths: list[float]):
        size = 8
        line_h = 10
        min_row_h = 29
        x0 = MARGIN_X
        total_w = PAGE_W - 2 * MARGIN_X
        abs_widths = [w * total_w for w in widths]
        self.ensure(min_row_h + 12)
        x = x0
        y = self.y
        for i, h in enumerate(headers):
            rect = fitz.Rect(x, y, x + abs_widths[i], y + min_row_h)
            self.page.draw_rect(rect, color=(0.82, 0.84, 0.86), fill=(0.93, 0.94, 0.95), width=0.5)
            self.page.insert_text((x + 5, y + 17), clean(h), fontsize=size, fontname="hebo", color=DARK)
            x += abs_widths[i]
        y += min_row_h
        for row in rows:
            wrapped_cells = [self.wrap(cell, size, "helv", abs_widths[i] - 10) for i, cell in enumerate(row)]
            row_h = max(min_row_h, max(len(lines) for lines in wrapped_cells) * line_h + 14)
            if y + row_h > PAGE_H - BOTTOM:
                self.y = y
                self.footer()
                self.new_page()
                y = self.y
            x = x0
            for i, lines in enumerate(wrapped_cells):
                rect = fitz.Rect(x, y, x + abs_widths[i], y + row_h)
                self.page.draw_rect(rect, color=(0.88, 0.89, 0.90), fill=(1, 1, 1), width=0.4)
                line_y = y + 15
                for line in lines:
                    self.page.insert_text((x + 5, line_y), line, fontsize=size, fontname="helv", color=DARK)
                    line_y += line_h
                x += abs_widths[i]
            y += row_h
        self.y = y + 12

    def save(self, path: Path):
        self.footer()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(path)
        self.doc.close()


def build_user_manual():
    pdf = PdfManual(
        "Manual de Usuario",
        "Guia para operar la herramienta de evaluacion de perfil de egreso",
    )

    pdf.h1("1. Objetivo y publico objetivo")
    pdf.p(
        "El Evaluador de Perfil de Egreso es una aplicacion web que apoya la revision de informes de practica "
        "pre-profesional y profesional. El sistema analiza documentos PDF, identifica evidencia por competencia, "
        "asigna niveles de logro entre 0 y 3, muestra resultados agregados por cohorte y permite exportar reportes."
    )
    pdf.p(
        "Esta guia esta orientada a docentes, coordinadores de programa y ayudantes que necesitan revisar informes "
        "de estudiantes sin operar directamente el codigo fuente ni el pipeline de IA."
    )

    pdf.h1("2. Requisitos para usar la aplicacion")
    for item in [
        "Navegador web moderno y conexion a Internet para utilizar los proveedores de IA.",
        "Archivos PDF con texto digital seleccionable. Los PDF escaneados requieren OCR previo.",
        "Claves API configuradas para embeddings y evaluacion LLM: Gemini u OpenAI para embeddings, y OpenRouter para evaluacion.",
        "Matriz de competencias y rubrica configuradas. Si no se cargan archivos personalizados, se usan config/matriz.csv y config/rubrica.json.",
    ]:
        pdf.bullet(item)

    pdf.h1("3. Funcionalidades principales")
    pdf.table(
        ["Modulo", "Uso"],
        [
            ["Cohortes", "Crear, seleccionar, renombrar y gestionar grupos de informes."],
            ["Carga", "Subir PDF individuales o archivos ZIP con multiples informes."],
            ["Procesamiento", "Ejecutar pipeline C1-C8 con progreso global, por informe y por competencia."],
            ["Macro", "Ver resultados agregados de la cohorte y competencias debiles."],
            ["Micro", "Revisar resultados de un informe y detalle por competencia."],
            ["Comparacion", "Comparar dos cohortes mediante graficos y tablas."],
            ["Exportacion", "Descargar Excel de resultados y reporte tecnico de procesamiento."],
        ],
        [0.28, 0.72],
    )

    pdf.h1("4. Primer uso: configurar claves API")
    pdf.p("Antes de procesar informes, configure las claves en el archivo .env o ingreselas desde la barra lateral de la aplicacion.")
    pdf.code(["cp .env.example .env"])
    pdf.table(
        ["Variable", "Proveedor", "Uso"],
        [
            ["GEMINI_API_KEY", "Google Gemini", "Embeddings con gemini-embedding-2."],
            ["OPENAI_API_KEY", "OpenAI", "Embeddings con text-embedding-3-small."],
            ["OPENROUTER_API_KEY", "OpenRouter", "Evaluacion LLM de competencias."],
        ],
        [0.30, 0.25, 0.45],
    )
    pdf.p("Se recomienda validar con la institucion las politicas de privacidad de cada proveedor antes de procesar informes con datos sensibles.")

    pdf.h1("5. Crear una cohorte y subir informes")
    for item in [
        "Desde la pagina principal, seleccione Nueva Cohorte.",
        "Ingrese un nombre descriptivo, por ejemplo Practica Pre-Profesional 2026.",
        "Arrastre los PDF o un ZIP con varios PDF al area de carga.",
        "Seleccione el tipo de practica: Pre-Profesional o Profesional.",
        "Opcionalmente, cargue matriz de competencias CSV o rubrica JSON personalizada.",
        "Presione Crear Cohorte. El sistema iniciara el procesamiento automaticamente.",
    ]:
        pdf.bullet(item)

    pdf.h1("6. Monitorear el procesamiento")
    pdf.p(
        "La vista Procesando muestra una barra global, el avance de cada informe y el estado de cada competencia. "
        "El procesamiento continua aunque el usuario navegue a otras vistas. Al finalizar, la aplicacion muestra la vista macro."
    )
    for item in [
        "Si un informe queda con error, revise si el PDF tiene texto digital o si las claves API estan vigentes.",
        "Si una competencia falla, use la opcion de re-evaluar en la vista de detalle del informe.",
        "El tiempo estimado depende del largo del PDF y de la disponibilidad de los proveedores de IA.",
    ]:
        pdf.bullet(item)

    pdf.h1("7. Revisar resultados")
    pdf.h2("7.1 Vista Macro")
    pdf.p(
        "Resume la cohorte completa. Muestra porcentaje de logro, perfil de egreso cubierto, grado de evidencia promedio, "
        "competencias por reforzar, graficos de distribucion y una matriz agregada por competencia."
    )
    pdf.h2("7.2 Vista Micro")
    pdf.p(
        "Permite seleccionar un informe especifico y revisar competencias aprobadas, competencias por revisar, tarjetas por competencia, "
        "resumen por competencia, distribucion por niveles, justificaciones, secciones fuente y citas."
    )
    pdf.h2("7.3 Configuracion de cohorte")
    pdf.p(
        "Muestra el porcentaje del perfil de egreso aprobado y las competencias debiles de la cohorte. Desde esta vista se puede "
        "agregar informes, exportar resultados, descargar el reporte tecnico y eliminar informes."
    )

    pdf.h1("8. Exportar resultados")
    for item in [
        "Desde Configuracion o Resultados Macro, use Exportar Excel para descargar resultados consolidados.",
        "Use Descargar Reporte Tecnico para obtener datos de procesamiento separados de los resultados finales.",
        "Desde el detalle de un informe tambien se puede exportar el Excel individual.",
    ]:
        pdf.bullet(item)

    pdf.h1("9. Comparar cohortes")
    for item in [
        "Abra Comparar Cohortes desde el menu lateral.",
        "Seleccione dos cohortes en los menus desplegables.",
        "Revise diferencias por competencia, variacion de porcentaje de logro y clasificacion resumida.",
    ]:
        pdf.bullet(item)

    pdf.h1("10. Casos de uso practicos")
    pdf.h2("Caso 1: revision de una cohorte nueva")
    pdf.p("Un coordinador crea una cohorte, sube todos los informes de practica, espera el procesamiento y usa la vista macro para identificar competencias con escasa evidencia.")
    pdf.h2("Caso 2: revision de un informe particular")
    pdf.p("Un docente entra a Resultados Micro, abre un informe y revisa justificaciones y citas de cada competencia antes de retroalimentar al estudiante.")
    pdf.h2("Caso 3: mejora curricular")
    pdf.p("La direccion compara dos cohortes y observa si las competencias debiles se repiten, para priorizar acciones de mejora en asignaturas o practicas.")

    pdf.h1("11. Limitaciones y consideraciones")
    for item in [
        "La evaluacion es una ayuda para la revision docente; no reemplaza el criterio academico.",
        "Los resultados dependen de la calidad del texto extraido desde los PDF.",
        "La herramienta requiere Internet y claves API vigentes para procesar nuevos informes.",
        "Los datos quedan almacenados localmente en data/. Se recomienda respaldar esta carpeta.",
        "El sistema no implementa autenticacion de usuarios ni roles.",
        "Las politicas de uso de datos dependen de los proveedores externos configurados.",
    ]:
        pdf.bullet(item)

    pdf.save(OUT_DIR / "Manual_de_Usuario.pdf")


def build_install_manual():
    pdf = PdfManual(
        "Manual de Instalacion y Despliegue",
        "Guia tecnica para instalar, configurar, ejecutar y mantener el sistema",
    )

    pdf.h1("1. Requisitos de hardware y software")
    pdf.h2("Software")
    for item in [
        "Python 3.10 o superior.",
        "pip para instalar dependencias.",
        "Navegador moderno: Chrome, Firefox, Edge o Safari.",
        "Conexion a Internet para llamadas a APIs de IA.",
        "Git, si se instalara desde repositorio remoto.",
    ]:
        pdf.bullet(item)
    pdf.h2("Hardware recomendado")
    for item in [
        "4 GB de RAM o superior.",
        "1 GB de espacio libre en disco como minimo.",
        "Procesador dual-core de 2 GHz o superior.",
    ]:
        pdf.bullet(item)

    pdf.h1("2. Dependencias utilizadas")
    pdf.table(
        ["Paquete", "Proposito"],
        [
            ["streamlit", "Interfaz web."],
            ["pymupdf", "Extraccion de texto desde PDF."],
            ["google-genai", "Embeddings mediante Gemini."],
            ["openai", "Embeddings mediante OpenAI."],
            ["pandas", "Manejo de datos tabulares."],
            ["python-dotenv", "Carga de variables de entorno."],
            ["openpyxl", "Exportacion Excel."],
            ["numpy / scipy", "Calculo numerico y similitud coseno."],
        ],
        [0.32, 0.68],
    )

    pdf.h1("3. Procedimiento de instalacion")
    pdf.h2("3.1 Obtener el codigo")
    pdf.code(["git clone https://github.com/ClaraLeighton/proyectoIAA.git", "cd proyectoIAA"])
    pdf.h2("3.2 Crear entorno virtual")
    pdf.code(["python -m venv venv", "source venv/bin/activate    # macOS / Linux", "venv\\Scripts\\activate       # Windows"])
    pdf.h2("3.3 Instalar dependencias")
    pdf.code(["pip install -r requirements.txt"])

    pdf.h1("4. Configuracion de variables de entorno")
    pdf.p("Copie el archivo de ejemplo y edite sus valores con claves API vigentes.")
    pdf.code(["cp .env.example .env"])
    pdf.table(
        ["Variable", "Obligatoriedad", "Descripcion"],
        [
            ["GEMINI_API_KEY", "Recomendada", "Embeddings con Google Gemini."],
            ["OPENAI_API_KEY", "Alternativa", "Embeddings con OpenAI."],
            ["OPENROUTER_API_KEY", "Recomendada", "Evaluacion LLM en C6."],
        ],
        [0.30, 0.25, 0.45],
    )
    pdf.p("Debe existir al menos un proveedor de embeddings operativo. Para evaluacion LLM se recomienda configurar OpenRouter.")

    pdf.h1("5. Ejecucion del sistema")
    pdf.code(["streamlit run app.py"])
    pdf.p("Por defecto, Streamlit abre la aplicacion en http://localhost:8501. Si el puerto esta ocupado, use:")
    pdf.code(["streamlit run app.py --server.port 8502"])

    pdf.h1("6. Estructura general del proyecto")
    pdf.code(
        [
            "proyectoIAA/",
            "  app.py                  # Entrada Streamlit",
            "  requirements.txt        # Dependencias",
            "  MANUAL.md               # Manual base del proyecto",
            "  pipeline/               # Pipeline C1-C8 y logica de IA",
            "  ui/                     # Paginas y componentes Streamlit",
            "  config/                 # matriz.csv y rubrica.json",
            "  assets/                 # CSS, imagenes y recursos estaticos",
            "  data/                   # Datos generados: index, cohorts y reports",
            "  tests/                  # Pruebas unitarias",
            "  docs/                   # Manuales PDF generados",
        ]
    )
    pdf.h2("Pipeline C1-C8")
    pdf.p(
        "El flujo ejecuta ingesta, parseo, chunking, embeddings, similitud coseno, recuperacion de evidencia, "
        "evaluacion LLM, agregacion y resumen macro. La intervencion humana se apoya en router.py y hitl.py."
    )

    pdf.h1("7. Consideraciones de mantenimiento")
    for item in [
        "Respaldar periodicamente data/, porque contiene informes procesados, cohortes y resultados.",
        "Mantener .env fuera del repositorio publico y rotar claves si se comparten accidentalmente.",
        "Actualizar dependencias con pip install -r requirements.txt despues de cambios relevantes.",
        "Editar config/matriz.csv para actualizar competencias y config/rubrica.json para ajustar secciones evaluadas.",
        "Revisar logs de Streamlit en consola ante errores de procesamiento.",
        "Para reiniciar el sistema desde cero, respaldar data/ y luego limpiar data/reports, data/index.json y data/cohorts.json.",
    ]:
        pdf.bullet(item)

    pdf.h1("8. Problemas frecuentes")
    pdf.table(
        ["Problema", "Causa probable", "Solucion"],
        [
            ["Error API 401", "Clave invalida o vencida", "Actualizar .env o ingresar clave en la barra lateral."],
            ["PDF sin texto", "Documento escaneado", "Aplicar OCR o subir PDF con texto seleccionable."],
            ["No avanza", "Llamadas API lentas o limite de concurrencia", "Esperar, reducir lote o revisar proveedor."],
            ["Excel no descarga", "Archivo bloqueado o error temporal", "Cerrar Excel y reintentar exportacion."],
            ["ModuleNotFoundError", "Dependencias faltantes", "Ejecutar pip install -r requirements.txt."],
            ["Puerto ocupado", "Otro proceso usa 8501", "Ejecutar con --server.port 8502."],
        ],
        [0.25, 0.35, 0.40],
    )

    pdf.h1("9. Validacion posterior a instalacion")
    for item in [
        "Abrir la aplicacion en el navegador.",
        "Crear una cohorte de prueba con un PDF de texto digital.",
        "Confirmar que el procesamiento termina y genera vista macro.",
        "Abrir la vista micro de un informe y revisar detalle por competencia.",
        "Exportar Excel de resultados y Descargar Reporte Tecnico.",
    ]:
        pdf.bullet(item)

    pdf.save(OUT_DIR / "Manual_de_Instalacion.pdf")


if __name__ == "__main__":
    build_user_manual()
    build_install_manual()
    print(f"PDFs generados en {OUT_DIR}")
