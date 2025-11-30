import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from typing import Optional, Dict, Any
import os

BASE_URL = os.getenv("API_GATEWAY_URL")

@st.cache_data(ttl=3600)
def _get_report_data(endpoint: str, params: Optional[Dict[str, Any]] = None):
    """Helper genérico para consumir los endpoints de reportes."""
    try:
        url = f"{BASE_URL}/reports/{endpoint}"
        resp = requests.get(url, params=params or {})
        resp.raise_for_status()
        data = resp.json()
        return data
    except Exception as exc:
        st.error(f"No se pudo obtener datos del endpoint '{endpoint}': {exc}")
        return []

def _render_dashboard_tab():
    st.subheader("📊 Dashboard de análisis")

    col_top1, col_top2 = st.columns(2)

    with col_top1:
        st.markdown("### Estado de los equipos")
        status_data = _get_report_data("equipment-status")
        df_status = pd.DataFrame(status_data)

        if not df_status.empty:
            total_equipos = df_status["count"].sum()
            operativos = df_status.loc[
                df_status["status"].str.lower().str.contains("operativo", na=False),
                "count",
            ].sum()
            porc_operativo = (operativos / total_equipos * 100) if total_equipos else 0

            m1, m2 = st.columns(2)
            m1.metric("Total equipos", int(total_equipos))
            m2.metric("% operativos", f"{porc_operativo:,.1f}%")

            fig_status = px.pie(
                df_status,
                values="count",
                names="status",
                title="Distribución de equipos por estado",
            )
            st.plotly_chart(fig_status, use_container_width=True)
        else:
            st.info("No hay datos de estado de equipos disponibles.")

    with col_top2:
        st.markdown("### Costos de mantenimiento (últimos meses)")

        months = st.slider(
            "Rango de meses para análisis", min_value=3, max_value=24, value=12, step=3
        )
        cost_data = _get_report_data("maintenance-costs", params={"months": months})
        df_costs = pd.DataFrame(cost_data)

        if not df_costs.empty:
            df_costs["total_cost"] = df_costs["total_cost"].fillna(0.0)
            total_cost = df_costs["total_cost"].sum()
            total_mants = df_costs["maintenance_count"].sum()

            m3, m4 = st.columns(2)
            m3.metric("Costo total", f"S/ {total_cost:,.2f}")
            m4.metric("Mantenimientos", int(total_mants))

            fig_costs = px.bar(
                df_costs,
                x="month",
                y="total_cost",
                title="Costos de mantenimiento por mes",
                labels={"total_cost": "Costo total", "month": "Mes"},
            )
            st.plotly_chart(fig_costs, use_container_width=True)
        else:
            st.info("No hay datos de costos de mantenimiento disponibles.")

    st.markdown("---")

    st.markdown("### Equipos por ubicación")
    location_data = _get_report_data("equipment-by-location")
    df_locations = pd.DataFrame(location_data)

    if not df_locations.empty:
        fig_locations = px.bar(
            df_locations,
            x="ubicacion",
            y="count",
            title="Distribución de equipos por ubicación",
            labels={"count": "Cantidad de equipos", "ubicacion": "Ubicación"},
        )
        st.plotly_chart(fig_locations, use_container_width=True)
    else:
        st.info("No hay datos de equipos por ubicación disponibles.")

    st.markdown("---")

    cols_mid = st.columns(2)

    with cols_mid[0]:
        st.markdown("### Mantenimientos por tipo")
        type_data = _get_report_data("maintenance-by-type")
        df_type = pd.DataFrame(type_data)

        if not df_type.empty:
            df_type["total_cost"] = df_type["total_cost"].fillna(0.0)
            fig_type = px.bar(
                df_type,
                x="tipo_mantenimiento",
                y="count",
                title="Cantidad de mantenimientos por tipo",
                labels={"tipo_mantenimiento": "Tipo", "count": "Cantidad"},
            )
            st.plotly_chart(fig_type, use_container_width=True)

            fig_type_cost = px.pie(
                df_type,
                values="total_cost",
                names="tipo_mantenimiento",
                title="Distribución de costos por tipo de mantenimiento",
            )
            st.plotly_chart(fig_type_cost, use_container_width=True)
        else:
            st.info("No hay datos de mantenimientos por tipo.")

    with cols_mid[1]:
        st.markdown("### Antigüedad de equipos")
        aging_data = _get_report_data("equipment-aging")
        df_aging = pd.DataFrame(aging_data)

        if not df_aging.empty:
            fig_aging = px.bar(
                df_aging,
                x="age_group",
                y="count",
                title="Equipos por rango de antigüedad",
                labels={"age_group": "Rango", "count": "Cantidad"},
            )
            st.plotly_chart(fig_aging, use_container_width=True)
        else:
            st.info("No hay datos de antigüedad de equipos.")

    st.markdown("---")
    st.caption(
        "Los datos se actualizan desde el microservicio de reportes. "
        "Los resultados se cachean por 1 hora para mejorar el rendimiento."
    )


def _render_export_tab():
    st.subheader("📤 Exportación de reportes")

    st.markdown(
        "Desde aquí puedes generar un paquete de reportes consolidado "
        "en **Excel** o **PDF**."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📑 Exportar a Excel")
        st.write(
            "Genera un archivo Excel con hojas para:\n"
            "- Estado de equipos\n"
            "- Costos de mantenimiento\n"
            "- Equipos por ubicación\n"
            "- Mantenimientos por tipo\n"
            "- Antigüedad de equipos"
        )

        if st.button("Generar Excel"):
            try:
                resp = requests.get(f"{BASE_URL}/reports/export/excel")
                resp.raise_for_status()
                st.download_button(
                    label="⬇️ Descargar Excel",
                    data=resp.content,
                    file_name="reportes_de_equipos.xlsx",
                    mime=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                )
            except Exception as exc:
                st.error(f"Error al exportar el reporte a Excel: {exc}")

    with col2:
        st.markdown("### 🧾 Exportar a PDF")
        st.write(
            "Genera un reporte PDF con tablas para:\n"
            "- Estado del equipo\n"
            "- Costos de mantenimiento (12 meses)\n"
            "- Equipos por ubicación\n"
            "- Mantenimientos por tipo\n"
            "- Antigüedad del equipo"
        )

        if st.button("Generar PDF"):
            try:
                resp = requests.get(f"{BASE_URL}/reports/export/pdf")
                resp.raise_for_status()
                st.download_button(
                    label="⬇️ Descargar PDF",
                    data=resp.content,
                    file_name="reportes_de_equipos.pdf",
                    mime="application/pdf",
                )
            except Exception as exc:
                st.error(f"Error al exportar el reporte a PDF: {exc}")

def render():
    st.header("Reportes y análisis 📈")

    tab1, tab2 = st.tabs(["📊 Dashboard", "📤 Exportación"])

    with tab1:
        _render_dashboard_tab()
    with tab2:
        _render_export_tab()