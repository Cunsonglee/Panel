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
    
    # 将 Sin Estado 替换为 No implementado
    df['Estado_País'] = df['Estado_País'].fillna('No implementado').replace('nan', 'No implementado').replace('Sin Estado', 'No implementado').astype(str).str.strip()
    df['Estado_Producto'] = df['Estado_Producto'].fillna('No implementado').replace('nan', 'No implementado').replace('Sin Estado', 'No implementado').astype(str).str.strip()
    
    return df

# 初始化 Session State 用于保存交互式修改
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# 侧边栏菜单
menu = st.sidebar.radio("Menu", ["Paises", "Productos", "Resumen", "Prioridad"])

# 日期格式化工具
def format_dates(df_to_format):
    res_df = df_to_format.copy()
    date_cols = ['Actualización Completo', 'Actualización regla']
    for col in date_cols:
        if col in res_df.columns:
            res_df[col] = res_df[col].dt.strftime('%d-%m-%Y').fillna("")
    return res_df

# --- 1. Paises 页面 ---
if menu == "Paises":
    st.title("🌍 Paises - 国家维度统计")
    
    valid_countries = sorted([c for c in st.session_state.df['País'].unique() if c.lower() != 'nan'])
    valid_status = ["Activo", "Inactivo", "No implementado"]
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_countries = st.multiselect("选择国家", options=valid_countries)
    with col_f2:
        status_filter = st.multiselect("国家状态筛选", options=valid_status)
    
    # 统计逻辑
    def get_stats(group):
        has_prod = (group['Producto'].notna()) & (group['Producto'].str.lower() != 'nan')
        activos = (has_prod & (group['Estado_Producto'].str.lower() == 'activo')).sum()
        inactivos = (has_prod & (group['Estado_Producto'].str.lower() == 'inactivo')).sum()
        # 这里保留 Estado_País 的第一个值用于显示
        return pd.Series({
            'Estado_País': group['Estado_País'].iloc[0],
            'Activos': activos, 
            'Inactivos': inactivos
        })

    stats = st.session_state.df.groupby(['País', 'ISO3']).apply(get_stats).reset_index()

    if selected_countries:
        stats = stats[stats['País'].isin(selected_countries)]
    if status_filter:
        stats = stats[stats['Estado_País'].isin(status_filter)]
    
    st.info("💡 您可以在下表的 'Estado_País' 列通过下拉菜单修改状态。")
    
    # 使用 data_editor 实现下拉选择和保存
    edited_stats = st.data_editor(
        stats,
        column_config={
            "Estado_País": st.column_config.SelectboxColumn(
                "Estado País",
                options=valid_status,
                required=True,
            )
        },
        use_container_width=True,
        hide_index=True,
        height=800
    )

    if st.button("保存状态修改"):
        # 将修改同步回全局 session_state
        for index, row in edited_stats.iterrows():
            st.session_state.df.loc[st.session_state.df['País'] == row['País'], 'Estado_País'] = row['Estado_País']
        # 注意：此处如需永久保存到 Excel，需添加 df.to_excel(...) 代码
        st.success("状态已更新！(仅限当前会话，刷新页面后还原)")

# --- 2. Productos 页面 ---
elif menu == "Productos":
    st.title("📦 Productos - 产品维度详情")
    
    df_p = st.session_state.df[st.session_state.df['Producto'].notna() & (st.session_state.df['Producto'].str.lower() != 'nan')].copy()
    
    all_countries = sorted([str(c) for c in df_p['País'].unique()])
    all_p_status = ["Activo", "Inactivo", "No implementado"]
    
    c1, c2, c3 = st.columns(3)
    with c1:
        f_country = st.multiselect("筛选国家", options=all_countries)
    with c2:
        f_p_status = st.multiselect("筛选产品状态", options=all_p_status)
    with c3:
        f_c_status = st.multiselect("筛选国家状态", options=all_p_status)
    
    if f_country: df_p = df_p[df_p['País'].isin(f_country)]
    if f_p_status: df_p = df_p[df_p['Estado_Producto'].isin(f_p_status)]
    if f_c_status: df_p = df_p[df_p['Estado_País'].isin(f_c_status)]
        
    st.divider()
    # 格式化日期显示
    df_display = format_dates(df_p)
    
    display_cols = ['Producto', 'País', 'Estado_País', 'Estado_Producto', 
                    'Actualización Completo', 'Actualización regla', 'Nota_Producto']
    st.dataframe(df_display[display_cols], use_container_width=True, hide_index=True, height=1000)

# --- 3. Resumen 页面 ---
elif menu == "Resumen":
    st.title("📊 Resumen - 更新状态汇总")
    
    df_res = st.session_state.df[st.session_state.df['Producto'].notna() & (st.session_state.df['Producto'].str.lower() != 'nan')].copy()
    today = datetime.now()
    six_months_ago = today - timedelta(days=180)
    
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        st.subheader("⚠️ Regla 逾期")
        overdue_r = df_res[(df_res['Actualización regla'] < six_months_ago) | (df_res['Actualización regla'].isna())]
        st.dataframe(format_dates(overdue_r)[['Producto', 'País', 'Actualización regla']], use_container_width=True, hide_index=True)
        
    with col_w2:
        st.subheader("⚠️ Completo 逾期")
        overdue_c = df_res[(df_res['Actualización Completo'] < six_months_ago) | (df_res['Actualización Completo'].isna())]
        st.dataframe(format_dates(overdue_c)[['Producto', 'País', 'Actualización Completo']], use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("📅 季度更新统计")
    # 季度统计逻辑保持不变，但显示时会自动匹配 UI
    df_res['Q_Regla'] = df_res['Actualización regla'].dt.to_period('Q').astype(str).replace('NaT', None)
    df_res['Q_Completo'] = df_res['Actualización Completo'].dt.to_period('Q').astype(str).replace('NaT', None)
    
    qs = sorted(list(set(df_res['Q_Regla'].dropna().tolist() + df_res['Q_Completo'].dropna().tolist())))
    if qs:
        sel_q = st.selectbox("选择季度", options=["全部"] + qs)
        # 此处可添加条形图绘制逻辑
    else:
        st.info("无更新日期数据")

# --- 4. Prioridad 页面 ---
elif menu == "Prioridad":
    st.title("⚡ Prioridad")
    st.info("该模块内容暂未发布。")
