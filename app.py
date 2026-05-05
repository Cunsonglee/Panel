import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 页面配置
st.set_page_config(page_title="Panel de Control v2", layout="wide")

# 加载数据
@st.cache_data
def load_data():
    # 读取 Excel
    df = pd.read_excel('Merged_Countries_Vista-v2.xlsx')
    
    # 日期转换
    date_cols = ['Actualización Completo', 'Actualización regla']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # 清洗数据：去除国家名或产品名两端的空格
    if 'País' in df.columns:
        df['País'] = df['País'].astype(str).str.strip()
    if 'Producto' in df.columns:
        df['Producto'] = df['Producto'].astype(str).str.strip()
        
    # 状态填充，避免 NaN 影响逻辑
    df['Estado_País'] = df['Estado_País'].fillna('Inactivo')
    df['Estado_Producto'] = df['Estado_Producto'].fillna('Inactivo')
    
    return df

df_raw = load_data()

# 侧边栏菜单
menu = st.sidebar.radio("Menu", ["Paises", "Productos", "Resumen", "Prioridad"])

# --- 1. Paises 页面 ---
if menu == "Paises":
    st.title("🌍 Paises - 国家维度统计")
    
    # 筛选器：排除 NaN (nan)
    all_countries = sorted([c for c in df_raw['País'].unique() if str(c).lower() != 'nan'])
    all_p_status = sorted([s for s in df_raw['Estado_País'].unique() if str(s).lower() != 'nan'])
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_countries = st.multiselect("选择国家", options=all_countries)
    with col_f2:
        status_filter = st.multiselect("国家状态 (Estado País)", options=all_p_status)
    
    # 逻辑：展示全部国家，包括没有产品的
    # 先按国家汇总统计
    stats = df_raw.groupby(['País', 'ISO3', 'Estado_País']).apply(lambda x: pd.Series({
        'Activos': ((x['Estado_Producto'].str.lower() == 'activo') & (x['Producto'].notna()) & (x['Producto'] != 'nan')).sum(),
        'Inactivos': ((x['Estado_Producto'].str.lower() == 'inactivo') & (x['Producto'].notna()) & (x['Producto'] != 'nan')).sum()
    })).reset_index()

    # 应用筛选器
    if selected_countries:
        stats = stats[stats['País'].isin(selected_countries)]
    if status_filter:
        stats = stats[stats['Estado_País'].isin(status_filter)]
    
    # 顶部指标
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("总国家数量", len(df_raw['País'].unique()))
    m2.metric("激活国家 (Activo País)", len(df_raw[df_raw['Estado_País'].str.lower() == 'activo']['País'].unique()))
    m3.metric("激活产品总数 (Activo Producto)", ((df_raw['Estado_Producto'].str.lower() == 'activo') & (df_raw['Producto'].notna()) & (df_raw['Producto'] != 'nan')).sum())
    
    # 展示列表
    st.subheader("国家详细列表")
    st.dataframe(stats, use_container_width=True, hide_index=True)

# --- 2. Productos 页面 ---
elif menu == "Productos":
    st.title("📦 Productos - 产品维度详情")
    
    # 基础过滤：只显示有产品的行
    df_prod_base = df_raw[df_raw['Producto'].notna() & (df_raw['Producto'] != 'nan')].copy()
    
    # 筛选器：排除 NaN
    all_countries_p = sorted([c for c in df_prod_base['País'].unique() if str(c).lower() != 'nan'])
    all_prod_status = sorted([s for s in df_prod_base['Estado_Producto'].unique() if str(s).lower() != 'nan'])

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        p_country_filter = st.multiselect("筛选国家", options=all_countries_p)
    with col_f2:
        p_status_filter = st.multiselect("产品状态 (Estado Producto)", options=all_prod_status)
    
    # 应用筛选
    if p_country_filter:
        df_prod_base = df_prod_base[df_prod_base['País'].isin(p_country_filter)]
    if p_status_filter:
        df_prod_base = df_prod_base[df_prod_base['Estado_Producto'].isin(p_status_filter)]
        
    # 顶部指标
    st.divider()
    pm1, pm2, pm3 = st.columns(3)
    pm1.metric("总产品数量", len(df_prod_base))
    pm2.metric("激活产品数", (df_prod_base['Estado_Producto'].str.lower() == 'activo').sum())
    pm3.metric("下线产品数", (df_prod_base['Estado_Producto'].str.lower() == 'inactivo').sum())
    
    # 展示列表
    st.subheader("产品详情清单")
    display_cols = ['Producto', 'País', 'Estado_País', 'Estado_Producto', 
                    'Actualización Completo', 'Actualización regla', 'Nota_Producto']
    st.dataframe(df_prod_base[display_cols], use_container_width=True, hide_index=True)

# --- 3. Resumen 页面 ---
elif menu == "Resumen":
    st.title("📊 Resumen - 更新与预警")
    
    # 基础过滤：只针对有产品的行进行预警和统计
    df_res = df_raw[df_raw['Producto'].notna() & (df_raw['Producto'] != 'nan')].copy()
    six_months_ago = datetime.now() - timedelta(days=180)
    
    # 1 & 2. 预警部分
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        st.subheader("⚠️ Regla 逾期")
        overdue_regla = df_res[(df_res['Actualización regla'] < six_months_ago) | (df_res['Actualización regla'].isna())]
        st.write(f"共计: {len(overdue_regla)}")
        st.dataframe(overdue_regla[['Producto', 'País', 'Actualización regla']], height=300, hide_index=True)
        
    with col_w2:
        st.subheader("⚠️ Completo 逾期")
        overdue_comp = df_res[(df_res['Actualización Completo'] < six_months_ago) | (df_res['Actualización Completo'].isna())]
        st.write(f"共计: {len(overdue_comp)}")
        st.dataframe(overdue_comp[['Producto', 'País', 'Actualización Completo']], height=300, hide_index=True)

    st.divider()
    
    # 3 & 4. 季度更新统计 (修复 TypeError)
    st.subheader("📅 季度更新趋势")
    
    # 转换季度字符串，处理空值
    df_res['Q_Regla'] = df_res['Actualización regla'].dt.to_period('Q').astype(str).replace('NaT', None)
    df_res['Q_Completo'] = df_res['Actualización Completo'].dt.to_period('Q').astype(str).replace('NaT', None)
    
    # 稳健地合并季度列表
    qs_regla = [q for q in df_res['Q_Regla'].unique() if q is not None]
    qs_comp = [q for q in df_res['Q_Completo'].unique() if q is not None]
    all_quarters = sorted(list(set(qs_regla + qs_comp)))
    
    selected_q = st.selectbox("筛选季度", options=["全部"] + all_quarters)
    
    q_col1, q_col2 = st.columns(2)
    
    with q_col1:
        st.markdown("**Regla 更新分布**")
        regla_counts = df_res['Q_Regla'].value_counts().reset_index()
        regla_counts.columns = ['Quarter', 'Count']
        if selected_q != "全部":
            regla_counts = regla_counts[regla_counts['Quarter'] == selected_q]
        st.bar_chart(regla_counts.set_index('Quarter'))
        
    with q_col2:
        st.markdown("**Completo 更新分布**")
        comp_counts = df_res['Q_Completo'].value_counts().reset_index()
        comp_counts.columns = ['Quarter', 'Count']
        if selected_q != "全部":
            comp_counts = comp_counts[comp_counts['Quarter'] == selected_q]
        st.bar_chart(comp_counts.set_index('Quarter'))

# --- 4. Prioridad 页面 ---
elif menu == "Prioridad":
    st.title("⚡ Prioridad")
    st.info("该模块内容暂未发布。")
