import streamlit as st
import json
from typing import Any


def _json(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, default=str)


def _safe_json(obj: Any) -> str:
    try:
        return _json(obj)
    except Exception:
        return str(obj)


def render() -> None:
    st.title("Administración — Inspección por Capa")

    state = st.session_state.get("pipeline_state")
    if state is None:
        st.info("No hay un pipeline ejecutado. Sube un PDF y ejecuta el pipeline primero.")
        return

    tabs = st.tabs(["C1 — Ingesta", "C2 — Parseo", "C3 — Chunking",
                     "C4 — Embeddings", "C5 — Retrieval", "C6 — Evaluación",
                     "C7 — Agregación", "Pipeline State (raw)"])

    c1 = state.get("c1", {})
    c2 = state.get("c2", {})
    c3 = state.get("c3", {})
    c4 = state.get("c4", {})
    resultados = state.get("resultados_competencias", [])
    c7 = state.get("c7", {})

    with tabs[0]:
        _render_c1(c1)

    with tabs[1]:
        _render_c2(c2)

    with tabs[2]:
        _render_c3(c3)

    with tabs[3]:
        _render_c4(c4, resultados)

    with tabs[4]:
        _render_c5(resultados)

    with tabs[5]:
        _render_c6(resultados)

    with tabs[6]:
        _render_c7(c7)

    with tabs[7]:
        st.code(_safe_json(state), language="json")


def _render_c1(c1: dict) -> None:
    st.subheader("Metadatos del documento")
    st.json(c1.get("metadatos", {}))

    st.subheader("Tipo de documento")
    st.code(c1.get("tipo_documento", "N/A"))

    st.subheader("Competencias activas")
    comps = c1.get("competencias_activas", [])
    if comps:
        data = []
        for c in comps:
            data.append({
                "ID": c.get("competencia_id"),
                "Nombre": c.get("nombre"),
                "Descripción": c.get("descripcion", "")[:120],
            })
        st.dataframe(data, use_container_width=True)
    else:
        st.info("Sin competencias activas.")

    st.subheader("Config activa (rúbrica)")
    st.json(c1.get("config_activa", {}))

    st.subheader("Texto completo extraído")
    texto = c1.get("texto_completo", "")
    with st.expander(f"Ver texto ({len(texto)} caracteres)", expanded=False):
        st.text_area("texto", texto, height=400, label_visibility="collapsed")

    st.subheader("Reporte C1")
    st.json(c1.get("reporte", {}))


def _render_c2(c2: dict) -> None:
    st.subheader("Secciones del informe")
    secciones = c2.get("secciones_informe", {})
    if secciones:
        data = []
        for nombre, info in secciones.items():
            txt = info.get("texto", "")
            data.append({
                "Sección": nombre,
                "Peso": info.get("peso", 0),
                "Texto preview": txt[:150],
            })
        st.dataframe(data, use_container_width=True)
    else:
        st.info("Sin secciones.")

    st.subheader("Mapa de relevancia")
    mapa = c2.get("mapa_relevancia", {})
    if mapa:
        for cid, secciones_map in mapa.items():
            with st.expander(f"{cid}", expanded=False):
                data = []
                for sec, tipo in secciones_map.items():
                    data.append({"Sección": sec, "Tipo": tipo})
                if data:
                    st.dataframe(data, use_container_width=True)
    else:
        st.info("Sin mapa de relevancia.")

    st.subheader("Reporte C2")
    st.json(c2.get("reporte", {}))


def _render_c3(c3: dict) -> None:
    st.subheader("Fragmentos (chunks)")
    chunks = c3.get("chunks", [])
    st.metric("Total chunks", len(chunks))

    if chunks:
        data = []
        for ch in chunks:
            data.append({
                "chunk_id": ch.get("chunk_id"),
                "sección": ch.get("seccion"),
                "peso": ch.get("peso"),
                "posición": ch.get("posicion"),
                "texto": ch.get("texto", "")[:100],
            })
        st.dataframe(data, use_container_width=True)

        with st.expander("Ver texto completo de un chunk", expanded=False):
            chunk_ids = [ch.get("chunk_id", f"chunk_{i}") for i, ch in enumerate(chunks)]
            sel = st.selectbox("Seleccionar chunk", chunk_ids)
            for ch in chunks:
                if ch.get("chunk_id") == sel:
                    st.text_area("contenido", ch.get("texto", ""),
                                 height=200, label_visibility="collapsed")
                    break
    else:
        st.info("Sin chunks.")

    st.subheader("Reporte C3")
    st.json(c3.get("reporte", {}))


def _render_c4(c4: dict, resultados: list) -> None:
    rep = c4.get("reporte", {})
    st.metric("Modelo embeddings", rep.get("modelo_embeddings", "N/A"))
    st.metric("Proveedor", rep.get("proveedor", "N/A"))

    st.subheader("Embeddings data (chunks)")
    emb_data = c4.get("embeddings_data", [])
    if emb_data:
        data = []
        for e in emb_data:
            data.append({
                "chunk_id": e.get("chunk_id"),
                "sección": e.get("seccion"),
                "embedding dims": len(e.get("embedding", [])),
                "texto": e.get("texto", "")[:80],
            })
        st.dataframe(data, use_container_width=True)
    else:
        st.info("Sin datos de embeddings.")

    st.subheader("Similitud por competencia (top 5 chunks)")
    sims_by_comp = c4.get("similarities_by_comp", {})
    if sims_by_comp:
        for cid, sims in sims_by_comp.items():
            with st.expander(f"{cid}", expanded=False):
                sorted_sims = sorted(sims.items(), key=lambda x: x[1], reverse=True)[:5]
                data = []
                for ch_id, score in sorted_sims:
                    texto = ""
                    for e in emb_data:
                        if e.get("chunk_id") == ch_id:
                            texto = e.get("texto", "")[:100]
                            break
                    data.append({"chunk_id": ch_id, "similitud": round(score, 4), "texto": texto})
                st.dataframe(data, use_container_width=True)
    else:
        st.info("Sin datos de similitud.")

    st.subheader("Reporte C4")
    st.json(rep)

    st.subheader("Vector de embedding por competencia")
    comp_embs = c4.get("comp_embeddings", {})
    if comp_embs:
        data = []
        for cid, vec in comp_embs.items():
            data.append({"competencia_id": cid, "dimensiones": len(vec), "primeros_5_valores": str(vec[:5])})
        st.dataframe(data, use_container_width=True)
    else:
        st.info("Sin vectores de competencia.")


def _render_c5(resultados: list) -> None:
    st.subheader("Evidencia recuperada por competencia")
    if not resultados:
        st.info("Sin resultados.")
        return

    for r in resultados:
        cid = r.get("competencia_id", "?")
        evidencia = r.get("evidencia_recuperada", [])
        r_sim = r.get("r_similitud", 0)
        with st.expander(f"{cid} — {len(evidencia)} fragmentos — R_similitud: {r_sim:.3f}", expanded=False):
            if evidencia:
                data = []
                for e in evidencia:
                    data.append({
                        "chunk_id": e.get("chunk_id"),
                        "sección": e.get("seccion"),
                        "tipo fuente": e.get("tipo_fuente"),
                        "similitud": round(e.get("similitud", 0), 4),
                        "texto": e.get("texto", "")[:150],
                    })
                st.dataframe(data, use_container_width=True)
            else:
                st.info("Sin evidencia.")


def _render_c6(resultados: list) -> None:
    st.subheader("Evaluación LLM por competencia")
    if not resultados:
        st.info("Sin resultados.")
        return

    for r in resultados:
        cid = r.get("competencia_id", "?")
        nombre = r.get("competencia_nombre", "")
        nivel = r.get("nivel", 0)
        just = r.get("justificacion", "")
        citas = r.get("citas", [])
        p = r.get("p", [])

        with st.expander(f"{cid} — {nombre} — Nivel {nivel}", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Nivel", nivel)
                st.metric("Confianza", f"{r.get('confianza', max(p) if p else 0):.2%}")
            with col2:
                if p:
                    st.markdown("**Distribución p:**")
                    labels = [f"N{i}" for i in range(len(p))]
                    st.markdown(" | ".join(f"{l}={v:.3f}" for l, v in zip(labels, p)))

            st.markdown("**Justificación**")
            st.write(just)

            if citas:
                st.markdown("**Citas textuales**")
                for j, cita in enumerate(citas):
                    st.markdown(f"{j+1}. _{cita}_")
            else:
                st.info("Sin citas.")

            st.markdown("**Reporte C6**")
            st.json(r.get("reporte", {}))

            raw = r.get("raw_response", "")
            if raw:
                with st.expander("Respuesta LLM raw", expanded=False):
                    st.code(raw, language="json")


def _render_c7(c7: dict) -> None:
    st.subheader("Vista preliminar")
    preview = c7.get("vista_preliminar", {}).get("resultados_competencias", [])
    if preview:
        data = []
        for r in preview:
            data.append({
                "ID": r.get("competencia_id"),
                "Nombre": r.get("competencia_nombre"),
                "Nivel": r.get("nivel"),
                "Label": r.get("nivel_label"),
                "Estado revisión": r.get("estado_revision"),
                "Estado final": r.get("estado_final", "pendiente"),
                "Confianza": f"{r.get('confianza', 0):.2%}",
                "Entropy": round(r.get("entropy", 0), 3),
            })
        st.dataframe(data, use_container_width=True)

        with st.expander("Detalle por competencia", expanded=False):
            for r in preview:
                cid = r.get("competencia_id", "?")
                st.markdown(f"**{cid}** — {r.get('competencia_nombre', '')}")
                st.json({
                    "nivel": r.get("nivel"),
                    "nivel_label": r.get("nivel_label"),
                    "secciones_fuente": r.get("secciones_fuente"),
                    "estado_revision": r.get("estado_revision"),
                    "estado_final": r.get("estado_final", "pendiente"),
                    "confianza": r.get("confianza"),
                    "entropy": r.get("entropy"),
                    "citas": r.get("citas"),
                })
    else:
        st.info("Sin vista preliminar.")

    st.subheader("Trazabilidad de competencias (con JPC)")
    trazabilidad = c7.get("reporte_procesamiento", {}).get("trazabilidad_competencias", [])
    if trazabilidad:
        data = []
        for tr in trazabilidad:
            data.append({
                "ID": tr.get("competencia_id"),
                "Cobertura citas": round(tr.get("C_cobertura_citas", 0), 3),
                "Pertinencia sección": round(tr.get("S_pertinencia_seccion", 0), 3),
                "R_similitud": round(tr.get("R_similitud_promedio", 0), 3),
                "F_confianza": round(tr.get("F_confianza", 0), 3),
                "JPC": round(tr.get("JPC", 0), 3),
                "JPC aplicable": tr.get("JPC_aplicable", False),
                "Estado final": tr.get("estado_final", "pendiente"),
            })
        st.dataframe(data, use_container_width=True)
    else:
        st.info("Sin trazabilidad.")

    st.subheader("Tiempos de procesamiento")
    st.json(c7.get("reporte_procesamiento", {}).get("tiempos", {}))

    st.subheader("Historial de ajustes HITL")
    ajustes = c7.get("reporte_procesamiento", {}).get("historial_ajustes", [])
    if ajustes:
        for a in ajustes:
            with st.expander(a.get("ajuste_id", "ajuste"), expanded=False):
                st.json(a)
    else:
        st.info("Sin ajustes.")

    st.subheader("Reporte C7")
    st.json(c7.get("reporte_procesamiento", {}))
