import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 页面配置
st.set_page_config(page_title="Panel de Control v2", layout="wide")

# 加载数据
@st.cache_data
def load_data():
    df = pd.read_excel('Merged_Countries_Vista-v2.xlsx')
    # 日期转换
    date_cols = ['Actualización Completo', 'Actualización regla']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    # 状态统一处理
    df['Estado_País'] = df['Estado_País'].fillna('Inactivo').astype(str)
    df['Estado_Producto'] = df['Estado_Producto'].fillna('Inactivo').astype(str)
    return df

df = load_data()

# 侧边栏菜单
menu = st.sidebar.radio("Menu", ["Paises", "Productos", "Resumen", "Prioridad"])

# --- 1. Paises 页面 ---
if menu == "Paises":
    st.title("🌍 Paises - 国家维度统计")
    
    # 筛选器
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_countries = st.multiselect("选择国家", options=df['País'].unique())
    with col_f2:
        status_filter = st.multiselect("国家状态 (Estado País)", options=df['Estado_País'].unique())
    
    # 应用筛选
    df_p = df.copy()
    if selected_countries:
        df_p = df_p[df_p['País'].isin(selected_countries)]
    if status_filter:
        df_p = df_p[df_p['Estado_País'].isin(status_filter)]
    
    # 统计数据逻辑
    stats = df_p.groupby(['País', 'ISO3', 'Estado_País']).apply(lambda x: pd.Series({
        'Activos': (x['Estado_Producto'].str.lower() == 'activo').sum(),
        'Inactivos': (x['Estado_Producto'].str.lower() == 'inactivo').sum()
    })).reset_index()

    # 顶部指标
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("总国家数量", len(df['País'].unique()))
    m2.metric("激活国家 (Activo País)", len(df[df['Estado_País'].str.lower() == 'activo']['País'].unique()))
    m3.metric("激活产品总数 (Activo Producto)", (df['Estado_Producto'].str.lower() == 'activo').sum())
    
    # 展示列表
    st.subheader("国家详细列表")
    st.dataframe(stats, use_container_width=True, hide_index=True)

# --- 2. Productos 页面 ---
elif menu == "Productos":
    st.title("📦 Productos - 产品维度详情")
    
    # 筛选器
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        p_country_filter = st.multiselect("筛选国家", options=df['País'].unique())
    with col_f2:
        p_status_filter = st.multiselect("产品状态 (Estado Producto)", options=df['Estado_Producto'].unique())
    
    # 应用筛选
    df_prod = df.copy()
    if p_country_filter:
        df_prod = df_prod[df_prod['País'].isin(p_country_filter)]
    if p_status_filter:
        df_prod = df_prod[df_prod['Estado_Producto'].isin(p_status_filter)]
        
    # 顶部指标
    st.divider()
    pm1, pm2, pm3 = st.columns(3)
    pm1.metric("总产品数量", len(df_prod))
    pm2.metric("激活产品数", (df_prod['Estado_Producto'].str.lower() == 'activo').sum())
    pm3.metric("下线产品数", (df_prod['Estado_Producto'].str.lower() == 'inactivo').sum())
    
    # 展示列表
    st.subheader("产品详情清单")
    display_cols = ['Producto', 'País', 'Estado_País', 'Estado_Producto', 
                    'Actualización Completo', 'Actualización regla', 'Nota_Producto']
    st.dataframe(df_prod[display_cols], use_container_width=True, hide_index=True)

# --- 3. Resumen 页面 ---
elif menu == "Resumen":
    st.title("📊 Resumen - 更新与预警")
    
    six_months_ago = datetime.now() - timedelta(days=180)
    
    # 1 & 2. 预警部分
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        st.subheader("⚠️ Regla 逾期 (6个月未更新或无日期)")
        overdue_regla = df[(df['Actualización regla'] < six_months_ago) | (df['Actualización regla'].isna())]
        st.write(f"共计: {len(overdue_regla)}")
        st.dataframe(overdue_regla[['Producto', 'País', 'Actualización regla']], height=200)
        
    with col_w2:
        st.subheader("⚠️ Completo 逾期 (6个月未更新或无日期)")
        overdue_comp = df[(df['Actualización Completo'] < six_months_ago) | (df['Actualización Completo'].isna())]
        st.write(f"共计: {len(overdue_comp)}")
        st.dataframe(overdue_comp[['Producto', 'País', 'Actualización Completo']], height=200)

    st.divider()
    
    # 3 & 4. 季度更新统计
    st.subheader("📅 季度更新趋势")
    
    # 准备季度数据
    df['Q_Regla'] = df['Actualización regla'].dt.to_period('Q').astype(str)
    df['Q_Completo'] = df['Actualización Completo'].dt.to_period('Q').astype(str)
    
    all_quarters = sorted(list(set(df['Q_Regla'].unique()) | set(df['Q_Completo'].unique())))
    all_quarters = [q for q in all_quarters if q != 'NaT']
    
    selected_q = st.selectbox("筛选季度", options=["全部"] + all_quarters)
    
    q_col1, q_col2 = st.columns(2)
    
    with q_col1:
        st.markdown("**Regla 更新分布**")
        regla_counts = df['Q_Regla'].value_counts().reset_index()
        if selected_q != "全部":
            regla_counts = regla_counts[regla_counts['Q_Regla'] == selected_q]
        st.bar_chart(regla_counts.set_index('Q_Regla'))
        
    with q_col2:
        st.markdown("**Completo 更新分布**")
        comp_counts = df['Q_Completo'].value_counts().reset_index()
        if selected_q != "全部":
            comp_counts = comp_counts[comp_counts['Q_Completo'] == selected_q]
        st.bar_chart(comp_counts.set_index('Q_Completo'))

# --- 4. Prioridad 页面 ---
elif menu == "Prioridad":
    st.title("⚡ Prioridad")
    st.info("该模块内容暂未发布，敬请期待。")
