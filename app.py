import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Configuración de la página
st.set_page_config(page_title="Panel de Control v2", layout="wide")

# Carga de datos[cite: 1]
@st.cache_data
def load_data():
    file_name = 'Merged_Countries_Vista-v2.xlsx'
    try:
        df = pd.read_excel(file_name)
    except FileNotFoundError:
        st.error(f"❌ No se encontró el archivo: {file_name}")
        st.stop()
    
    # Conversión forzada de fechas[cite: 2]
    date_cols = ['Actualización Completo', 'Actualización regla']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Limpieza de datos[cite: 1]
    df['País'] = df['País'].astype(str).str.strip()
    df['Producto'] = df['Producto'].astype(str).str.strip()
    
    # Unificar estados: Activo, Inactivo, No implementado[cite: 2]
    status_map = {'nan': 'No implementado', 'Sin Estado': 'No implementado', 'None': 'No implementado'}
    valid_options = ["Activo", "Inactivo", "No implementado"]
    
    for col in ['Estado_País', 'Estado_Producto']:
        df[col] = df[col].astype(str).str.strip().replace(status_map).fillna('No implementado')
        df[col] = df[col].apply(lambda x: x if x in valid_options else "No implementado")
    
    return df

# Inicialización del Session State[cite: 2]
if 'df' not in st.session_state:
    st.session_state.df = load_data()

valid_status = ["Activo", "Inactivo", "No implementado"]

# Función para formatear fechas[cite: 2]
def get_display_df(df_input):
    display_df = df_input.copy()
    for col in ['Actualización Completo', 'Actualización regla']:
        if col in display_df.columns:
            display_df[col] = display_df[col].dt.strftime('%d-%m-%Y').fillna("")
    return display_df

# Menú lateral
menu = st.sidebar.radio("Menú", ["Países", "Productos", "Resumen", "Prioridad"])

# --- 1. Página de Países ---
if menu == "Países":
    # Título y botón de guardado en la parte superior derecha[cite: 2]
    head_col1, head_col2 = st.columns([0.85, 0.15])
    with head_col1:
        st.title("🌍 Países - Estadísticas por Nación")
    
    # Resumen de datos por país
    stats = st.session_state.df.groupby(['País', 'ISO3']).apply(lambda x: pd.Series({
        'Estado_País': x['Estado_País'].iloc[0],
        'Activos': ((x['Estado_Producto'] == 'Activo') & (x['Producto'].notna())).sum(),
        'Inactivos': ((x['Estado_Producto'] == 'Inactivo') & (x['Producto'].notna())).sum()
    })).reset_index()

    # Filtros
    all_countries = sorted([c for c in st.session_state.df['País'].unique() if c.lower() != 'nan'])
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_countries = st.multiselect("Seleccionar País", options=all_countries)
    with col_f2:
        status_filter = st.multiselect("Filtrar por Estado de País", options=valid_status)

    if selected_countries:
        stats = stats[stats['País'].isin(selected_countries)]
    if status_filter:
        stats = stats[stats['Estado_País'].isin(status_filter)]

    with head_col2:
        st.write(" ") 
        if st.button("💾 Guardar Cambios"):
            st.session_state.trigger_save_paises = True

    # Editor de datos
    edited_paises = st.data_editor(
        stats,
        column_config={
            "Estado_País": st.column_config.SelectboxColumn("Estado País", options=valid_status, required=True),
            "País": st.column_config.Column(disabled=True),
            "ISO3": st.column_config.Column(disabled=True),
            "Activos": st.column_config.Column(disabled=True),
            "Inactivos": st.column_config.Column(disabled=True),
        },
        use_container_width=True, hide_index=True, height=800
    )

    if st.session_state.get('trigger_save_paises'):
        for _, row in edited_paises.iterrows():
            st.session_state.df.loc[st.session_state.df['País'] == row['País'], 'Estado_País'] = row['Estado_País']
        st.success("¡Estados de país guardados exitosamente!")
        del st.session_state.trigger_save_paises

# --- 2. Página de Productos ---
elif menu == "Productos":
    head_col1, head_col2 = st.columns([0.85, 0.15])
    with head_col1:
        st.title("📦 Productos - Detalles por Producto")
    
    with head_col2:
        st.write(" ") 
        if st.button("💾 Guardar Cambios"):
            st.session_state.trigger_save_prod = True

    # Filtrado base[cite: 2]
    df_prod = st.session_state.df[st.session_state.df['Producto'].notna() & (st.session_state.df['Producto'] != 'nan')].copy()
    
    # Filtros
    c1, c2, c3 = st.columns(3)
    with c1:
        f_country = st.multiselect("Filtrar por País", options=sorted(df_prod['País'].unique()))
    with c2:
        f_p_status = st.multiselect("Filtrar por Estado de Producto", options=valid_status)
    with c3:
        f_c_status = st.multiselect("Filtrar por Estado de País", options=valid_status)
    
    if f_country: df_prod = df_prod[df_prod['País'].isin(f_country)]
    if f_p_status: df_prod = df_prod[df_prod['Estado_Producto'].isin(f_p_status)]
    if f_c_status: df_prod = df_prod[df_prod['Estado_País'].isin(f_c_status)]

    # Mostrar columnas específicas y formatear fechas[cite: 2]
    display_cols = ['País', 'Estado_País', 'Producto', 'Estado_Producto', 
                    'Actualización Completo', 'Actualización regla', 'Nota_Producto']
    df_for_edit = get_display_df(df_prod[display_cols])
    
    edited_prod = st.data_editor(
        df_for_edit,
        column_config={
            "Estado_Producto": st.column_config.SelectboxColumn("Estado Producto", options=valid_status, required=True),
            "Estado_País": st.column_config.Column("Estado País (Bloqueado)", disabled=True), 
            "País": st.column_config.Column(disabled=True),
            "Producto": st.column_config.Column(disabled=True),
            "Actualización Completo": st.column_config.Column(disabled=True),
            "Actualización regla": st.column_config.Column(disabled=True),
            "Nota_Producto": st.column_config.Column(disabled=True),
        },
        use_container_width=True, hide_index=True, height=1000
    )

    if st.session_state.get('trigger_save_prod'):
        for _, row in edited_prod.iterrows():
            mask = (st.session_state.df['Producto'] == row['Producto']) & (st.session_state.df['País'] == row['País'])
            st.session_state.df.loc[mask, 'Estado_Producto'] = row['Estado_Producto']
        st.success("¡Estados de producto guardados exitosamente!")
        del st.session_state.trigger_save_prod

# --- 3. Página de Resumen ---
elif menu == "Resumen":
    st.title("📊 Resumen - Alertas de Actualización")
    df_res = st.session_state.df[st.session_state.df['Producto'].notna() & (st.session_state.df['Producto'] != 'nan')].copy()
    limit_date = datetime.now() - timedelta(days=180)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("⚠️ Regla Vencida (> 6 meses)")
        r_df = df_res[(df_res['Actualización regla'] < limit_date) | (df_res['Actualización regla'].isna())]
        st.dataframe(get_display_df(r_df)[['Producto', 'País', 'Actualización regla']], use_container_width=True, hide_index=True)
    with col2:
        st.subheader("⚠️ Completo Vencido (> 6 meses)")
        c_df = df_res[(df_res['Actualización Completo'] < limit_date) | (df_res['Actualización Completo'].isna())]
        st.dataframe(get_display_df(c_df)[['Producto', 'País', 'Actualización Completo']], use_container_width=True, hide_index=True)

# --- 4. Página de Prioridad ---
elif menu == "Prioridad":
    st.title("⚡ Prioridad")
    st.info("Este módulo aún no ha sido publicado.")
