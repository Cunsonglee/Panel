import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 页面配置
st.set_page_config(page_title="Panel de Control v2", layout="wide")

# 加载数据
@st.cache_data
def load_data():
    file_name = 'Merged_Countries_Vista-v2.xlsx'
    try:
        df = pd.read_excel(file_name)
    except FileNotFoundError:
        st.error(f"❌ 找不到文件: {file_name}")
        st.stop()
    
    # 强制转换日期
    date_cols = ['Actualización Completo', 'Actualización regla']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # 清洗数据
    df['País'] = df['País'].astype(str).str.strip()
    df['Producto'] = df['Producto'].astype(str).str.strip()
    
    # 初始状态清洗：统一为三种状态
    status_map = {
        'nan': 'No implementado',
        'Sin Estado': 'No implementado',
        'None': 'No implementado'
    }
    for col in ['Estado_País', 'Estado_Producto']:
        df[col] = df[col].astype(str).str.strip().replace(status_map).fillna('No implementado')
        # 兜底：如果不在三个标准状态内，也设为 No implementado
        valid_options = ["Activo", "Inactivo", "No implementado"]
        df[col] = df[col].apply(lambda x: x if x in valid_options else "No implementado")
    
    return df

# 初始化 Session State
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# 通用配置
valid_status = ["Activo", "Inactivo", "No implementado"]

# 日期格式化工具函数
def get_display_df(df_input):
    display_df = df_input.copy()
    for col in ['Actualización Completo', 'Actualización regla']:
        if col in display_df.columns:
            display_df[col] = display_df[col].dt.strftime('%d-%m-%Y').fillna("")
    return display_df

# 侧边栏菜单
menu = st.sidebar.radio("Menu", ["Paises", "Productos", "Resumen", "Prioridad"])

# --- 1. Paises 页面 ---
if menu == "Paises":
    st.title("🌍 Paises - 国家维度统计")
    
    all_countries = sorted([c for c in st.session_state.df['País'].unique() if c.lower() != 'nan'])
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_countries = st.multiselect("选择国家", options=all_countries)
    with col_f2:
        status_filter = st.multiselect("国家状态筛选", options=valid_status)
    
    # 按国家汇总
    stats = st.session_state.df.groupby(['País', 'ISO3']).apply(lambda x: pd.Series({
        'Estado_País': x['Estado_País'].iloc[0],
        'Activos': ((x['Estado_Producto'] == 'Activo') & (x['Producto'].notna())).sum(),
        'Inactivos': ((x['Estado_Producto'] == 'Inactivo') & (x['Producto'].notna())).sum()
    })).reset_index()

    if selected_countries:
        stats = stats[stats['País'].isin(selected_countries)]
    if status_filter:
        stats = stats[stats['Estado_País'].isin(status_filter)]
    
    st.info("💡 您可以修改 'Estado_País'。修改后请点击下方保存按钮。")
    
    edited_paises = st.data_editor(
        stats,
        column_config={
            "Estado_País": st.column_config.SelectboxColumn("Estado País", options=valid_status, required=True),
            "País": st.column_config.Column(disabled=True),
            "ISO3": st.column_config.Column(disabled=True),
            "Activos": st.column_config.Column(disabled=True),
            "Inactivos": st.column_config.Column(disabled=True),
        },
        use_container_width=True, hide_index=True, height=600
    )

    if st.button("💾 保存国家状态修改"):
        for _, row in edited_paises.iterrows():
            st.session_state.df.loc[st.session_state.df['País'] == row['País'], 'Estado_País'] = row['Estado_País']
        st.success("国家状态已成功同步到全局数据！")

# --- 2. Productos 页面 ---
elif menu == "Productos":
    st.title("📦 Productos - 产品维度详情")
    
    # 基础过滤：只显示有产品的行
    df_prod = st.session_state.df[st.session_state.df['Producto'].notna() & (st.session_state.df['Producto'] != 'nan')].copy()
    
    c1, c2, c3 = st.columns(3)
    with c1:
        f_country = st.multiselect("筛选国家", options=sorted(df_prod['País'].unique()))
    with c2:
        f_p_status = st.multiselect("筛选产品状态", options=valid_status)
    with c3:
        f_c_status = st.multiselect("筛选国家状态", options=valid_status)
    
    if f_country: df_prod = df_prod[df_prod['País'].isin(f_country)]
    if f_p_status: df_prod = df_prod[df_prod['Estado_Producto'].isin(f_p_status)]
    if f_c_status: df_prod = df_prod[df_prod['Estado_País'].isin(f_c_status)]

    st.warning("⚠️ 此页面仅允许修改 'Estado_Producto'。'Estado_País' 为只读锁住状态。")
    
    # 为了编辑，我们需要一个带有原始索引的副本
    df_for_edit = get_display_df(df_prod)
    
    edited_prod = st.data_editor(
        df_for_edit,
        column_config={
            "Estado_Producto": st.column_config.SelectboxColumn("Estado Producto", options=valid_status, required=True),
            "Estado_País": st.column_config.Column("Estado País (锁住)", disabled=True), # 锁住国家状态
            "País": st.column_config.Column(disabled=True),
            "Producto": st.column_config.Column(disabled=True),
            "Actualización Completo": st.column_config.Column(disabled=True),
            "Actualización regla": st.column_config.Column(disabled=True),
        },
        use_container_width=True, hide_index=True, height=800
    )

    if st.button("💾 保存产品状态修改"):
        # 根据 Producto 和 País 唯一键回填数据
        for _, row in edited_prod.iterrows():
            mask = (st.session_state.df['Producto'] == row['Producto']) & (st.session_state.df['País'] == row['País'])
            st.session_state.df.loc[mask, 'Estado_Producto'] = row['Estado_Producto']
        st.success("产品状态已更新！")

# --- 3. Resumen 页面 ---
elif menu == "Resumen":
    st.title("📊 Resumen - 逾期预警")
    df_res = st.session_state.df[st.session_state.df['Producto'].notna() & (st.session_state.df['Producto'] != 'nan')].copy()
    limit_date = datetime.now() - timedelta(days=180)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("⚠️ Regla 逾期")
        r_df = df_res[(df_res['Actualización regla'] < limit_date) | (df_res['Actualización regla'].isna())]
        st.dataframe(get_display_df(r_df)[['Producto', 'País', 'Actualización regla']], use_container_width=True, hide_index=True)
    with col2:
        st.subheader("⚠️ Completo 逾期")
        c_df = df_res[(df_res['Actualización Completo'] < limit_date) | (df_res['Actualización Completo'].isna())]
        st.dataframe(get_display_df(c_df)[['Producto', 'País', 'Actualización Completo']], use_container_width=True, hide_index=True)

# --- 4. Prioridad 页面 ---
elif menu == "Prioridad":
    st.title("⚡ Prioridad")
    st.info("该模块内容暂未发布。")
