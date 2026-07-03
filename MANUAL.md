# Manual de Usuario — Evaluador de Perfil de Egreso

## 1. Objetivo de la aplicación

El **Evaluador de Perfil de Egreso** es una herramienta web que automatiza la evaluación de informes de práctica profesional y pre-profesional de estudiantes universitarios. Su objetivo es asistir a los docentes en la revisión de informes mediante un pipeline de inteligencia artificial que analiza cada documento, lo contrasta contra una matriz de competencias y genera una evaluación por competencia con nivel (0–3), justificación textual y citas extraídas del propio informe.

El sistema está diseñado para reducir el tiempo de revisión manual, aumentar la trazabilidad de las evaluaciones y entregar métricas agregadas (cobertura, tiempos, y un índice JPC de calidad del sustento) tanto a nivel de informe individual como de cohorte completa.

## 2. Público objetivo

- **Docentes y académicos** de la Universidad de los Andes (Chile) que supervisan prácticas profesionales o pre-profesionales.
- **Coordinadores de programa** que necesitan dar seguimiento al logro del perfil de egreso a lo largo de cohortes.
- **Ayudantes o revisores** que participan en el proceso de corrección de informes.

No se requiere conocimiento técnico en programación ni en inteligencia artificial para operar la herramienta.

## 3. Requisitos para su utilización

### 3.1 Requisitos del sistema
- Navegador web moderno (Chrome 90+, Firefox 88+, Edge 90+, Safari 14+).
- Conexión a Internet estable.
- Cuenta en al menos un proveedor de API de IA (ver sección 3.2).

### 3.2 Requisitos de configuración (una vez por instalación)

El administrador del sistema debe configurar las siguientes claves de API en un archivo `.env`:

| Variable | Proveedor | ¿Obligatoria? | Uso |
|----------|-----------|---------------|-----|
| `GEMINI_API_KEY` | Google Gemini | Recomendada | Generación de embeddings (vectores de texto) |
| `OPENAI_API_KEY` | OpenAI | Alternativa | Generación de embeddings (alternativa) |
| `OPENROUTER_API_KEY` | OpenRouter | Recomendada | Evaluación por LLM (C6) |

Si alguna clave no está configurada, la aplicación mostrará un panel en la barra lateral para ingresarla durante la sesión.

### 3.3 Requisitos de entrada
- Informes de práctica en formato **PDF** (texto digital, no escaneados como imagen).
- Archivos **ZIP** con múltiples PDFs (para procesamiento por lotes).
- **Matriz de competencias** (archivo CSV opcional, con formato predefinido).
- **Rúbrica estructural** (archivo JSON opcional, con definición de secciones).

## 4. Funcionalidades disponibles

### 4.1 Gestión de cohortes
- **Crear cohorte**: agrupa informes bajo un nombre (ej. "Práctica Profesional 2025-I").
- **Eliminar cohorte**: elimina una cohorte y todos sus informes asociados.
- **Renombrar cohorte**: cambia el nombre de una cohorte existente.
- **Listar cohortes**: vista general con cantidad de informes y promedios globales.

### 4.2 Carga y procesamiento de informes
- **Subida individual**: arrastra y suelta uno o más PDFs.
- **Subida por lote**: arrastra y suelta un archivo ZIP con múltiples PDFs.
- **Detección de duplicados**: el sistema detecta informes duplicados por contenido (hash) y por nombre de archivo, permitiendo excluirlos.
- **Selección de tipo de práctica**: Pre-Profesional o Profesional.
- **Procesamiento batch**: múltiples informes se procesan en paralelo con límite configurable de concurrencia (5 por defecto).
- **Barra de progreso en tiempo real**: indicador por informe y por competencia.

### 4.3 Pipeline de evaluación (C1–C7)

| Capa | Nombre | ¿Qué hace? |
|------|--------|------------|
| C1 | Ingesta | Extrae el texto del PDF, detecta el tipo de práctica y carga la matriz de competencias. |
| C2 | Parser | Identifica secciones del informe (introducción, desarrollo, conclusiones, etc.) y construye un mapa de relevancia. |
| C3 | Chunker | Fragmenta el texto en segmentos de máximo 500 caracteres, preservando la sección de origen. |
| C41 | Embeddings | Genera vectores numéricos (embeddings) para cada fragmento y para cada competencia. |
| C42 | Similitud coseno | Calcula qué tan similares son los fragmentos del informe respecto a cada competencia. |
| C5 | Retriever | Selecciona los fragmentos más relevantes (top-k) como evidencia para cada competencia. |
| C6 | Evaluador | Envía la evidencia a un modelo de lenguaje (LLM) que genera nivel, justificación y citas textuales. |
| C7 | Agregador | Consolida resultados, calcula el índice JPC y genera la vista previa. |
| C8 | Macro | Calcula estadísticas agregadas a nivel de cohorte. |

### 4.4 Revisión y ajuste humano (HITL)
- **Vista por competencia**: muestra nivel asignado (0–3), justificación, citas textuales y puntaje JPC.
- **Ajuste manual**: el usuario puede escribir solicitudes de cambio en lenguaje natural, como:
  - *"Cambiar nivel a 2"*
  - *"Buscar más evidencia en la sección de resultados"*
  - *"La justificación no es coherente con el informe"*
- El sistema clasifica la solicitud (vía `router.py`) y re-ejecuta únicamente la capa del pipeline necesaria.
- **Aceptar/Rechazar**: cada competencia puede marcarse como aceptada o rechazada.

### 4.5 Visualización de resultados

| Vista | Ruta | Contenido |
|-------|------|-----------|
| Mis Cohortes | `cohorts` | Lista de cohortes con promedios globales. |
| Resultados Macro | `cohort_detail` | Estadísticas agregadas por competencia en toda la cohorte. |
| Resultados Micro | `cohort_reports` | Lista de informes dentro de una cohorte con sus promedios individuales. |
| Detalle Informe | `report_detail` | Desglose completo por competencia con nivel, justificación, citas y JPC. |
| Comparar Cohortes | `cohort_comparison` | Gráficos comparativos lado a lado entre dos cohortes. |
| Configuración | `cohort_config` | Editar nombre, eliminar informes, exportar Excel. |

### 4.6 Exportación a Excel
El archivo Excel generado contiene tres hojas:

1. **Resumen Macro de Competencias**: estadísticas agregadas por competencia en la cohorte, incluyendo porcentaje de aprobación por nivel y desglose JPC.
2. **Resultados de Evaluación**: detalle por informe y por competencia con nivel, justificación y citas textuales.
3. **Reporte de Procesamiento**: tiempos de procesamiento, análisis de secciones, historial de ajustes y trazabilidad.

### 4.7 KPIs registrados
- **Cobertura**: competencias procesadas vs. competencias esperadas.
- **Tiempos**: tiempo automático, tiempo de revisión, tiempo de ajustes y tiempo total.
- **Índice JPC**: promedio de C (cantidad de citas), S (relevancia de sección), R (similitud coseno) y F (confianza del LLM).

## 5. Instrucciones paso a paso

### 5.1 Primer uso: configurar las API keys

Si eres administrador del sistema y las claves no están configuradas:

1. Abre el archivo `.env` en la carpeta del proyecto.
2. Agrega tus claves:
   ```
   GEMINI_API_KEY=tu_clave_aqui
   OPENAI_API_KEY=tu_clave_aqui
   OPENROUTER_API_KEY=tu_clave_aqui
   ```
3. Guarda el archivo y reinicia la aplicación.
4. Si no tienes acceso al archivo `.env`, puedes ingresar las claves desde la barra lateral de la aplicación (panel "Configuración de API").

### 5.2 Crear una cohorte y subir informes

1. Desde la página principal, haz clic en **"Nueva Cohorte"**.
2. Ingresa un nombre para la cohorte (ej. "Práctica Pre-Profesional 2025").
3. Arrastra y suelta los archivos PDF (o un ZIP con varios PDFs) en el área de carga.
4. Selecciona el tipo de práctica: **Pre-Profesional** o **Profesional**.
5. (Opcional) Sube una matriz de competencias personalizada (CSV) o una rúbrica (JSON).
6. Haz clic en **"Crear Cohorte"**.
7. El sistema comenzará a procesar los informes automáticamente.

### 5.3 Monitorear el procesamiento

1. Durante el procesamiento, la vista **"Procesando"** muestra:
   - Barra de progreso global.
   - Progreso individual de cada informe (qué capa del pipeline está ejecutando).
   - Progreso por competencia dentro de cada informe.
2. Puedes navegar a otras vistas mientras se procesa; el sistema continúa en segundo plano.
3. Al finalizar, serás redirigido automáticamente a la vista de resultados macro.

### 5.4 Revisar resultados

1. En **"Resultados Macro"** (vista por defecto tras el procesamiento), observa:
   - Gráfico de barras con el promedio por competencia en toda la cohorte.
   - Tabla resumen con niveles promedio y desglose JPC.
2. Haz clic en una competencia para ver el detalle por informe.
3. Desde **"Resultados Micro"**, haz clic en un informe específico para ver su **detalle completo**.

### 5.5 Ajustar una evaluación (HITL)

1. Desde la vista de **"Detalle Informe"**, localiza la competencia que deseas ajustar.
2. En el campo de texto **"Solicitar ajuste"**, escribe tu solicitud en lenguaje natural, por ejemplo:
   - *"Subir nivel a 2 porque el informe describe implementación"*
   - *"La evidencia citada no corresponde a esta competencia"*
3. Presiona Enter o haz clic en **"Enviar"**.
4. El sistema procesará el ajuste y actualizará la evaluación.
5. Si estás conforme, marca la competencia como **"Aceptada"**.
6. Si no estás conforme, puedes rechazarla y escribir un nuevo ajuste.

### 5.6 Exportar resultados a Excel

1. Desde la vista **"Configuración"** de la cohorte (o desde el detalle de informe), haz clic en **"Exportar a Excel"**.
2. El archivo se descargará automáticamente con las tres hojas descritas en la sección 4.6.

### 5.7 Comparar dos cohortes

1. Desde el menú lateral, selecciona **"Comparar Cohortes"**.
2. Elige dos cohortes de los menús desplegables.
3. El sistema mostrará gráficos comparativos lado a lado por competencia.
4. Los resultados se actualizan automáticamente al cambiar la selección.

## 6. Ejemplos prácticos y casos de uso

### Caso 1: Evaluación individual de un informe

**Escenario**: La profesora María recibe el informe de práctica de un estudiante y quiere evaluarlo rápidamente.

1. María crea una cohorte llamada "Práctica Profesional 2025-01".
2. Arrastra el PDF del informe al área de carga.
3. Selecciona "Profesional" como tipo de práctica.
4. Hace clic en "Crear Cohorte".
5. En 2–3 minutos, el sistema entrega la evaluación completa.
6. María revisa cada competencia. Encuentra que la competencia "Trabajo en equipo" fue evaluada con nivel 1, pero según el informe el estudiante lideró un equipo de 5 personas.
7. Escribe: *"Subir nivel a 3, el estudiante lideró un equipo multidisciplinario"*.
8. El sistema re-evalúa y asigna nivel 3 con una nueva justificación.
9. María acepta la corrección y exporta el Excel para adjuntarlo a las notas.

### Caso 2: Procesamiento por lote de 30 informes

**Escenario**: El coordinador Pedro debe evaluar 30 informes de la misma promoción.

1. Pedro comprime los 30 PDFs en un archivo ZIP.
2. Crea una cohorte llamada "Práctica Pre-Profesional 2025".
3. Arrastra el ZIP al área de carga.
4. El sistema detecta automáticamente un archivo duplicado (mismo contenido, nombre distinto) y pregunta si desea excluirlo.
5. Pedro confirma la exclusión y procede con los 29 informes restantes.
6. El sistema procesa los informes en paralelo (5 concurrentes). El progreso se muestra en tiempo real.
7. Tras 15–20 minutos, todos los informes están evaluados.
8. Pedro accede a "Resultados Macro" para ver el promedio general de la cohorte.
9. Identifica que la competencia "Innovación" tiene el promedio más bajo (1.2).
10. Exporta el Excel con el resumen macro para presentarlo en el consejo de facultad.

### Caso 3: Comparación entre cohortes

**Escenario**: El director del programa quiere comparar los resultados del año 2024 vs. 2025.

1. El director tiene dos cohortes ya creadas: "Práctica 2024" y "Práctica 2025".
2. Va a "Comparar Cohortes" y selecciona ambas.
3. El sistema muestra gráficos lado a lado. Se observa que:
   - "Comunicación efectiva" subió de 2.1 a 2.6.
   - "Responsabilidad profesional" se mantuvo estable (2.8 → 2.8).
   - "Innovación" bajó de 2.0 a 1.5.
4. El director decide investigar por qué bajó "Innovación" y programa una reunión con los supervisores de práctica.

### Caso 4: Ajuste por evidencia faltante

**Escenario**: El revisor Carlos nota que una competencia fue evaluada con nivel 0 ("Sin evidencia"), pero él recuerda que el informe sí menciona el tema en la sección de conclusiones.

1. Carlos escribe en el campo de ajuste: *"Buscar en la sección de conclusiones, ahí se menciona el uso de metodologías ágiles"*.
2. El router clasifica la solicitud como un cambio en la capa C5 (recuperación de evidencia).
3. El sistema re-ejecuta la recuperación con énfasis en la sección indicada y encuentra los fragmentos relevantes.
4. Luego re-ejecuta C6 (evaluación) con la nueva evidencia.
5. El nivel cambia de 0 a 2, con citas textuales de la sección de conclusiones.

## 7. Limitaciones conocidas

1. **Dependencia de API externas**: el sistema requiere conexión a Internet y claves API vigentes. Si un proveedor está caído o la clave expiró, el procesamiento falla (con mensaje de error claro).
2. **Calidad del PDF**: los informes deben ser PDF con texto digital seleccionable. Los PDF escaneados (imágenes) no pueden ser procesados automáticamente. Si se detecta un PDF sin texto, el sistema lo reporta como error.
3. **Tiempo de procesamiento**: la evaluación por LLM puede tomar entre 1 y 5 minutos por informe, dependiendo de la cantidad de competencias y la velocidad del proveedor API.
4. **Límite de concurrencia**: por defecto se procesan hasta 5 informes en paralelo y máximo 10 por lote. Esto es configurable por el administrador.
5. **Sin autenticación de usuarios**: la herramienta no incluye sistema de inicio de sesión ni permisos por rol. Está diseñada para uso interno en un entorno controlado.
6. **Almacenamiento en archivos JSON**: los datos se guardan en archivos JSON locales. No está diseñada para escalar a cientos de miles de informes ni para uso multiusuario simultáneo intensivo.
7. **Idioma**: la interfaz y los prompts de evaluación están en español. No se recomienda usarla con informes en otros idiomas.
8. **Sensibilidad a la estructura del informe**: el parser (C2) funciona mejor con informes que siguen la estructura esperada (introducción, marco teórico, desarrollo, conclusiones). Informes con estructuras muy atípicas pueden producir resultados subóptimos.
9. **Modelos de lenguaje**: la calidad de la evaluación depende del modelo LLM utilizado. Si se usa un modelo gratuito o de baja capacidad, las justificaciones pueden ser menos precisas. El sistema incluye un mecanismo de *fallback* que cambia automáticamente a un modelo alternativo si el principal falla.

## 8. Consideraciones relevantes

### 8.1 Privacidad y datos
- Los informes de estudiantes y sus evaluaciones se almacenan localmente en el servidor donde se ejecuta la aplicación.
- Los datos enviados a las APIs externas (Google Gemini, OpenAI, OpenRouter) están sujetos a las políticas de privacidad de cada proveedor. Se recomienda no incluir información sensible o personal sin consultar con la unidad de protección de datos de la institución.
- El sistema no comparte datos entre distintas instalaciones ni los utiliza para entrenar modelos (salvo que el proveedor lo haga por defecto en su capa gratuita; revisar términos de servicio).

### 8.2 Respaldos
- Los datos se almacenan en la carpeta `data/` del proyecto. Se recomienda realizar respaldos periódicos de esta carpeta.
- El archivo Excel exportado sirve como respaldo de los resultados de evaluación.

### 8.3 Personalización
- La **matriz de competencias** (`config/matriz.csv`) puede modificarse para reflejar el perfil de egreso de cada carrera.
- La **rúbrica** (`config/rubrica.json`) puede ajustarse para cambiar las secciones evaluadas o sus pesos relativos.
- Los **niveles de evaluación** (0–3) y sus etiquetas están definidos en la configuración del pipeline.

### 8.4 Solución de problemas comunes

| Problema | Causa probable | Solución |
|----------|---------------|----------|
| "Error de API: 401" | Clave API inválida o vencida | Verificar claves en `.env` o barra lateral |
| "El PDF no contiene texto" | PDF escaneado o protegido | Usar un PDF con texto digital o OCR |
| "El procesamiento no avanza" | Límite de concurrencia alcanzado | Esperar a que terminen los procesos activos |
| "La evaluación parece incorrecta" | Evidencia insuficiente o mal recuperada | Usar el ajuste HITL para redirigir la búsqueda |
| "Error al exportar Excel" | Archivo bloqueado o permisos | Cerrar el Excel si está abierto, reintentar |

### 8.5 Soporte
Para reportar problemas o solicitar mejoras, contactar al equipo desarrollador. Este manual está diseñado para que cualquier usuario pueda operar la herramienta de forma autónoma sin apoyo directo del equipo técnico.
