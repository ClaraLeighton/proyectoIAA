import streamlit as st
import base64
from pipeline.cohorts import get_cohort, compute_cohort_macro, delete_cohort, update_cohort_name
from pipeline.reportes_export import build_export_index, exportar_excel_multi_hoja
from ui.components import page_hero, badge, metric_grid, action_tiles
from ui.icons import chart, upload, download, trash


def _formatear_tipo(tipo: str) -> str:
    nombre = tipo.replace("_", " ").title()
    nombre = nombre.replace("Pre ", "Pre-")
    nombre = nombre.replace("Practica", "Práctica")
    return nombre


@st.dialog("Eliminar Cohorte")
def confirm_delete_dialog(cohort_id, cohort_name, n_reports):
    st.write(f"¿Estás seguro de que deseas eliminar la cohorte **'{cohort_name}'**?")
    st.write(f"Esta acción eliminará permanentemente la cohorte y sus **{n_reports}** informes asociados. Esta acción **no se puede deshacer**.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancelar", use_container_width=True, key="cancel_delete_dialog"):
            st.rerun()
    with col2:
        if st.button("Sí, eliminar", type="primary", use_container_width=True, key="confirm_delete_dialog_btn"):
            delete_cohort(cohort_id)
            st.session_state.pop("selected_cohort_id", None)
            st.session_state.pop("_export_buf", None)
            st.session_state.pop("_export_name", None)
            st.session_state["report_count"] = max(0, st.session_state.get("report_count", 0) - n_reports)
            st.session_state["page"] = "cohorts"
            st.rerun()


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
        "Configuración: " + cohort["name"],
        subtitle="Acciones rápidas y gestión de la cohorte.",
        meta_items=meta_items,
        back_target="cohorts",
    )

    def get_status_class(val):
        if isinstance(val, float):
            if val >= 0.70: return "ok"
            if val >= 0.50: return "mid"
            return "risk"
        return ""

    metric_grid([
        {"label": "Score Global", "value": f'{g["score_pct"]:.1%}' if g["total_reportes"] > 0 else "—", "status": get_status_class(g["score_pct"]), "sub": "Promedio ponderado según desempeño"},
        {"label": "Nivel Promedio", "value": f'{g["nivel_promedio_global"]:.2f}' if g["total_reportes"] > 0 else "—", "status": get_status_class(g["nivel_promedio_global"] / 3), "sub": "Escala de 0 a 3 (Sin evidencia a Dominio técnico)"},
    ])

    st.subheader("Acciones Rápidas")
    
    # Preparar Excel base64 para descarga directa desde el tile
    export_index = build_export_index(cohort.get("report_ids", []))
    excel_io = exportar_excel_multi_hoja(export_index)
    excel_b64 = base64.b64encode(excel_io.getvalue()).decode()
    
    col_tiles = st.columns(4)
    with col_tiles[0]:
        action_tiles([{
            "icon": chart(28, 28, "currentColor"),
            "title": "Resultados Macro",
            "desc": "Ver resumen agregado de la cohorte",
            "tone": "tone-red",
            "url": f"?page=cohort_macro&cid={cohort_id}"
        }])
        
    with col_tiles[1]:
        action_tiles([{
            "icon": upload(28, 28, "currentColor"),
            "title": "Agregar Informes",
            "desc": "Subir más informes a esta cohorte",
            "tone": "tone-blue",
            "url": f"?page=upload&cid={cohort_id}&new=0"
        }])

    with col_tiles[2]:
        action_tiles([{
            "icon": download(28, 28, "currentColor"),
            "title": "Exportar Excel",
            "desc": "Descargar resultados validados",
            "tone": "tone-yellow",
            "download": excel_b64,
            "filename": f"{cohort['name']}.xlsx"
        }])

    with col_tiles[3]:
        action_tiles([{
            "icon": trash(28, 28, "currentColor"),
            "title": "Eliminar Cohorte",
            "desc": "Borrar cohorte e informes",
            "danger": True,
            "tone": "tone-danger",
            "url": "?page=cohort_config&action=confirm_delete"
        }])

    if st.session_state.get("_action") == "confirm_delete":
        st.session_state.pop("_action", None)
        confirm_delete_dialog(cohort_id, cohort["name"], n_reports)

    st.subheader("Configuración")
    with st.container(border=True):
        st.markdown('<div class="uandes-form-section">Edición de datos</div>', unsafe_allow_html=True)
        col_name, col_meta = st.columns([2, 1])
        with col_name:
            new_name = st.text_input("Nombre de la cohorte", value=cohort["name"], key="edit_cohort_name")
            if new_name != cohort["name"]:
                if update_cohort_name(cohort_id, new_name):
                    st.success("Nombre actualizado.")
                    st.rerun()
        with col_meta:
             st.markdown(f'''
             <div class="config-meta-card">
               <p><strong>Tipo:</strong> {tipo_label}</p>
               <p><strong>Creada:</strong> {cohort.get("created_at", "")[:10]}</p>
             </div>
             ''', unsafe_allow_html=True)
