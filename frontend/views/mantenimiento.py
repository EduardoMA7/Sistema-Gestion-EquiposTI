import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime, date

BASE_URL = os.getenv("API_GATEWAY_URL")

def _fetch_maintenance():
    try:
        response = requests.get(f"{BASE_URL}/maintenance/")
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.error(f"No se pudieron cargar los mantenimientos: {exc}")
        return []

def _fetch_maintenance_spare_parts(maintenance_id: int):
    try:
        response = requests.get(f"{BASE_URL}/maintenance/{maintenance_id}/spare-parts/")
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.warning(f"No se pudieron cargar los repuestos del mantenimiento #{maintenance_id}: {exc}")
        return []

def _create_maintenance(payload: dict):
    try:
        response = requests.post(f"{BASE_URL}/maintenance/", json=payload)
        if response.status_code in (200, 201):
            st.success("✅ Mantenimiento registrado correctamente.")
        else:
            st.error(f"No se pudo registrar el mantenimiento. Código: {response.status_code}")
    except Exception as exc:
        st.error(f"Error de conexión: {exc}")

def _render_history_tab():
    st.subheader("Historial de mantenimientos y costos")

    data = _fetch_maintenance()
    df = pd.DataFrame(data)

    if df.empty:
        st.info("No hay registros de mantenimiento.")
        return

    expected_cols = [
        "id_mantenimiento",
        "id_equipo",
        "equipo_nombre",
        "tipo_mantenimiento",
        "estado_mantenimiento",
        "prioridad",
        "fecha_solicitud",
        "fecha_programada",
        "fecha_inicio",
        "fecha_fin",
        "costo_mano_obra",
        "costo_repuestos",
        "costo_total",
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    for col in ["fecha_solicitud", "fecha_programada", "fecha_inicio", "fecha_fin"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    total_registros = len(df)
    total_costo = df["costo_total"].fillna(0).sum()
    preventivos = (df["tipo_mantenimiento"] == "preventivo").sum()
    correctivos = (df["tipo_mantenimiento"] == "correctivo").sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total mantenimientos", total_registros)
    c2.metric("Preventivos", int(preventivos))
    c3.metric("Correctivos", int(correctivos))
    c4.metric("Costo total", f"S/ {total_costo:,.2f}")

    st.markdown("---")

    with st.expander("🔍 Filtros de búsqueda", expanded=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            tipos = df["tipo_mantenimiento"].dropna().unique().tolist()
            filtro_tipo = st.multiselect(
                "Tipo de mantenimiento",
                tipos,
                default=tipos,
            )
        with col_f2:
            estados = df["estado_mantenimiento"].dropna().unique().tolist()
            filtro_estado = st.multiselect(
                "Estado",
                estados,
                default=estados,
            )
        with col_f3:
            texto_equipo = st.text_input(
                "Filtrar por equipo (nombre o ID)",
                placeholder="Ej. Laptop Dell, 1...",
            )

    df_filtrado = df.copy()
    if filtro_tipo:
        df_filtrado = df_filtrado[df_filtrado["tipo_mantenimiento"].isin(filtro_tipo)]
    if filtro_estado:
        df_filtrado = df_filtrado[df_filtrado["estado_mantenimiento"].isin(filtro_estado)]
    if texto_equipo:
        texto = texto_equipo.strip()
        mask = (
            df_filtrado["equipo_nombre"].astype(str).str.contains(texto, case=False, na=False)
            | df_filtrado["id_equipo"].astype(str).str.contains(texto, case=False, na=False)
        )
        df_filtrado = df_filtrado[mask]

    st.markdown("### 📋 Registros")

    records = (
        df_filtrado.sort_values("fecha_solicitud", ascending=False)
        .to_dict(orient="records")
    )

    h = st.columns([1, 2.5, 1.3, 1.5, 1.2, 1.8, 1.8, 1.8, 1.4, 1.2])
    h[0].markdown("**ID mant.**")
    h[1].markdown("**Equipo**")
    h[2].markdown("**Tipo**")
    h[3].markdown("**Estado**")
    h[4].markdown("**Prioridad**")
    h[5].markdown("**Fecha solicitud**")
    h[6].markdown("**Fecha programada**")
    h[7].markdown("**Fecha fin**")
    h[8].markdown("**Costo total**")
    h[9].markdown("**Acciones**")

    for mant in records:
        c = st.columns([1, 2.5, 1.3, 1.5, 1.2, 1.8, 1.8, 1.8, 1.4, 1.2])

        c[0].write(mant.get("id_mantenimiento", "—"))

        equipo_nombre = mant.get("equipo_nombre") or f"Equipo #{mant.get('id_equipo', '—')}"
        c[1].write(equipo_nombre)

        c[2].write(mant.get("tipo_mantenimiento", "—"))
        c[3].write(mant.get("estado_mantenimiento", "—"))
        c[4].write(mant.get("prioridad", "—"))

        c[5].write(
            mant["fecha_solicitud"].strftime("%Y-%m-%d %H:%M")
            if pd.notnull(mant.get("fecha_solicitud"))
            else "—"
        )
        c[6].write(
            mant["fecha_programada"].date()
            if pd.notnull(mant.get("fecha_programada"))
            else "—"
        )
        c[7].write(
            mant["fecha_fin"].strftime("%Y-%m-%d %H:%M")
            if pd.notnull(mant.get("fecha_fin"))
            else "—"
        )

        costo_total = mant.get("costo_total", 0) or 0
        c[8].write(f"S/ {costo_total:,.2f}")

        if c[9].button("Ver repuestos", key=f"btn_mant_{mant['id_mantenimiento']}"):

            @st.dialog("Repuestos / insumos")
            def _show_spare_parts_dialog(mant_dialog=mant):
                repuestos = _fetch_maintenance_spare_parts(mant_dialog["id_mantenimiento"])
                df_rep = pd.DataFrame(repuestos)
                if df_rep.empty:
                    st.caption("Este mantenimiento no tiene repuestos registrados.")
                else:
                    orden_cols = [
                        "id_repuesto",
                        "descripcion",
                        "cantidad",
                        "costo_unitario",
                        "subtotal",
                    ]
                    existentes = [c for c in orden_cols if c in df_rep.columns]
                    df_rep_vista = df_rep[existentes].rename(
                        columns={
                            "id_repuesto": "ID repuesto",
                            "descripcion": "Descripción",
                            "cantidad": "Cantidad",
                            "costo_unitario": "Costo unitario",
                            "subtotal": "Subtotal",
                        }
                    )
                    st.dataframe(df_rep_vista, use_container_width=True, hide_index=True)

            _show_spare_parts_dialog()

def _render_calendar_tab():
    st.subheader("Calendario de mantenimientos programados")

    data = _fetch_maintenance()
    df = pd.DataFrame(data)

    if df.empty:
        st.info("No hay mantenimientos registrados.")
        return

    if "fecha_programada" not in df.columns:
        st.warning("No se encontró la columna fecha_programada en los registros.")
        return

    df["fecha_programada"] = pd.to_datetime(df["fecha_programada"], errors="coerce")
    df_cal = df.dropna(subset=["fecha_programada"]).copy()

    if df_cal.empty:
        st.info("No hay mantenimientos programados.")
        return

    min_date = df_cal["fecha_programada"].min().date()
    max_date = df_cal["fecha_programada"].max().date()

    col1, col2 = st.columns(2)
    with col1:
        desde = st.date_input("Desde", value=min_date, min_value=min_date, max_value=max_date)
    with col2:
        hasta = st.date_input("Hasta", value=max_date, min_value=min_date, max_value=max_date)

    if desde > hasta:
        st.error("La fecha 'Desde' no puede ser mayor que 'Hasta'.")
        return

    mask = (df_cal["fecha_programada"].dt.date >= desde) & (df_cal["fecha_programada"].dt.date <= hasta)
    df_filtrado = df_cal[mask]

    st.markdown("### 🗓️ Mantenimientos programados en el rango seleccionado")

    vista = df_filtrado[
        [
            "id_mantenimiento",
            "id_equipo",
            "tipo_mantenimiento",
            "estado_mantenimiento",
            "prioridad",
            "fecha_programada",
        ]
    ].rename(
        columns={
            "id_mantenimiento": "ID mant.",
            "id_equipo": "Equipo",
            "tipo_mantenimiento": "Tipo",
            "estado_mantenimiento": "Estado",
            "prioridad": "Prioridad",
            "fecha_programada": "Fecha programada",
        }
    )

    st.dataframe(vista.sort_values("Fecha programada"), use_container_width=True, hide_index=True)

    resumen = (
        df_filtrado.groupby(df_filtrado["fecha_programada"].dt.date)["id_mantenimiento"]
        .count()
        .reset_index(name="total_mantenimientos")
    )
    st.markdown("### 📈 Resumen por día")
    st.dataframe(resumen.rename(columns={"fecha_programada": "Fecha"}), use_container_width=True, hide_index=True)

def _render_create_tab():
    st.subheader("Registrar / programar nuevo mantenimiento")

    with st.form("schedule_maintenance"):
        col1, col2 = st.columns(2)
        with col1:
            equipment_id = st.number_input("ID del equipo *", min_value=1, step=1)
            maintenance_type_label = st.selectbox(
                "Tipo de mantenimiento *",
                ["Preventivo", "Correctivo"],
            )
            priority_label = st.selectbox(
                "Prioridad",
                ["Baja", "Media", "Alta"],
            )
        with col2:
            scheduled_date = st.date_input("Fecha programada (opcional)", value=date.today())

        st.caption("* Campos obligatorios")

        if st.form_submit_button("💾 Registrar mantenimiento"):
            errores = []
            if not equipment_id:
                errores.append("Debe indicar un ID de equipo.")

            if errores:
                for e in errores:
                    st.error(e)
                return

            maintenance_type = "preventivo" if maintenance_type_label == "Preventivo" else "correctivo"
            priority = priority_label.lower()
            estado_mantenimiento = "solicitado"

            payload = {
                "id_equipo": int(equipment_id),
                "tipo_mantenimiento": maintenance_type,
                "estado_mantenimiento": estado_mantenimiento,
                "prioridad": priority,
                "fecha_solicitud": datetime.now().isoformat(),
                "fecha_programada": scheduled_date.isoformat() if scheduled_date else None,
                "fecha_inicio": None,
                "fecha_fin": None,
                "costo_mano_obra": None,
                "costo_repuestos": None,
            }

            _create_maintenance(payload)

def render():
    st.header("Gestión de Mantenimiento 🛠️")

    tab1, tab2, tab3 = st.tabs(
        [
            "📊 Historial y costos",
            "🗓️ Calendario programado",
            "➕ Registrar mantenimiento",
        ]
    )

    with tab1:
        _render_history_tab()
    with tab2:
        _render_calendar_tab()
    with tab3:
        _render_create_tab()