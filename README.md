# Evaluador de Perfil de Egreso

Sistema automatizado de evaluación de informes de práctica profesional/pre-profesional mediante un pipeline de IA en 8 capas (C1–C8)

---

## Navegación

- [1. Manual de Usuario](MANUAL.md)
  - [1.1 Objetivo y público objetivo](#11-objetivo-y-público-objetivo)
  - [1.2 Funcionalidades](#12-funcionalidades)
  - [1.3 Instrucciones paso a paso](#13-instrucciones-paso-a-paso)
  - [1.4 Limitaciones](#14-limitaciones)
- [2. Manual de Instalación y Despliegue](#2-manual-de-instalación-y-despliegue)
  - [2.1 Requisitos de hardware y software](#21-requisitos-de-hardware-y-software)
  - [2.2 Dependencias](#22-dependencias)
  - [2.3 Instalación](#23-instalación)
  - [2.4 Configuración de variables de entorno](#24-configuración-de-variables-de-entorno)
  - [2.5 Ejecución](#25-ejecución)
  - [2.6 Estructura del proyecto](#26-estructura-del-proyecto)
  - [2.7 Mantenimiento](#27-mantenimiento)
  - [2.8 Problemas frecuentes](#28-problemas-frecuentes)
- [3. Código Fuente](#3-código-fuente)
  - [3.1 Estructura de directorios](#31-estructura-de-directorios)
  - [3.2 Pipeline C1–C8](#32-pipeline-c1c8)
  - [3.3 Interfaz de usuario (UI)](#33-interfaz-de-usuario-ui)

---

## 1. Manual de Usuario

El manual de usuario completo y detallado se encuentra en [`MANUAL.md`](MANUAL.md).

### 1.1 Objetivo y público objetivo

Herramienta web que automatiza la evaluación de informes de práctica estudiantil. Asiste a docentes en la revisión mediante un pipeline de IA que analiza cada documento, lo contrasta contra una matriz de competencias y genera una evaluación por competencia con nivel (0–3), justificación textual y citas extraídas del informe.

**Público objetivo:** docentes, coordinadores de programa y ayudantes de la Universidad de los Andes (Chile). No se requieren conocimientos técnicos de programación ni IA.

### 1.2 Funcionalidades

| Función | Descripción                                                                            |
|---------|----------------------------------------------------------------------------------------|
| **Gestión de cohortes** | Crear, renombrar, eliminar y listar cohortes de informes                               |
| **Carga de informes** | Subida individual (PDF), por lote (ZIP)                                                |
| **Pipeline C1–C8** | Ingesta, parseo, chunking, embeddings, recuperación, evaluación LLM, agregación, macro |
| **Revisión HITL** | Ajuste por lenguaje natural, aceptar/rechazar por competencia                          |
| **Resultados** | Vista macro (cohorte), micro (por informe), detalle por competencia                    |
| **Comparación** | Gráficos comparativos entre dos cohortes                                               |
| **Exportación** | Excels: resumen macro, resultados, reporte de procesamiento                            |
| **KPIs** | Cobertura, tiempos de revisión, índice JPC (citas, sección, similitud, confianza)      |

### 1.3 Instrucciones paso a paso

Las instrucciones detalladas para cada operación —desde la configuración inicial hasta la exportación de resultados— están disponibles en [`MANUAL.md`](MANUAL.md), secciones 5 y 6, incluyendo ejemplos prácticos de uso.

### 1.4 Limitaciones

- Dependencia de APIs externas (requiere claves vigentes e Internet)
- Los PDF deben ser texto digital seleccionable (no escaneados)
- 1–5 min por informe de procesamiento LLM
- Máximo 5 informes en paralelo, 10 por lote
- Sin autenticación de usuarios ni roles
- Almacenamiento en JSON local (no escala a cientos de miles)
- Interfaz y prompts en español
- El parser (C2) funciona mejor con estructura de informe estándar

---

## 2. Manual de Instalación y Despliegue

### 2.1 Requisitos de hardware y software

**Software:**
- Python 3.10 o superior
- pip (gestor de paquetes de Python)
- Navegador web moderno (Chrome 90+, Firefox 88+, Edge 90+, Safari 14+)
- Conexión a Internet (para APIs de IA)

**Hardware (recomendado):**
- 4 GB de RAM
- 1 GB de espacio en disco
- Procesador dual-core 2 GHz

### 2.2 Dependencias

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| `streamlit` | ≥1.32.0 | Framework web de interfaz de usuario |
| `pymupdf` | ≥1.23.0 | Extracción de texto desde PDF |
| `google-genai` | ≥2.0.0 | Embeddings vía Google Gemini |
| `openai` | ≥1.50.0 | Embeddings vía OpenAI |
| `pandas` | ≥2.0.0 | Manejo de datos tabulares |
| `python-dotenv` | ≥1.0.0 | Carga de variables de entorno |
| `openpyxl` | ≥3.1.0 | Exportación a Excel |
| `numpy` | ≥1.26.0 | Cómputo numérico |
| `scipy` | ≥1.12.0 | Distancias y similitud coseno |

Todas las dependencias se instalan automáticamente vía `requirements.txt`.

### 2.3 Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/ClaraLeighton/proyectoIAA.git
cd proyectoIAA

# 2. Crear y activar entorno virtual (opcional pero recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Instalar dependencias
pip install -r requirements.txt
```

### 2.4 Configuración de variables de entorno

Copia el archivo de ejemplo y edítalo con tus claves:

```bash
cp .env.example .env
```

| Variable | Proveedor | ¿Obligatoria? | Uso |
|----------|-----------|---------------|-----|
| `GEMINI_API_KEY` | Google Gemini | Recomendada | Embeddings (modelo `gemini-embedding-2`) |
| `OPENAI_API_KEY` | OpenAI | Alternativa | Embeddings (modelo `text-embedding-3-small`) |
| `OPENROUTER_API_KEY` | OpenRouter | Recomendada | Evaluación LLM (C6) |

Se necesita al menos un proveedor de embeddings (Gemini u OpenAI) y OpenRouter para la evaluación. Si no se configuran en `.env`, se puede ingresar desde la barra lateral de la aplicación.

**Obtención de claves:**
- [Google AI Studio](https://aistudio.google.com/apikey) — Gemini
- [OpenAI API Keys](https://platform.openai.com/api-keys) — OpenAI
- [OpenRouter Keys](https://openrouter.ai/keys) — OpenRouter

### 2.5 Ejecución

```bash
streamlit run app.py
```

La aplicación se abrirá en `http://localhost:8501`.

**Flujo de trabajo básico:**
1. Crear una cohorte y subir uno o más PDFs
2. El pipeline C1–C8 se ejecuta automáticamente
3. Revisar resultados por competencia (vista macro y micro)
4. Exportar resultados a Excel

### 2.6 Estructura del proyecto

```
proyectoIAA/
├── app.py                     # Entry point — aplicación Streamlit
├── requirements.txt           # Dependencias Python
├── .env                       # Variables de entorno 
├── MANUAL.md                  # Manual de usuario detallado
│
├── pipeline/                  # Lógica del pipeline de evaluación
│   ├── c1_ingesta.py          # Extracción PDF + detección tipo práctica
│   ├── c2_parser.py           # Parseo por secciones + mapa de relevancia
│   ├── c3_chunker.py          # Fragmentación en chunks (500 chars)
│   ├── c41_embeddings.py      # Generación de vectores (embeddings)
│   ├── c42_similitud_cos.py   # Similitud coseno fragmento-competencia
│   ├── c5_retriever.py        # Recuperación de evidencia (top-k, umbral)
│   ├── c6_evaluador.py        # Evaluación LLM con prompt estructurado
│   ├── c7_agregador.py        # Agregación de resultados + JPC
│   ├── c8_macro.py            # Estadísticas agregadas por cohorte
│   ├── router.py              # Clasificador de solicitudes HITL
│   ├── orchestrator.py        # Orquestador del pipeline completo
│   ├── batch_orchestrator.py  # Orquestación batch multi-informe
│   ├── batch_processor.py     # Procesamiento paralelo con límite
│   ├── cohorts.py             # Gestión de cohortes (CRUD)
│   ├── db.py                  # Operaciones de base de datos (JSON)
│   ├── hitl.py                # Lógica de ajuste humano (HITL)
│   ├── models.py              # Modelos de datos (dataclasses)
│   ├── persistence.py         # Persistencia en archivos JSON
│   ├── providers.py           # Proveedores de API (embeddings, LLM)
│   ├── report_runner.py       # Ejecutor individual por informe
│   └── reportes_export.py     # Exportación a Excel
│
├── ui/                        # Interfaz de usuario (Streamlit)
│   ├── components.py          # Componentes reutilizables
│   ├── icons.py               # Iconos SVG inline
│   ├── page_cohorts.py        # Vista: listado de cohortes
│   ├── page_cohort_detail.py  # Vista: resultados macro por cohorte
│   ├── page_cohort_reports.py # Vista: lista de informes (micro)
│   ├── page_cohort_config.py  # Vista: configuración de cohorte
│   ├── page_report_detail.py  # Vista: detalle por informe
│   ├── page_upload.py         # Vista: carga de informes
│   ├── page_processing.py     # Vista: progreso de procesamiento
│   └── page_cohort_comparison.py # Vista: comparación entre cohortes
│
├── config/                    # Archivos de configuración
│   ├── matriz.csv             # Matriz de competencias (editable)
│   └── rubrica.json           # Rúbrica estructural (editable)
│
├── assets/                    # Recursos estáticos
│   ├── style.css              # Estilos globales
│   ├── micro_views.css        # Estilos vistas detalle
│   ├── grid_fixes.css         # Correcciones de grid
│   └── logo_uandes.png        # Logo Universidad de los Andes
│
├── data/                      # Datos generados en ejecución
│   ├── index.json             # Índice global de informes
│   ├── cohorts.json           # Metadatos de cohortes
│   └── reports/               # Resultados por informe
│
└── tests/                     # Tests unitarios
    ├── test_c1_ingesta.py
    ├── test_c2_parser.py
    ├── test_c3_chunker.py
    ├── test_c6_evaluador.py
    ├── test_router.py
    └── test_timings.py
```

### 2.7 Mantenimiento

- **Respaldos:** la carpeta `data/` contiene todos los datos; respáldala periódicamente.
- **Actualización:** `git pull` para actualizar el código, luego `pip install -r requirements.txt` si cambiaron las dependencias.
- **Personalización:** editar `config/matriz.csv` para cambiar competencias, o `config/rubrica.json` para ajustar secciones y pesos.
- **Limpieza:** eliminar archivos dentro de `data/reports/` y reiniciar `data/index.json` a `{}` para empezar desde cero.
- **Logs:** Streamlit muestra logs en la consola; revisarlos ante errores inesperados.

### 2.8 Problemas frecuentes

| Problema | Causa | Solución |
|----------|-------|----------|
| `Error de API: 401` | Clave API inválida o vencida | Verificar claves en `.env` o barra lateral |
| `El PDF no contiene texto` | PDF escaneado o protegido | Usar PDF con texto digital o aplicar OCR |
| El procesamiento no avanza | Límite de concurrencia alcanzado | Esperar a que terminen procesos activos |
| Error al exportar Excel | Archivo bloqueado | Cerrar Excel si está abierto, reintentar |
| `ModuleNotFoundError` | Dependencia faltante | Ejecutar `pip install -r requirements.txt` |
| Puerto 8501 ocupado | Otro proceso usando el puerto | Usar `streamlit run app.py --server.port 8502` |

---

## 3. Código Fuente

### 3.1 Estructura de directorios

El proyecto sigue una arquitectura modular con separación clara entre:

- **`pipeline/`** — lógica de negocio y procesamiento (8 capas + orquestación)
- **`ui/`** — interfaz de usuario en Streamlit (9 páginas)
- **`config/`** — configuración de competencias y rúbrica
- **`assets/`** — recursos estáticos (CSS, imágenes)
- **`tests/`** — tests unitarios por capa
- **`data/`** — datos generados en tiempo de ejecución (no versionados)

### 3.2 Pipeline C1–C8

```
C1 (Ingesta) → C2 (Parser) → C3 (Chunker) → C41 (Embeddings) → C42 (Similitud) → C5 (Retriever) → C6 (LLM) → C7 (Agregador) → C8 (Macro)
                                                                                                        ↑
                                                                                                   HITL + Router
```

Cada capa es un archivo independiente dentro de `pipeline/`. El flujo se orquesta desde `orchestrator.py` y puede ejecutarse de forma individual o batch (`batch_orchestrator.py`). El sistema HITL (`router.py`, `hitl.py`) permite intervenir en cualquier punto del pipeline mediante solicitudes en lenguaje natural.

### 3.3 Interfaz de usuario (UI)

Construida con **Streamlit**, organizada en 9 páginas dentro de `ui/`. La navegación es gestionada mediante `st.session_state["page"]` y la barra lateral en `app.py`. Los estilos están en `assets/` y los componentes reutilizables en `ui/components.py`.

---

> Para más detalles, consultar el [manual de usuario completo](MANUAL.md) y la documentación interna de cada módulo.
