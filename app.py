import streamlit as st
import pandas as pd
import os
from datetime import date

# 页面配置
st.set_page_config(page_title="Panel Países & Productos", layout="wide")

# ==================== 数据初始化与保存逻辑 ====================
FILES = {
    "paises": "paises.csv",
    "productos": "productos.csv",
    "prioridad": "prioridad.csv"
}

def save_to_csv(df, key):
    """将修改后的数据保存回CSV文件，并更新Session State"""
    # 创建一个副本来保存，防止污染内存中的日期对象
    df_save = df.copy()
    
    # 【修复】保存 Productos 时，强制把日期转回你习惯的 DD/MM/YYYY 字符串格式
    if key == "productos":
        for col in ['Actualización Completo', 'Actualización regla']:
            if col in df_save.columns:
                df_save[col] = pd.to_datetime(df_save[col], errors='coerce').dt.strftime('%d/%m/%Y').fillna("")
                
    df_save.to_csv(FILES[key], index=False)
    st.session_state[f"df_{key}"] = df

def init_data():
    """首次加载数据并存入内存 (Session State)"""
    for key, path in FILES.items():
        if f"df_{key}" not in st.session_state:
            if os.path.exists(path):
                df = pd.read_csv(path)
                
                # 【修复】智能处理日期格式，兼容原版和Pandas保存后的版本
                if key == "productos":
                    for col in ['Actualización Completo', 'Actualización regla']:
                        if col in df.columns:
                            # dayfirst=True 允许解析 DD/MM/YYYY
                            temp_dates = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
                            # 必须将 NaT(空时间) 替换为 None，否则 Streamlit 日历控件会显示空白错误
                            df[col] = [d.date() if pd.notnull(d) else None for d in temp_dates]
                            
                st.session_state[f"df_{key}"] = df
            else:
                st.error(f"⚠️ No se encontró el archivo: {path}. Por favor revisa el nombre.")

init_data()

def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

# 左侧导航栏 (Sidebar)
st.sidebar.title("Mi panel")
view = st.sidebar.radio("Menú", ["Países", "Productos", "Prioridad", "Resumen", "Vista Maestra (3 en 1)"])

# ==================== 视图 1: PAÍSES ====================
if view == "Países":
    st.title("Países")
    st.info("💡 Haz doble clic en la columna 'Estado' para elegir opciones de la lista desplegable.")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        estado_filter = st.selectbox("Filtro Estado:", ["Todos", "Activo", "Inactivo", "No implementado"])
    
    df_paises = st.session_state["df_paises"]
    filtered_df = df_paises.copy()
    
    if estado_filter != "Todos":
        filtered_df = filtered_df[filtered_df['Estado'] == estado_filter]
        
    with col2:
        st.write("")
        st.write("")
        st.download_button(label="Exportar a CSV", data=convert_df(filtered_df), file_name='paises_export.csv', mime='text/csv')
    
    edited_df = st.data_editor(
        filtered_df, 
        use_container_width=True, 
        hide_index=True,
        num_rows="dynamic" if estado_filter == "Todos" else "fixed",
        column_config={
            "Estado": st.column_config.SelectboxColumn(
                "Estado",
                help="Selecciona el estado del país",
                options=["Activo", "Inactivo", "No implementado"], 
                required=True
            )
        }
    )
    
    if not edited_df.equals(filtered_df):
        if estado_filter == "Todos":
            df_paises = edited_df
        else:
            df_paises.update(edited_df)
        save_to_csv(df_paises, "paises")
        st.success("¡Cambios guardados!")
        st.rerun()

# ==================== 视图 2: PRODUCTOS ====================
elif view == "Productos":
    st.title("Productos")
    
    col1, col2, col3, col4 = st.columns([2, 3, 3, 2])
    with col1:
        estado_filter = st.selectbox("Filtro Estado:", ["Todos", "Activo", "Inactivo"])
    with col2:
        comp_dates = st.date_input("Actualización Completo (Rango)", value=None)
    with col3:
        reg_dates = st.date_input("Actualización regla (Rango)", value=None)
        
    df_productos = st.session_state["df_productos"]
    filtered_df = df_productos.copy()
    
    if estado_filter != "Todos":
        filtered_df = filtered_df[filtered_df['Estado'] == filter]
    
    # 【修复】安全的时间过滤方式，忽略为空(None)的日期
    if comp_dates and len(comp_dates) == 2:
        mask = filtered_df['Actualización Completo'].apply(
            lambda d: comp_dates[0] <= d <= comp_dates[1] if d is not None else False
        )
        filtered_df = filtered_df[mask]
                                  
    if reg_dates and len(reg_dates) == 2:
        mask = filtered_df['Actualización regla'].apply(
            lambda d: reg_dates[0] <= d <= reg_dates[1] if d is not None else False
        )
        filtered_df = filtered_df[mask]

    with col4:
        st.write("")
        st.write("")
        st.download_button(label="Exportar a CSV", data=convert_df(filtered_df), file_name='productos_export.csv', mime='text/csv')

    edited_df = st.data_editor(
        filtered_df, 
        use_container_width=True, 
        hide_index=True,
        num_rows="dynamic" if estado_filter == "Todos" else "fixed",
        column_config={
            "Estado": st.column_config.SelectboxColumn(
                "Estado",
                help="Selecciona el estado del producto",
                options=["Activo", "Inactivo"],
                required=True
            ),
            # 日期控件配置不变，现在它可以正确获取到真正的日期对象了
            "Actualización Completo": st.column_config.DateColumn(
                "Actualización Completo",
                format="DD/MM/YYYY"
            ),
            "Actualización regla": st.column_config.DateColumn(
                "Actualización regla",
                format="DD/MM/YYYY"
            )
        }
    )

    if not edited_df.equals(filtered_df):
        if estado_filter == "Todos" and not comp_dates and not reg_dates:
            df_productos = edited_df
        else:
            df_productos.update(edited_df)
        save_to_csv(df_productos, "productos")
        st.success("¡Cambios guardados!")
        st.rerun()

# ==================== 视图 3: PRIORIDAD ====================
elif view == "Prioridad":
    st.title("Prioridad (mantenimiento)")
    
    col1, col2, col3 = st.columns([2, 3, 2])
    with col1:
        estado_filter = st.selectbox("Filtro Estado país:", ["Todos", "Activo", "Inactivo", "No implementado"])
    with col2:
        search_query = st.text_input("Búsqueda (País o ISO3):", placeholder="Ej: Sri Lanka o LKA")
        
    st.markdown("##### Pesos (suman 1 idealmente)")
    w_col1, w_col2, w_col3, w_col4, w_col5 = st.columns(5)
    w_c1 = w_col1.number_input("Clientes (C1)", value=0.45, step=0.05)
    w_c2 = w_col2.number_input("Productos (C2)", value=0.15, step=0.05)
    w_c3 = w_col3.number_input("Complejidad (C3)", value=0.25, step=0.05)
    w_c4 = w_col4.number_input("Recencia (C4)", value=0.15, step=0.05)
    recency_window = w_col5.number_input("Ventana recencia (días)", value=180, step=1)
    
    df_prioridad = st.session_state["df_prioridad"]
    filtered_df = df_prioridad.copy()
    
    if estado_filter != "Todos":
        filtered_df = filtered_df[filtered_df['estado_pais'] == estado_filter]
        
    if search_query:
        query = search_query.lower()
        filtered_df = filtered_df[
            filtered_df['country'].str.lower().str.contains(query, na=False) |
            filtered_df['iso3'].str.lower().str.contains(query, na=False)
        ]
    
    filtered_df['clientes365'] = pd.to_numeric(filtered_df['clientes365'], errors='coerce').fillna(0)
    filtered_df['productos_activos'] = pd.to_numeric(filtered_df['productos_activos'], errors='coerce').fillna(0)
    filtered_df['complejidadScore'] = pd.to_numeric(filtered_df['complejidadScore'], errors='coerce').fillna(0)
    filtered_df['daysSince'] = pd.to_numeric(filtered_df['daysSince'], errors='coerce').fillna(0)

    score01 = (
        (filtered_df['clientes365'] * w_c1) + 
        (filtered_df['productos_activos'] * w_c2) + 
        (filtered_df['complejidadScore'] * w_c3) - 
        (filtered_df['daysSince'] / recency_window * w_c4)
    )
    
    filtered_df['score100'] = (score01 * 100).round()

    def assign_nivel(score):
        if score >= 80: return "P0"
        elif score >= 60: return "P1"
        elif score >= 40: return "P2"
        else: return "P3"

    filtered_df['nivel'] = filtered_df['score100'].apply(assign_nivel)
    filtered_df = filtered_df.sort_values(by="score100", ascending=False)
    
    with col3:
        st.write("")
        st.write("")
        st.download_button(label="Exportar prioridad (CSV)", data=convert_df(filtered_df), file_name='prioridad_export.csv', mime='text/csv')

    edited_df = st.data_editor(
        filtered_df, 
        use_container_width=True, 
        hide_index=True,
        disabled=["score100", "nivel"], 
        num_rows="dynamic" if estado_filter == "Todos" and not search_query else "fixed",
        column_config={
            "estado_pais": st.column_config.SelectboxColumn(
                "Estado País",
                options=["Activo", "Inactivo", "No implementado"],
                required=True
            )
        }
    )

    if not edited_df.equals(filtered_df):
        clean_edited = edited_df.drop(columns=["score100", "nivel"], errors='ignore')
        if estado_filter == "Todos" and not search_query:
            df_prioridad = clean_edited
        else:
            df_prioridad.update(clean_edited)
        save_to_csv(df_prioridad, "prioridad")
        st.success("¡Métricas actualizadas!")
        st.rerun()

# ==================== 视图 4: RESUMEN ====================
elif view == "Resumen":
    st.title("Resumen del Panel")

    df_paises = st.session_state["df_paises"]
    df_productos = st.session_state["df_productos"]
    df_prioridad = st.session_state["df_prioridad"]

    total_paises = len(df_paises)
    paises_activos = len(df_paises[df_paises['Estado'] == 'Activo'])
    total_productos = len(df_productos)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Países", total_paises)
    col2.metric("Países Activos", paises_activos)
    col3.metric("Total Productos", total_productos)

    st.divider()

    st.subheader("📊 Distribución por Estado")
    status_counts = df_paises['Estado'].value_counts()
    st.bar_chart(status_counts)

    st.subheader("🎯 Resumen de Prioridad")
    w_c1, w_c2, w_c3, w_c4, recency_window = 0.45, 0.15, 0.25, 0.15, 180
    
    calc_df = df_prioridad.copy()
    calc_df['clientes365'] = pd.to_numeric(calc_df['clientes365'], errors='coerce').fillna(0)
    calc_df['productos_activos'] = pd.to_numeric(calc_df['productos_activos'], errors='coerce').fillna(0)
    calc_df['complejidadScore'] = pd.to_numeric(calc_df['complejidadScore'], errors='coerce').fillna(0)
    calc_df['daysSince'] = pd.to_numeric(calc_df['daysSince'], errors='coerce').fillna(0)

    score01 = (calc_df['clientes365'] * w_c1) + (calc_df['productos_activos'] * w_c2) + \
              (calc_df['complejidadScore'] * w_c3) - (calc_df['daysSince'] / recency_window * w_c4)
    calc_df['score100'] = (score01 * 100).round()

    def assign_nivel(score):
        if score >= 80: return "P0"
        elif score >= 60: return "P1"
        elif score >= 40: return "P2"
        else: return "P3"

    calc_df['nivel'] = calc_df['score100'].apply(assign_nivel)
    nivel_counts = calc_df['nivel'].value_counts().reindex(["P0", "P1", "P2", "P3"], fill_value=0)
    
    n1, n2, n3, n4 = st.columns(4)
    n1.metric("P0 (Alta)", nivel_counts["P0"])
    n2.metric("P1", nivel_counts["P1"])
    n3.metric("P2", nivel_counts["P2"])
    n4.metric("P3 (Baja)", nivel_counts["P3"])

    st.subheader("🔥 Top 10 Países Prioritarios (P0/P1)")
    top_paises = calc_df[calc_df['nivel'].isin(["P0", "P1"])].sort_values(by="score100", ascending=False).head(10)
    
    if not top_paises.empty:
        st.dataframe(top_paises[['country', 'iso3', 'score100', 'nivel']], use_container_width=True, hide_index=True)
    else:
        st.info("No hay países en niveles P0 o P1 con los pesos actuales.")

# ==================== 视图 5: VISTA MAESTRA (3 EN 1) ====================
elif view == "Vista Maestra (3 en 1)":
    st.title("Vista Maestra: Países, Prioridad y Productos")
    st.write("Esta tabla combina la información base, las métricas de prioridad y el listado de productos.")
    
    # 获取最新的内存数据（这样你在其他页面修改了状态或分数，这里会实时体现）
    df_paises = st.session_state["df_paises"]
    df_productos = st.session_state["df_productos"]
    df_prioridad = st.session_state["df_prioridad"]
    
    # 提取优先级表的核心列
    # 注意：这里的列名要根据你 df_prioridad 实际存在的列名来定
    # 如果你在之前的编辑代码里生成了 nivel 和 score100，这里就能直接用
    cols_prio = ['country', 'clientes365', 'complejidadScore', 'daysSince']
    if 'score100' in df_prioridad.columns: cols_prio.append('score100')
    if 'nivel' in df_prioridad.columns: cols_prio.append('nivel')
        
    df_prio_clean = df_prioridad[cols_prio]
    
    # 第一步：合并国家和优先级
    df_step1 = pd.merge(df_paises, df_prio_clean, left_on='País', right_on='country', how='left')
    if 'country' in df_step1.columns:
        df_step1 = df_step1.drop(columns=['country'])
        
    # 第二步：合并产品
    df_master = pd.merge(df_step1, df_productos, on='País', how='inner', suffixes=('_País', '_Producto'))
    
    # 清理多余的列
    if 'ISO3_Producto' in df_master.columns:
        df_master = df_master.drop(columns=['ISO3_Producto'])
    df_master = df_master.rename(columns={'ISO3_País': 'ISO3'})
    
    # 下载按钮
    st.download_button(
        label="Descargar Tabla Maestra (CSV)", 
        data=convert_df(df_master), 
        file_name='master_data_fusion.csv', 
        mime='text/csv'
    )
    
    # 在界面上展示
    st.dataframe(df_master, use_container_width=True, hide_index=True)
