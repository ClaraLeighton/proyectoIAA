import streamlit as st
from pipeline.cohorts import get_cohort, compute_cohort_macro, delete_cohort, update_cohort_name
from pipeline.reportes_export import exportar_excel_multi_hoja
from pipeline.persistence import load_report
from ui.components import page_hero, section_card, section_card_end, badge, metric_grid, empty_state, action_tiles
from ui.icons import chart, upload, download, trash


def _formatear_tipo(tipo: str) -> str:
    nombre = tipo.replace("_", " ").title()
    nombre = nombre.replace("Pre ", "Pre-")
    nombre = nombre.replace("Practica", "Práctica")
    return nombre


def render():
    cohort_id = st.session_state.get("selected_cohort_id")
    cohort = get_cohort(cohort_id) if cohort_id else None

    if not cohort:
        st.warning("No se encontró la cohorte seleccionada.")
        return

    tipo_label = _formatear_tipo(cohort.get("tipo_documento", ""))
    n_reports = len(cohort.get("report_ids", []))
    macro = compute_cohort_macro(cohort_id)
    g = macro["global"]

    meta_items = [
        badge(tipo_label, "outline"),
        f"{n_reports} informe{'s' if n_reports != 1 else ''}",
    ]
    if cohort.get("created_at"):
        meta_items.append(f'Creada: {cohort["created_at"][:10]}')

    page_hero(
        cohort["name"],
        subtitle="Configuración, acciones rápidas y gestión de la cohorte.",
        meta_items=meta_items,
        back_target="cohorts",
    )

    metric_grid([
        ("Score Global", f'{g["score_pct"]:.1%}' if g["total_reportes"] > 0 else "—", True, f'{g["score_actual"]}/{g["score_max"]}' if g["total_reportes"] > 0 else ""),
        ("Nivel Promedio", f'{g["nivel_promedio_global"]:.2f}' if g["total_reportes"] > 0 else "—"),
        ("Total Informes", g["total_reportes"]),
        ("Tipo", tipo_label),
    ])

    section_card("Acciones Rápidas")
    action_tiles([
        {
            "icon": chart(28, 28, "#17212B"),
            "title": "Resultados Macro",
            "desc": "Ver resumen agregado de la cohorte",
        },
        {
            "icon": upload(28, 28, "#17212B"),
            "title": "Agregar Informes",
            "desc": "Subir más informes a esta cohorte",
        },
        {
            "icon": download(28, 28, "#17212B"),
            "title": "Exportar Excel",
            "desc": "Descargar resultados en Excel",
        },
        {
            "icon": trash(28, 28, "#CE0019"),
            "title": "Eliminar Cohorte",
            "desc": "Borrar esta cohorte y sus informes",
            "danger": True,
        },
    ])
    section_card_end()

    col_tiles = st.columns(4)
    with col_tiles[0]:
        if st.button("Resultados Macro", key="tile_macro", use_container_width=True):
            st.session_state["page"] = "cohort_macro"
            st.rerun()
    with col_tiles[1]:
        if st.button("Agregar informes", key="tile_upload", use_container_width=True):
            st.session_state["new_cohort"] = False
            st.session_state["page"] = "upload"
            st.rerun()
    with col_tiles[2]:
        if st.button("Exportar Excel", key="tile_export", use_container_width=True):
            st.session_state["_trigger_export"] = True
            st.rerun()
    with col_tiles[3]:
        if st.button("Eliminar cohorte", key="tile_delete", use_container_width=True):
            st.session_state["_show_delete"] = True
            st.rerun()

    section_card("Configuración")

    col_info1, col_info2 = st.columns(2)
    with col_info1:
        new_name = st.text_input("Nombre de la cohorte", value=cohort["name"], key="edit_cohort_name")
        if new_name != cohort["name"]:
            if update_cohort_name(cohort_id, new_name):
                st.success("Nombre actualizado.")
                st.rerun()
    with col_info2:
        st.markdown(f'<p style="font-size:14px;color:var(--uandes-text-secondary);margin-bottom:4px"><strong>Creada:</strong> {cohort.get("created_at", "")[:19]}</p>', unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:14px;color:var(--uandes-text-secondary);margin-bottom:4px"><strong>Tipo:</strong> {tipo_label}</p>', unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:14px;color:var(--uandes-text-secondary);margin-bottom:4px"><strong>Informes:</strong> {n_reports}</p>', unsafe_allow_html=True)

    section_card_end()

    if st.session_state.get("_trigger_export"):
        index = [load_report(rid).to_index_entry() for rid in cohort["report_ids"] if load_report(rid)]
        index = [e for e in index if e]
        st.session_state["_export_buf"] = exportar_excel_multi_hoja(index)
        st.session_state["_export_name"] = f"{cohort['name']}.xlsx"
        st.session_state["_trigger_export"] = False

    if st.session_state.get("_export_buf"):
        st.download_button(
            "Descargar Excel",
            data=st.session_state["_export_buf"],
            file_name=st.session_state["_export_name"],
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    if st.session_state.get("_show_delete"):
        section_card("Eliminar cohorte")
        st.warning(f"¿Eliminar toda la cohorte **'{cohort['name']}'** y sus **{n_reports}** informes? Esta acción no se puede deshacer.")
        confirm = st.text_input("Escribe 'ELIMINAR' para confirmar:", key="del_confirm")
        if confirm == "ELIMINAR":
            if st.button("Sí, eliminar", type="primary"):
                delete_cohort(cohort_id)
                st.session_state.pop("selected_cohort_id", None)
                st.session_state.pop("_export_buf", None)
                st.session_state.pop("_show_delete", None)
                st.session_state["page"] = "cohorts"
                st.rerun()
        section_card_end()
