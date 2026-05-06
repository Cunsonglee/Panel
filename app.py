import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 页面配置
st.set_page_config(page_title="Panel de Control v2", layout="wide")

# 加载数据
@st.cache_data
def load_data():
    # 使用您提供的新文件名
    file_name = 'Merged_Countries_Vista-v2.xlsx'
    df = pd.read_excel(file_name)
    
    # 强制转换日期并去除时间部分 (只保留日期)
    date_cols = ['Actualización Completo', 'Actualización regla']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce').dt.date  # 关键修改：添加 .dt.date
    
    # 清洗关键列，确保为字符串且无空字符
    df['País'] = df['País'].astype(str).str.strip()
    df['Producto'] = df['Producto'].astype(str).str.strip()
    df['Estado_País'] = df['Estado_País'].fillna('Sin Estado').astype(str).str.strip()
    df['Estado_Producto'] = df['Estado_Producto'].fillna('Sin Estado').astype(str).str.strip()
    
    return df

df_raw = load_data()

# 侧边栏菜单
menu = st.sidebar.radio("Menu", ["Paises", "Productos", "Resumen", "Prioridad"])

# --- 1. Paises 页面 ---
if menu == "Paises":
    st.title("🌍 Paises - 国家维度统计")
    
    valid_countries = sorted([c for c in df_raw['País'].unique() if pd.notna(c) and str(c).lower() != 'nan'])
    valid_status = sorted([s for s in df_raw['Estado_País'].unique() if pd.notna(s) and str(s).lower() != 'nan'])
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_countries = st.multiselect("选择国家 (可多选)", options=valid_countries)
    with col_f2:
        status_filter = st.multiselect("国家状态筛选", options=valid_status)
    
    def get_stats(group):
        has_prod = (group['Producto'].notna()) & (group['Producto'].str.lower() != 'nan')
        activos = (has_prod & (group['Estado_Producto'].str.lower() == 'activo')).sum()
        inactivos = (has_prod & (group['Estado_Producto'].str.lower() == 'inactivo')).sum()
        return pd.Series({'Activos': activos, 'Inactivos': inactivos})

    stats = df_raw.groupby(['País', 'ISO3', 'Estado_País']).apply(get_stats).reset_index()

    if selected_countries:
        stats = stats[stats['País'].isin(selected_countries)]
    if status_filter:
        stats = stats[stats['Estado_País'].isin(status_filter)]
    
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("总国家数", len(df_raw['País'].unique()))
    m2.metric("激活状态国家", len(df_raw[df_raw['Estado_País'].str.lower() == 'activo']['País'].unique()))
    m3.metric("全系统激活产品总数", ((df_raw['Estado_Producto'].str.lower() == 'activo') & (df_raw['Producto'].notna()) & (df_raw['Producto'].str.lower() != 'nan')).sum())
    
    st.subheader("国家状态列表 (全部展示)")
    st.dataframe(stats, use_container_width=True, hide_index=True, height=1000)

# --- 2. Productos 页面 ---
elif menu == "Productos":
    st.title("📦 Productos - 产品维度详情")
    
    df_prod_base = df_raw[df_raw['Producto'].notna() & (df_raw['Producto'].str.lower() != 'nan')].copy()
    
    all_countries_p = sorted([str(c) for c in df_prod_base['País'].unique() if pd.notna(c)])
    all_prod_status = sorted([str(s) for s in df_prod_base['Estado_Producto'].unique() if pd.notna(s)])

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        p_country_filter = st.multiselect("按国家筛选产品", options=all_countries_p)
    with col_f2:
        p_status_filter = st.multiselect("按产品状态筛选", options=all_prod_status)
    
    if p_country_filter:
        df_prod_base = df_prod_base[df_prod_base['País'].isin(p_country_filter)]
    if p_status_filter:
        df_prod_base = df_prod_base[df_prod_base['Estado_Producto'].isin(p_status_filter)]
        
    st.divider()
    pm1, pm2, pm3 = st.columns(3)
    pm1.metric("当前显示产品数", len(df_prod_base))
    pm2.metric("激活产品", (df_prod_base['Estado_Producto'].str.lower() == 'activo').sum())
    pm3.metric("下线产品", (df_prod_base['Estado_Producto'].str.lower() == 'inactivo').sum())
    
    st.subheader("产品清单 (全部展示)")
    display_cols = ['Producto', 'País', 'Estado_País', 'Estado_Producto', 
                    'Actualización Completo', 'Actualización regla', 'Nota_Producto']
    st.dataframe(df_prod_base[display_cols], use_container_width=True, hide_index=True, height=1000)

# --- 3. Resumen 页面 ---
elif menu == "Resumen":
    st.title("📊 Resumen - 更新状态汇总")
    
    df_res = df_raw[df_raw['Producto'].notna() & (df_raw['Producto'].str.lower() != 'nan')].copy()
    # 这里的比较逻辑需要稍微调整，因为现在 df_res 里的列是 date 对象
    today = datetime.now().date()
    six_months_ago = today - timedelta(days=180)
    
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        st.subheader("⚠️ Regla 逾期 (6个月未更)")
        # 即使列是 date 类型，也可以直接与 date 对象比较
        overdue_regla = df_res[(df_res['Actualización regla'] < six_months_ago) | (df_res['Actualización regla'].isna())]
        st.write(f"数量: {len(overdue_regla)}")
        st.dataframe(overdue_regla[['Producto', 'País', 'Actualización regla']], use_container_width=True, hide_index=True, height=400)
        
    with col_w2:
        st.subheader("⚠️ Completo 逾期 (6个月未更)")
        overdue_comp = df_res[(df_res['Actualización Completo'] < six_months_ago) | (df_res['Actualización Completo'].isna())]
        st.write(f"数量: {len(overdue_comp)}")
        st.dataframe(overdue_comp[['Producto', 'País', 'Actualización Completo']], use_container_width=True, hide_index=True, height=400)

    st.divider()
    
    st.subheader("📅 季度更新趋势")
    
    # 将 date 对象重新转为 period 统计
    df_res['Q_Regla'] = pd.to_datetime(df_res['Actualización regla']).dt.to_period('Q').apply(lambda x: x.strftime('%YQ%q') if pd.notna(x) else None)
    df_res['Q_Completo'] = pd.to_datetime(df_res['Actualización Completo']).dt.to_period('Q').apply(lambda x: x.strftime('%YQ%q') if pd.notna(x) else None)
    
    qs_regla = [str(q) for q in df_res['Q_Regla'].dropna().unique()]
    qs_comp = [str(q) for q in df_res['Q_Completo'].dropna().unique()]
    all_quarters = sorted(list(set(qs_regla + qs_comp)))
    
    if not all_quarters:
        st.info("没有发现可用的季度更新记录。")
    else:
        selected_q = st.selectbox("选择统计季度", options=["全部"] + all_quarters)
        
        qc1, qc2 = st.columns(2)
        with qc1:
            st.markdown("**Regla 更新数**")
            counts = df_res['Q_Regla'].value_counts().reset_index()
            counts.columns = ['Quarter', 'Count']
            if selected_q != "全部": counts = counts[counts['Quarter'] == selected_q]
            st.bar_chart(counts.set_index('Quarter'))
            
        with qc2:
            st.markdown("**Completo 更新数**")
            counts = df_res['Q_Completo'].value_counts().reset_index()
            counts.columns = ['Quarter', 'Count']
            if selected_q != "全部": counts = counts[counts['Quarter'] == selected_q]
            st.bar_chart(counts.set_index('Quarter'))

# --- 4. Prioridad 页面 ---
elif menu == "Prioridad":
    st.title("⚡ Prioridad")
    st.info("该模块内容暂未发布。")
