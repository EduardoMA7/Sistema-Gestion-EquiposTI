import streamlit as st
from streamlit_option_menu import option_menu 
from views import equipos, mantenimiento, proveedores, reportes

st.set_page_config(
    page_title="Sistema de Gestión de Equipos de TI",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main {
        padding: 2rem;
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    selected = option_menu(
        "Menú Principal",
        ["Inicio", "Equipos", "Proveedores", "Mantenimiento", "Reportes"],
        icons=["house", "pc", "truck", "tools", "bar-chart"],
        menu_icon="cast", 
        default_index=0,
    )

st.title("Sistema de Gestión de Equipos de TI")

if selected == "Inicio":
    st.markdown(
        """
    ## Bienvenido al Sistema de Gestión de Equipos de TI

    Este sistema le permite gestionar los equipos de TI de la institución, incluyendo:

    - 🧾 **Inventario de equipos**
    - 🤝 **Gestión de proveedores**
    - 🛠️ **Control de mantenimiento**
    - 📊 **Reportes y análisis**

    Utilice el menú lateral para navegar entre las secciones.
    """
    )

elif selected == "Equipos":
    equipos.render()
elif selected == "Proveedores":
    proveedores.render()
elif selected == "Mantenimiento":
    mantenimiento.render()
elif selected == "Reportes":
    reportes.render()