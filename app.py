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
    
    # 强制转换日期
    date_cols = ['Actualización Completo', 'Actualización regla']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # 数据清洗：确保国家和产品列是字符串且去除空格
    df['País'] = df['País'].astype(str).str.strip()
    df['Producto'] = df['Producto'].astype(str).str.strip()
    
    # 统一处理状态列
    df['Estado_País'] = df['Estado_País'].fillna('Sin Estado').astype(str)
    df['Estado_Producto'] = df['Estado_Producto'].fillna('Sin Estado').astype(str)
    
    return df

df_raw = load_data()

# 侧边栏菜单
menu = st.sidebar.radio("Menu", ["Paises", "Productos", "Resumen", "Prioridad"])

# --- 1. Paises 页面 ---
if menu == "Paises":
    st.title("🌍 Paises - 国家维度统计")
    
    # 修复：确保 unique() 结果中不包含非字符串，并过滤掉 'nan' 字符串
    all_countries = sorted([str(c) for c in df_raw['País'].unique() if pd.notna(c) and str(c).lower() != 'nan'])
    all_p_status = sorted([str(s) for s in df_raw['Estado_País'].unique() if pd.notna(s) and str(s).lower() != 'nan'])
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_countries = st.multiselect("选择国家", options=all_countries)
    with col_f2:
        status_filter = st.multiselect("国家状态 (Estado País)", options=all_p_status)
    
    # 统计逻辑
    stats = df_raw.groupby(['País', 'ISO3', 'Estado_País']).apply(lambda x: pd.Series({
        'Activos': ((x['Estado_Producto'].str.lower() == 'activo') & (x['Producto'].notna()) & (x['Producto'].astype(str).str.lower() != 'nan')).sum(),
        'Inactivos': ((x['Estado_Producto'].str.lower() == 'inactivo') & (x['Producto'].notna()) & (x['Producto'].astype(str).str.lower() != 'nan')).sum()
    })).reset_index()

    if selected_countries:
        stats = stats[stats['País'].isin(selected_countries)]
    if status_filter:
        stats = stats[stats['Estado_País'].isin(status_filter)]
    
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("总国家数量", len(df_raw['País'].unique()))
    m2.metric("激活国家 (Activo País)", len(df_raw[df_raw['Estado_País'].str.lower() == 'activo']['País'].unique()))
    m3.metric("激活产品总数", ((df_raw['Estado_Producto'].str.lower() == 'activo') & (df_raw['Producto'].notna()) & (df_raw['Producto'].astype(str).str.lower() != 'nan')).sum())
    
    st.subheader("国家详细列表 (全部展示)")
    st.dataframe(stats, use_container_width=True, hide_index=True, height=1000)

# --- 2. Productos 页面 ---
elif menu == "Productos":
    st.title("📦 Productos - 产品维度详情")
    
    # 只显示有有效产品的行
    df_prod_base = df_raw[df_raw['Producto'].notna() & (df_raw['Producto'].astype(str).str.lower() != 'nan')].copy()
    
    all_countries_p = sorted([str(c) for c in df_prod_base['País'].unique() if pd.notna(c) and str(c).lower() != 'nan'])
    all_prod_status = sorted([str(s) for s in df_prod_base['Estado_Producto'].unique() if pd.notna(s) and str(s).lower() != 'nan'])

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        p_country_filter = st.multiselect("筛选国家", options=all_countries_p)
    with col_f2:
        p_status_filter = st.multiselect("产品状态 (Estado Producto)", options=all_prod_status)
    
    if p_country_filter:
        df_prod_base = df_prod_base[df_prod_base['País'].isin(p_country_filter)]
    if p_status_filter:
        df_prod_base = df_prod_base[df_prod_base['Estado_Producto'].isin(p_status_filter)]
        
    st.divider()
    pm1, pm2, pm3 = st.columns(3)
    pm1.metric("总产品数量", len(df_prod_base))
    pm2.metric("激活产品数", (df_prod_base['Estado_Producto'].str.lower() == 'activo').sum())
    pm3.metric("下线产品数", (df_prod_base['Estado_Producto'].str.lower() == 'inactivo').sum())
    
    st.subheader("产品详情清单 (全部展示)")
    # 调换顺序：Producto, País
    display_cols = ['Producto', 'País', 'Estado_País', 'Estado_Producto', 
                    'Actualización Completo', 'Actualización regla', 'Nota_Producto']
    st.dataframe(df_prod_base[display_cols], use_container_width=True, hide_index=True, height=1000)

# --- 3. Resumen 页面 ---
elif menu == "Resumen":
    st.title("📊 Resumen - 更新与预警")
    
    df_res = df_raw[df_raw['Producto'].notna() & (df_raw['Producto'].astype(str).str.lower() != 'nan')].copy()
    six_months_ago = datetime.now() - timedelta(days=180)
    
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        st.subheader("⚠️ Regla 逾期")
        overdue_regla = df_res[(df_res['Actualización regla'] < six_months_ago) | (df_res['Actualización regla'].isna())]
        st.write(f"共计: {len(overdue_regla)}")
        st.dataframe(overdue_regla[['Producto', 'País', 'Actualización regla']], use_container_width=True, hide_index=True, height=500)
        
    with col_w2:
        st.subheader("⚠️ Completo 逾期")
        overdue_comp = df_res[(df_res['Actualización Completo'] < six_months_ago) | (df_res['Actualización Completo'].isna())]
        st.write(f"共计: {len(overdue_comp)}")
        st.dataframe(overdue_comp[['Producto', 'País', 'Actualización Completo']], use_container_width=True, hide_index=True, height=500)

    st.divider()
    
    st.subheader("📅 季度更新趋势")
    
    # 安全处理季度转换
    df_res['Q_Regla'] = df_res['Actualización regla'].apply(lambda x: x.to_period('Q').strftime('%YQ%q') if pd.notna(x) else None)
    df_res['Q_Completo'] = df_res['Actualización Completo'].apply(lambda x: x.to_period('Q').strftime('%YQ%q') if pd.notna(x) else None)
    
    # 修复：使用更稳健的方式提取季度并排序
    qs_regla = [str(q) for q in df_res['Q_Regla'].dropna().unique()]
    qs_comp = [str(q) for q in df_res['Q_Completo'].dropna().unique()]
    all_quarters = sorted(list(set(qs_regla + qs_comp)))
    
    if not all_quarters:
        st.warning("数据中未发现有效的更新日期记录。")
    else:
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
