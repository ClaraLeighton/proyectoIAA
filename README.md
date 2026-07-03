# Evaluador de Informes de Práctica - MVP

Sistema de evaluación automatizada de informes de práctica profesional/pre-profesional mediante un pipeline de 7 capas (C1-C7) con Human-in-the-Loop (HITL).

## Arquitectura

```
C1 (Ingesta) → C2 (Parser) → C3 (Chunker) → C4 (Embeddings) → C5 (Retriever) → C6 (LLM Evaluador) → C7 (Agregador)
                                                                                    ↑
                                                                               HITL + Router
```

## Requisitos

- Python 3.10+
- Al menos una clave API de OpenAI, Google Gemini u OpenRouter (ver sección de configuración)

## Instalación

```bash
# Clonar el repositorio
cd evaluador-informes

# Instalar dependencias
pip install -r requirements.txt

# Configurar API keys
cp .env.example .env
# Editar .env con tus claves (ver sección siguiente)
```

## Configuración de API Keys

El sistema necesita al menos un proveedor para embeddings (Gemini u OpenAI) y uno para evaluación por LLM (OpenRouter, Gemini u OpenAI). Copia las claves en el archivo `.env` o ingrésalas desde la barra lateral de la aplicación.

### 1. OpenAI

Consigue una clave en [platform.openai.com/api-keys](https://platform.openai.com/api-keys).

En el archivo `.env`, pégala en `OPENAI_API_KEY`. El modelo usado es `text-embedding-3-small` para embeddings y `gpt-4o-mini` para evaluación por LLM.

OpenAI opera con créditos prepagos; la facturación es por uso (tokens). Revisa sus [políticas de uso de datos](https://openai.com/policies/api-data-usage) para conocer cómo se manejan los datos enviados.

### 2. OpenRouter

Consigue una clave en [openrouter.ai/keys](https://openrouter.ai/keys).

En el archivo `.env`, pégala en `OPENROUTER_API_KEY`. OpenRouter permite usar múltiples modelos de distintos proveedores desde una sola API. El modelo por defecto es `openrouter/free`.

Puedes explorar [todos los modelos disponibles](https://openrouter.ai/models) o los [modelos gratuitos](https://openrouter.ai/collections/free-models).

### 3. Google AI Studio (Gemini)

Consigue una clave de Gemini API en [Google AI Studio](https://aistudio.google.com/apikey).

En el archivo `.env`, pégala en `GEMINI_API_KEY`. El modelo usado es `models/gemini-embedding-2` para embeddings.

La API de Gemini expone un endpoint compatible con OpenAI en `https://generativelanguage.googleapis.com/v1beta/openai/`. Los límites de la capa gratuita varían por modelo. Revisa los [términos de Google](https://ai.google.dev/gemini-api/docs/terms) para conocer cómo se manejan los datos.

## Ejecución

```bash
streamlit run app.py
```

1. **Carga**: Sube un informe PDF (opcionalmente CSV de matriz y JSON de rúbrica).
2. **Pipeline**: Ejecuta el pipeline completo C1-C7.
3. **Revisión HITL**: Revisa cada competencia, acepta/modifica/rechaza.
4. **Resultados**: Exporta a Excel con dos hojas.

## Estructura

```
evaluador-informes/
  app.py                     # Entry point Streamlit
  requirements.txt
  .env
  pipeline/
    c1_ingesta.py            # Extracción PDF, detección tipo práctica
    c2_parser.py             # Parseo por secciones + mapa de relevancia
    c3_chunker.py            # Fragmentación en chunks (max 500 chars)
    c4_embeddings.py         # Embeddings + similitud coseno
    c5_retriever.py          # Recuperación de evidencia (top-k, umbral)
    c6_evaluador.py          # Evaluación LLM con prompt estructurado
    c7_agregador.py          # Agregación, JPC, vista preliminar
    router.py                # Clasificador de solicitudes HITL
    orchestrator.py          # Orquestador del pipeline
  ui/
    page_upload.py           # Página de carga
    page_pipeline.py         # Página de ejecución y HITL
    page_resultados.py       # Página de resultados y exportación
  config/
    matriz.csv               # Matriz de competencias
    rubrica.json             # Rúbrica estructural
  tests/                     # Tests unitarios
```

## KPIs

El sistema registra datos para tres KPIs:
1. **Cobertura de evaluación**: competencias procesadas vs esperadas.
2. **Reducción del tiempo de revisión**: T_automático, T_revisión, T_ajustes, T_total.
3. **Sustento (JPC)**: Promedio de C (citas), S (sección), R (similitud), F (confianza).
