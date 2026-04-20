import streamlit as st
import pandas as pd
from datetime import date

# 页面配置
st.set_page_config(page_title="Panel Países & Productos", layout="wide")

# 加载并缓存数据
@st.cache_data
def load_data():
    # 注意：确保这里的文件名与您上传至GitHub的文件名一致
    df_paises = pd.read_csv('paises.csv')
    df_productos = pd.read_csv('productos.csv')
    df_prioridad = pd.read_csv('prioridad.csv')
    
    # 将日期列转换为 datetime 格式以便进行时间段过滤
    # 日期格式似乎为 dd/mm/yyyy，errors='coerce' 会把空值或错误值变成 NaT
    df_productos['Actualización Completo'] = pd.to_datetime(df_productos['Actualización Completo'], format='%d/%m/%Y', errors='coerce')
    df_productos['Actualización regla'] = pd.to_datetime(df_productos['Actualización regla'], format='%d/%m/%Y', errors='coerce')
    
    return df_paises, df_productos, df_prioridad

df_paises, df_productos, df_prioridad = load_data()

# 将 DataFrame 转换为 CSV 格式以下载
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

# 左侧导航栏 (Sidebar)
st.sidebar.title("Mi panel")
view = st.sidebar.radio("Menú", ["Países", "Productos", "Prioridad", "Resumen"])

# ==================== 视图 1: PAÍSES ====================
if view == "Países":
    st.title("Países")
    
    # 顶部工具栏
    col1, col2 = st.columns([1, 4])
    with col1:
        estado_filter = st.selectbox("Estado:", ["Todos", "Activo", "Inactivo", "No implementado"])
    
    # 过滤逻辑
    filtered_df = df_paises.copy()
    if estado_filter != "Todos":
        filtered_df = filtered_df[filtered_df['Estado'] == estado_filter]
        
    with col2:
        st.write("") # 占位
        st.write("")
        st.download_button(label="Exportar a CSV", data=convert_df(filtered_df), file_name='paises_export.csv', mime='text/csv')
    
    # 显示表格 (Streamlit 表头自带排序功能)
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

# ==================== 视图 2: PRODUCTOS ====================
elif view == "Productos":
    st.title("Productos")
    
    col1, col2, col3, col4 = st.columns([2, 3, 3, 2])
    
    with col1:
        estado_filter = st.selectbox("Estado:", ["Todos", "Activo", "Inactivo"])
        
    with col2:
        comp_dates = st.date_input("Actualización Completo (Rango)", value=None)
        
    with col3:
        reg_dates = st.date_input("Actualización regla (Rango)", value=None)
        
    # 过滤逻辑
    filtered_df = df_productos.copy()
    
    if estado_filter != "Todos":
        filtered_df = filtered_df[filtered_df['Estado'] == estado_filter]
        
    # 时间范围过滤
    if comp_dates and len(comp_dates) == 2:
        start_date, end_date = comp_dates
        filtered_df = filtered_df[(filtered_df['Actualización Completo'].dt.date >= start_date) & 
                                  (filtered_df['Actualización Completo'].dt.date <= end_date)]
                                  
    if reg_dates and len(reg_dates) == 2:
        start_date, end_date = reg_dates
        filtered_df = filtered_df[(filtered_df['Actualización regla'].dt.date >= start_date) & 
                                  (filtered_df['Actualización regla'].dt.date <= end_date)]
    
    # 恢复日期格式以便于阅读
    filtered_df['Actualización Completo'] = filtered_df['Actualización Completo'].dt.strftime('%d/%m/%Y')
    filtered_df['Actualización regla'] = filtered_df['Actualización regla'].dt.strftime('%d/%m/%Y')

    with col4:
        st.write("")
        st.write("")
        st.download_button(label="Exportar a CSV", data=convert_df(filtered_df), file_name='productos_export.csv', mime='text/csv')

    # Streamlit 自带点击列名即可排序的功能
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

# ==================== 视图 3: PRIORIDAD ====================
elif view == "Prioridad":
    st.title("Prioridad (mantenimiento)")
    
    # 上半部分：筛选器与搜索
    col1, col2, col3 = st.columns([2, 3, 2])
    with col1:
        estado_filter = st.selectbox("Estado país:", ["Todos", "Activo", "Inactivo", "No implementado"])
    with col2:
        search_query = st.text_input("Búsqueda (País o ISO3):", placeholder="Ej: Sri Lanka o LKA")
        
    # 下半部分：权重调整器
    st.markdown("##### Pesos (suman 1 idealmente)")
    w_col1, w_col2, w_col3, w_col4, w_col5 = st.columns(5)
    w_c1 = w_col1.number_input("Clientes (C1)", value=0.45, step=0.05)
    w_c2 = w_col2.number_input("Productos (C2)", value=0.15, step=0.05)
    w_c3 = w_col3.number_input("Complejidad (C3)", value=0.25, step=0.05)
    w_c4 = w_col4.number_input("Recencia (C4)", value=0.15, step=0.05)
    recency_window = w_col5.number_input("Ventana recencia (días)", value=180, step=1)
    
    filtered_df = df_prioridad.copy()
    
    # 应用状态筛选
    if estado_filter != "Todos":
        filtered_df = filtered_df[filtered_df['estado_pais'] == estado_filter]
        
    # 应用文字搜索
    if search_query:
        query = search_query.lower()
        filtered_df = filtered_df[
            filtered_df['country'].str.lower().str.contains(query, na=False) |
            filtered_df['iso3'].str.lower().str.contains(query, na=False)
        ]
    
  # 动态计算逻辑 (清理数据为数值格式)
    filtered_df['clientes365'] = pd.to_numeric(filtered_df['clientes365'], errors='coerce').fillna(0)
    filtered_df['productos_activos'] = pd.to_numeric(filtered_df['productos_activos'], errors='coerce').fillna(0)
    filtered_df['complejidadScore'] = pd.to_numeric(filtered_df['complejidadScore'], errors='coerce').fillna(0)
    filtered_df['daysSince'] = pd.to_numeric(filtered_df['daysSince'], errors='coerce').fillna(0)

    # 1. 计算基础分 (对应 HTML 中的 score01)
    # 注意：为了让结果在 0-1 之间，您可以根据实际的数据规模对各列进行归一化。
    # 这里直接套用 JS 中的公式结构：(w1*n1) + (w2*n2) + (w3*n3) - (w4*n4)
    score01 = (
        (filtered_df['clientes365'] * w_c1) + 
        (filtered_df['productos_activos'] * w_c2) + 
        (filtered_df['complejidadScore'] * w_c3) - 
        (filtered_df['daysSince'] / recency_window * w_c4)
    )
    
    # 2. 转换为 100 分制并四舍五入 (对应 HTML 中的 score100)
    filtered_df['score100'] = (score01 * 100).round()

    # 3. 添加分级规则函数 (Nivel)
    def assign_nivel(score):
        if score >= 80:
            return "P0"
        elif score >= 60:
            return "P1"
        elif score >= 40:
            return "P2"
        else:
            return "P3"

    # 应用分级规则
    filtered_df['nivel'] = filtered_df['score100'].apply(assign_nivel)
    
    # 按照分数降序排序
    filtered_df = filtered_df.sort_values(by="score100", ascending=False)

# ==================== 视图 4: RESUMEN ====================
elif view == "Resumen":
    st.title("Resumen del Panel")

    # 1. 核心指标卡片 (Metrics)
    total_paises = len(df_paises)
    paises_activos = len(df_paises[df_paises['Estado'] == 'Activo'])
    total_productos = len(df_productos)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Países", total_paises)
    col2.metric("Países Activos", paises_activos)
    col3.metric("Total Productos", total_productos)

    st.divider()

    # 2. 国家状态分布图表
    st.subheader("📊 Distribución por Estado")
    # 统计每个状态的数量
    status_counts = df_paises['Estado'].value_counts()
    st.bar_chart(status_counts)

    # 3. 优先级统计 (同步 Prioridad 的计算规则)
    st.subheader("🎯 Resumen de Prioridad")
    
    # 定义计算用的默认权重（应与 Prioridad 页面保持一致）
    w_c1, w_c2, w_c3, w_c4, recency_window = 0.45, 0.15, 0.25, 0.15, 180
    
    # 计算所有国家的等级
    calc_df = df_prioridad.copy()
    calc_df['clientes365'] = pd.to_numeric(calc_df['clientes365'], errors='coerce').fillna(0)
    calc_df['productos_activos'] = pd.to_numeric(calc_df['productos_activos'], errors='coerce').fillna(0)
    calc_df['complejidadScore'] = pd.to_numeric(calc_df['complejidadScore'], errors='coerce').fillna(0)
    calc_df['daysSince'] = pd.to_numeric(calc_df['daysSince'], errors='coerce').fillna(0)

    # 计算分数和等级
    score01 = (calc_df['clientes365'] * w_c1) + (calc_df['productos_activos'] * w_c2) + \
              (calc_df['complejidadScore'] * w_c3) - (calc_df['daysSince'] / recency_window * w_c4)
    calc_df['score100'] = (score01 * 100).round()

    def assign_nivel(score):
        if score >= 80: return "P0"
        elif score >= 60: return "P1"
        elif score >= 40: return "P2"
        else: return "P3"

    calc_df['nivel'] = calc_df['score100'].apply(assign_nivel)
    
    # 统计各等级数量
    nivel_counts = calc_df['nivel'].value_counts().reindex(["P0", "P1", "P2", "P3"], fill_value=0)
    
    # 显示等级指标
    n1, n2, n3, n4 = st.columns(4)
    n1.metric("P0 (Alta)", nivel_counts["P0"])
    n2.metric("P1", nivel_counts["P1"])
    n3.metric("P2", nivel_counts["P2"])
    n4.metric("P3 (Baja)", nivel_counts["P3"])

    # 4. 高优先级国家列表 (Top 10)
    st.subheader("🔥 Top 10 Países Prioritarios (P0/P1)")
    top_paises = calc_df[calc_df['nivel'].isin(["P0", "P1"])].sort_values(by="score100", ascending=False).head(10)
    
    if not top_paises.empty:
        st.table(top_paises[['country', 'iso3', 'score100', 'nivel']])
    else:
        st.info("No hay países en niveles P0 o P1 con los pesos actuales.")
