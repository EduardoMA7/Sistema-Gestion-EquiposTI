import streamlit as st
import pandas as pd
import requests
import os

BASE_URL = os.getenv("API_GATEWAY_URL")

def _fetch_providers():
    try:
        response = requests.get(f"{BASE_URL}/providers/")
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.error(f"No se pudieron cargar los proveedores: {exc}")
        return []

def _fetch_provider_contracts(provider_id: int):
    try:
        response = requests.get(f"{BASE_URL}/providers/{provider_id}/contracts")
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.warning(f"No se pudieron cargar los contratos: {exc}")
        return []

def _fetch_provider_purchases(provider_id: int):
    try:
        response = requests.get(f"{BASE_URL}/providers/{provider_id}/purchases")
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.warning(f"No se pudieron cargar las compras: {exc}")
        return []

def _render_provider_selector(providers, label: str):
    """Devuelve el dict del proveedor seleccionado o None si no hay."""
    if not providers:
        st.info("Aún no hay proveedores registrados.")
        return None

    options = [
        f"{p.get('razon_social', '—')} ({p.get('ruc', 's/RUC')})"
        for p in providers
    ]
    idx = st.selectbox(label, options=range(len(options)), format_func=lambda i: options[i])
    return providers[idx]

def _render_overview_tab():
    if "purchase_dialog_data" not in st.session_state:
        st.session_state["purchase_dialog_data"] = None

    st.subheader("Proveedores registrados")

    providers = _fetch_providers()
    df = pd.DataFrame(providers)

    if df.empty:
        st.info("No hay proveedores registrados todavía.")
        return

    expected_cols = [
        "id_proveedor",
        "ruc",
        "razon_social",
        "nombre_comercial",
        "direccion",
        "telefono",
        "email",
        "estado",
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    total = len(df)
    activos = int(df["estado"].sum()) if "estado" in df.columns else 0
    inactivos = total - activos

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Total proveedores", total)
    col_m2.metric("Activos", activos)
    col_m3.metric("Inactivos", inactivos)

    st.markdown("---")

    with st.expander("🔍 Filtros de búsqueda", expanded=True):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            solo_activos = st.checkbox("Mostrar solo activos", value=True)
        with col_f2:
            texto_busqueda = st.text_input(
                "Buscar por RUC o razón social",
                placeholder="Ej. 20123456789, Tecnología Global...",
            )

    df_filtrado = df.copy()

    if solo_activos:
        df_filtrado = df_filtrado[df_filtrado["estado"] == True]

    if texto_busqueda:
        mask = (
            df_filtrado["ruc"]
            .astype(str)
            .str.contains(texto_busqueda, case=False, na=False)
            | df_filtrado["razon_social"]
            .astype(str)
            .str.contains(texto_busqueda, case=False, na=False)
        )
        df_filtrado = df_filtrado[mask]

    vista = df_filtrado[
        ["id_proveedor", "ruc", "razon_social", "nombre_comercial", "telefono", "email", "estado"]
    ].rename(
        columns={
            "id_proveedor": "ID",
            "ruc": "RUC",
            "razon_social": "Razón social",
            "nombre_comercial": "Nombre comercial",
            "telefono": "Teléfono",
            "email": "Correo",
            "estado": "Activo",
        }
    )

    st.dataframe(
        vista,
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")
    st.subheader("Detalle e historial de un proveedor")

    selected = _render_provider_selector(providers, "Selecciona un proveedor")
    if not selected:
        return

    provider_id = selected["id_proveedor"]

    st.markdown("### 📌 Información del proveedor")

    c1, c2, c3 = st.columns(3)
    c1.metric("RUC", selected.get("ruc", "—"))
    c2.metric("Razón social", selected.get("razon_social", "—"))
    estado_txt = "Activo" if selected.get("estado", True) else "Inactivo"
    c3.metric("Estado", estado_txt)

    st.markdown("---")

    t_contratos, t_compras = st.tabs(["📄 Contratos", "🧾 Compras"])

    with t_contratos:
        st.markdown("#### Contratos asociados")
        contracts = _fetch_provider_contracts(provider_id)
        df_contracts = pd.DataFrame(contracts)

        if df_contracts.empty:
            st.caption("Este proveedor no tiene contratos registrados.")
        else:
            orden_cols = [
                "id_contrato",
                "codigo_contrato",
                "descripcion",
                "fecha_inicio",
                "fecha_fin",
                "monto_total",
                "tipo_contrato",
                "estado",
            ]
            existentes = [c for c in orden_cols if c in df_contracts.columns]

            df_contracts_vista = df_contracts[existentes].rename(
                columns={
                    "id_contrato": "ID contrato",
                    "codigo_contrato": "Código contrato",
                    "descripcion": "Descripción",
                    "fecha_inicio": "Fecha inicio",
                    "fecha_fin": "Fecha fin",
                    "monto_total": "Monto total",
                    "tipo_contrato": "Tipo de contrato",
                    "estado": "Estado",
                }
            )

            st.dataframe(
                df_contracts_vista,
                use_container_width=True,
                hide_index=True,
            )

    with t_compras:
        st.markdown("#### Historial de compras")

        purchases = _fetch_provider_purchases(provider_id)
        df_purchases = pd.DataFrame(purchases)

        if df_purchases.empty:
            st.caption("Este proveedor no tiene compras registradas.")
        else:
            records = df_purchases.to_dict(orient="records")

            h1, h2, h3, h4, h5 = st.columns([2, 2, 2, 2, 1])
            h1.markdown("**N° documento**")
            h2.markdown("**Fecha de compra**")
            h3.markdown("**Monto total**")
            h4.markdown("**Código contrato**")
            h5.markdown("**Acciones**")

            for compra in records:
                c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1])

                c1.write(compra.get("numero_documento", "—"))
                c2.write(str(compra.get("fecha_compra", "—")))
                monto = compra.get("monto_total", None)
                c3.write(f"S/ {monto:,.2f}" if monto is not None else "—")
                c4.write(compra.get("codigo_contrato", "—"))

                if c5.button("Ver detalles", key=f"btn_compra_{compra['id_compra']}"):

                    @st.dialog("Detalle de compra")
                    def _show_purchase_dialog(
                        compra_dialog=compra, provider_id_local=provider_id
                    ):
                        purchase_id = compra_dialog["id_compra"]

                        try:
                            resp = requests.get(
                                f"{BASE_URL}/providers/{provider_id_local}/purchases/{purchase_id}/details"
                            )
                            resp.raise_for_status()
                            detalles = resp.json()
                            df_det = pd.DataFrame(detalles)

                            if df_det.empty:
                                st.caption("Esta compra no tiene detalles registrados.")
                            else:
                                orden_cols = [
                                    "codigo_inventario",
                                    "numero_serie",
                                    "tipo",
                                    "marca",
                                    "cantidad",
                                    "costo_unitario",
                                    "subtotal",
                                ]
                                existentes = [c for c in orden_cols if c in df_det.columns]

                                df_det_vista = df_det[existentes].rename(
                                    columns={
                                        "codigo_inventario": "Código inventario",
                                        "numero_serie": "N° serie",
                                        "tipo": "Tipo equipo",
                                        "marca": "Marca",
                                        "cantidad": "Cantidad",
                                        "costo_unitario": "Costo unitario",
                                        "subtotal": "Subtotal",
                                    }
                                )

                                st.dataframe(
                                    df_det_vista,
                                    use_container_width=True,
                                    hide_index=True,
                                )
                        except Exception as exc:
                            st.error(f"No se pudieron cargar los detalles de la compra: {exc}")

                    _show_purchase_dialog()


def _render_create_tab():
    st.subheader("Registrar nuevo proveedor")

    with st.form("nuevo_proveedor"):
        col_a, col_b = st.columns(2)

        with col_a:
            ruc = st.text_input("RUC *", max_chars=11, help="11 dígitos")
            razon_social = st.text_input("Razón social *")
            nombre_comercial = st.text_input("Nombre comercial *")
            estado = st.checkbox("Proveedor activo", value=True)

        with col_b:
            direccion = st.text_area("Dirección *", height=100)
            telefono = st.text_input("Teléfono *", max_chars=9)
            email = st.text_input("Correo electrónico *")

        st.caption("* Campos obligatorios")

        if st.form_submit_button("💾 Guardar proveedor"):
            errores = []
            if not ruc or len(ruc) != 11 or not ruc.isdigit():
                errores.append("El RUC debe tener 11 dígitos numéricos.")
            if not razon_social:
                errores.append("La razón social es obligatoria.")
            if not nombre_comercial:
                errores.append("El nombre comercial es obligatorio.")
            if not direccion:
                errores.append("La dirección es obligatoria.")
            if not telefono:
                errores.append("El teléfono es obligatorio.")
            if not email:
                errores.append("El correo electrónico es obligatorio.")

            if errores:
                for e in errores:
                    st.error(e)
                return

            payload = {
                "ruc": ruc,
                "razon_social": razon_social,
                "nombre_comercial": nombre_comercial,
                "direccion": direccion,
                "telefono": telefono,
                "email": email,
                "estado": estado,
            }
            try:
                response = requests.post(f"{BASE_URL}/providers/", json=payload)
                if response.status_code in (200, 201):
                    st.success("✅ Proveedor registrado correctamente.")
                else:
                    st.error(
                        f"No se pudo registrar el proveedor. Código: {response.status_code}"
                    )
            except Exception as exc:
                st.error(f"Error de conexión: {exc}")

def _render_update_tab():
    st.subheader("Actualizar proveedor existente")

    providers = _fetch_providers()
    if not providers:
        st.info("No hay proveedores para actualizar.")
        return

    selected = _render_provider_selector(
        providers, "Selecciona un proveedor a actualizar"
    )
    if not selected:
        return

    with st.form("actualizar_proveedor"):
        col_a, col_b = st.columns(2)

        with col_a:
            ruc = st.text_input(
                "RUC *", value=selected.get("ruc", ""), max_chars=11
            )
            razon_social = st.text_input(
                "Razón social *", value=selected.get("razon_social", "")
            )
            nombre_comercial = st.text_input(
                "Nombre comercial *", value=selected.get("nombre_comercial", "")
            )
            estado = st.checkbox(
                "Proveedor activo", value=selected.get("estado", True)
            )

        with col_b:
            direccion = st.text_area(
                "Dirección *", value=selected.get("direccion", ""), height=100
            )
            telefono = st.text_input(
                "Teléfono *", value=selected.get("telefono", ""), max_chars=9
            )
            email = st.text_input(
                "Correo electrónico *", value=selected.get("email", "")
            )

        st.caption("* Campos obligatorios")

        if st.form_submit_button("💾 Guardar cambios"):
            errores = []
            if not ruc or len(ruc) != 11 or not ruc.isdigit():
                errores.append("El RUC debe tener 11 dígitos numéricos.")
            if not razon_social:
                errores.append("La razón social es obligatoria.")
            if not nombre_comercial:
                errores.append("El nombre comercial es obligatorio.")
            if not direccion:
                errores.append("La dirección es obligatoria.")
            if not telefono:
                errores.append("El teléfono es obligatorio.")
            if not email:
                errores.append("El correo electrónico es obligatorio.")

            if errores:
                for e in errores:
                    st.error(e)
                return

            payload = {
                "ruc": ruc,
                "razon_social": razon_social,
                "nombre_comercial": nombre_comercial,
                "direccion": direccion,
                "telefono": telefono,
                "email": email,
                "estado": estado,
            }
            try:
                response = requests.put(
                    f"{BASE_URL}/providers/{selected['id_proveedor']}",
                    json=payload,
                )
                if response.status_code in (200, 204):
                    st.success("✅ Proveedor actualizado correctamente.")
                else:
                    st.error(
                        f"No se pudo actualizar el proveedor. Código: {response.status_code}"
                    )
            except Exception as exc:
                st.error(f"Error de conexión: {exc}")

def render():
    st.header("Gestión de Proveedores 🤝")

    tab1, tab2, tab3 = st.tabs(
        ["📋 Proveedores e historial", "➕ Nuevo proveedor", "✏️ Actualizar proveedor"]
    )

    with tab1:
        _render_overview_tab()
    with tab2:
        _render_create_tab()
    with tab3:
        _render_update_tab()