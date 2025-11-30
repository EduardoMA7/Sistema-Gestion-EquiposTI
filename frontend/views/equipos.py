import os
import pandas as pd
import requests
import streamlit as st

BASE_URL = os.getenv("API_GATEWAY_URL")

def _fetch_equipment():
    try:
        response = requests.get(f"{BASE_URL}/equipment/", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.error(f"No se pudieron cargar los equipos: {exc}")
        return []

def _fetch_equipment_detail(equipment_id: int):
    try:
        response = requests.get(f"{BASE_URL}/equipment/{equipment_id}", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.error(f"No se pudo cargar el detalle del equipo #{equipment_id}: {exc}")
        return None

def _fetch_equipment_movements(equipment_id: int):
    try:
        response = requests.get(
            f"{BASE_URL}/equipment/{equipment_id}/movements/", timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.warning(f"No se pudo cargar el historial de movimientos: {exc}")
        return []

def _fetch_equipment_purchases(equipment_id: int):
    try:
        response = requests.get(
            f"{BASE_URL}/equipment/{equipment_id}/purchases/", timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.warning(f"No se pudo cargar el historial de compras: {exc}")
        return []

def _fetch_locations():
    try:
        response = requests.get(f"{BASE_URL}/equipment/locations/", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.warning(f"No se pudieron cargar las ubicaciones: {exc}")
        return []

def _render_inventory_tab():
    st.subheader("Inventario de equipos de TI 🗂️")

    raw_data = _fetch_equipment()
    df = pd.DataFrame(raw_data)

    if df.empty:
        st.info("No hay equipos registrados.")
        return

    expected_cols = [
        "id_equipo",
        "codigo_inventario",
        "numero_serie",
        "tipo",
        "marca",
        "estado",
        "ubicacion_descripcion",
        "vida_util_meses",
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    estado_lower = df["estado"].fillna("").astype(str).str.lower()
    total_equipos = len(df)
    operativos = (estado_lower == "operativo").sum()
    en_mantenimiento = estado_lower.str.contains("manten", na=False).sum()
    dados_de_baja = estado_lower.str.contains("baja", na=False).sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de equipos", total_equipos)
    col2.metric("Operativos", int(operativos))
    col3.metric("En mantenimiento", int(en_mantenimiento))
    col4.metric("Dados de baja", int(dados_de_baja))

    st.markdown("---")

    with st.expander("Filtros de búsqueda", expanded=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filtro_tipo = st.multiselect(
                "Tipo de equipo", sorted(df["tipo"].dropna().unique().tolist())
            )
        with col_f2:
            filtro_estado = st.multiselect(
                "Estado operativo", sorted(df["estado"].dropna().unique().tolist())
            )
        with col_f3:
            texto_busqueda = st.text_input(
                "Buscar por código o serie",
                placeholder="EQ-0001, SN-123..., etc.",
            )

    df_filtrado = df.copy()

    if filtro_tipo:
        df_filtrado = df_filtrado[df_filtrado["tipo"].isin(filtro_tipo)]
    if filtro_estado:
        df_filtrado = df_filtrado[df_filtrado["estado"].isin(filtro_estado)]
    if texto_busqueda:
        mask = (
            df_filtrado["codigo_inventario"]
            .astype(str)
            .str.contains(texto_busqueda, case=False, na=False)
            | df_filtrado["numero_serie"]
            .astype(str)
            .str.contains(texto_busqueda, case=False, na=False)
        )
        df_filtrado = df_filtrado[mask]

    df_filtrado["ubicacion_actual"] = (
        df_filtrado["ubicacion_descripcion"].fillna("Sin ubicación registrada")
    )

    vista = df_filtrado[
        [
            "id_equipo",
            "codigo_inventario",
            "numero_serie",
            "tipo",
            "marca",
            "estado",
            "ubicacion_actual",
            "vida_util_meses",
        ]
    ].rename(
        columns={
            "id_equipo": "ID",
            "codigo_inventario": "Código inventario",
            "numero_serie": "Número de serie",
            "tipo": "Tipo",
            "marca": "Marca",
            "estado": "Estado operativo",
            "ubicacion_actual": "Ubicación actual",
            "vida_util_meses": "Vida útil (meses)",
        }
    )

    st.dataframe(vista, use_container_width=True, hide_index=True)

def _render_create_tab():
    st.subheader("Agregar nuevo equipo ➕")
    locations = _fetch_locations()
    ubicacion_options = locations or [
        {"id_ubicacion": None, "descripcion": "Sin ubicaciones disponibles"}
    ]
    if not locations:
        st.warning(
            "No hay ubicaciones activas. Crea una ubicación antes de registrar equipos."
        )

    with st.form("add_equipment"):
        col_a, col_b = st.columns(2)

        with col_a:
            codigo = st.text_input("Código de inventario *")
            serie = st.text_input("Número de serie *")
            tipo = st.selectbox(
                "Tipo *",
                ["Laptop", "Desktop", "Impresora", "Servidor", "Red", "Otro"],
            )
            marca = st.text_input("Marca *")

        with col_b:
            estado = st.selectbox(
                "Estado operativo *",
                ["Operativo", "En mantenimiento", "Baja"],
            )
            ubicacion_seleccionada = st.selectbox(
                "Ubicación actual *",
                options=ubicacion_options,
                format_func=lambda loc: loc["descripcion"],
            )
            vida_util = st.number_input(
                "Vida útil (meses)", min_value=0, step=1, value=36
            )
            observaciones = st.text_area("Observaciones", height=80)

        st.caption("* Campos obligatorios")

        submit_disabled = ubicacion_seleccionada.get("id_ubicacion") is None
        if submit_disabled:
            st.caption(
                "Selecciona una ubicación válida antes de registrar el equipo."
            )

        submit_pressed = st.form_submit_button(
            "Guardar equipo", disabled=submit_disabled
        )

    if not submit_pressed:
        return

    ubicacion = ubicacion_seleccionada.get("id_ubicacion")
    if ubicacion is None:
        st.error("Debes escoger una ubicación válida.")
        return

    if not codigo or not serie or not tipo or not marca:
        st.error("Por favor completa todos los campos obligatorios.")
        return

    payload = {
        "codigo_inventario": codigo,
        "numero_serie": serie,
        "tipo": tipo,
        "marca": marca,
        "estado": estado,
        "id_ubicacion_actual": int(ubicacion),
        "vida_util_meses": int(vida_util),
        "observaciones": observaciones or None,
    }
    try:
        response = requests.post(f"{BASE_URL}/equipment/", json=payload)
        if response.status_code in (200, 201):
            st.success("Equipo agregado correctamente.")
        else:
            st.error(f"No se pudo agregar el equipo. Código: {response.status_code}")
    except Exception as exc:
        st.error(f"Error de conexión: {exc}")

def _render_detail_tab():
    st.subheader("Detalle e historial del equipo 📚")

    data = _fetch_equipment()
    df_all = pd.DataFrame(data)

    if df_all.empty:
        st.info("No hay equipos registrados para mostrar historial.")
        return

    opciones = (
        df_all.assign(
            etiqueta=lambda d: d["codigo_inventario"]
            + " - "
            + d["tipo"].astype(str)
            + " (ID "
            + d["id_equipo"].astype(str)
            + ")"
        )[["id_equipo", "etiqueta"]]
        .sort_values("etiqueta")
        .values
    )

    etiquetas = [x[1] for x in opciones]
    ids = [x[0] for x in opciones]

    seleccion = st.selectbox(
        "Seleccione un equipo",
        options=range(len(ids)),
        format_func=lambda i: etiquetas[i],
    )
    equipo_id = int(ids[seleccion])

    detalle = _fetch_equipment_detail(equipo_id) or {}
    st.markdown("### 📄 Información general")

    col1, col2, col3 = st.columns(3)
    col1.metric("ID equipo", detalle.get("id_equipo", equipo_id))
    col2.metric("Código inventario", detalle.get("codigo_inventario", "—"))
    col3.metric("Número de serie", detalle.get("numero_serie", "—"))

    col4, col5, col6 = st.columns(3)
    col4.metric("Tipo", detalle.get("tipo", "—"))
    col5.metric("Marca", detalle.get("marca", "—"))
    col6.metric("Estado operativo", detalle.get("estado", "—"))

    st.markdown("**Ubicación física actual**")
    ubicacion_desc = detalle.get("ubicacion_descripcion")
    if ubicacion_desc:
        st.write(ubicacion_desc)
    else:
        st.write("Sin ubicación registrada")

    if detalle.get("observaciones"):
        st.markdown("**Observaciones**")
        st.info(detalle["observaciones"])

    st.markdown("---")

    st.markdown("### 🧾 Historial de compras")
    compras = _fetch_equipment_purchases(equipo_id)
    df_compras = pd.DataFrame(compras)
    if df_compras.empty:
        st.caption("No se encontraron registros de compra para este equipo.")
    else:
        compras_cols = {
            "numero_documento": "Documento",
            "fecha_compra": "Fecha de compra",
            "proveedor": "Proveedor",
            "codigo_contrato": "Contrato",
            "descripcion_contrato": "Descripción contrato",
            "cantidad": "Cantidad",
            "costo_unitario": "Costo unitario",
            "monto_total": "Monto total",
        }
        df_compras_vista = df_compras.rename(
            columns={k: v for k, v in compras_cols.items() if k in df_compras.columns}
        )
        orden = [col for col in compras_cols.values() if col in df_compras_vista.columns]
        st.dataframe(
            df_compras_vista[orden] if orden else df_compras_vista,
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### 📍 Ubicación histórica y movimientos")
    movimientos = _fetch_equipment_movements(equipo_id)
    df_mov = pd.DataFrame(movimientos)

    if df_mov.empty:
        st.caption("No se encontraron movimientos registrados para este equipo.")
    else:
        columnas_posibles = {
            "fecha_movimiento": "Fecha",
            "ubicacion_origen_descripcion": "Ubicación origen",
            "ubicacion_destino_descripcion": "Ubicación destino",
            "tipo_movimiento": "Tipo",
            "observaciones": "Observaciones",
        }
        df_mov_vista = df_mov.rename(
            columns={k: v for k, v in columnas_posibles.items() if k in df_mov.columns}
        )
        orden = [col for col in columnas_posibles.values() if col in df_mov_vista.columns]
        st.dataframe(
            df_mov_vista[orden] if orden else df_mov_vista,
            use_container_width=True,
            hide_index=True,
        )

    st.caption(
        "La sección de historial muestra inventario, compras, asignaciones y movimientos del equipo."
    )

def render():
    st.header("Gestión de Equipos 🛠️")

    tab1, tab2, tab3 = st.tabs(
        ["📋 Listado e inventario", "➕ Agregar equipo", "📚 Detalle e historial"]
    )

    with tab1:
        _render_inventory_tab()
    with tab2:
        _render_create_tab()
    with tab3:
        _render_detail_tab()