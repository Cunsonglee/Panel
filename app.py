import streamlit as st
import pandas as pd

# 设置页面配置
st.set_page_config(page_title="Panel de Control - Lee", layout="wide")

# 读取新上传的 Excel 数据
@st.cache_data
def load_data():
    file_path = "Merged_Countries_Vista-v2.xlsx"
    # 读取 Excel 文件
    df = pd.read_excel(file_path)
    # 确保状态列统一为小写，方便逻辑判断
    if 'Estado' in df.columns:
        df['Estado'] = df['Estado'].astype(str).str.lower()
    return df

df = load_data()

# 侧边栏导航
st.sidebar.title("导航栏")
page = st.sidebar.radio("选择页面", ["Resumen", "Paises", "Productos", "Prioridad"])

# --- 1. Resumen 页面 ---
if page == "Resumen":
    st.title("📊 总览 (Resumen)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总产品数", len(df))
    with col2:
        activos = len(df[df['Estado'] == 'activo']) if 'Estado' in df.columns else 0
        st.metric("在线产品 (Activo)", activos)
    with col3:
        inactivos = len(df[df['Estado'] == 'inactivo']) if 'Estado' in df.columns else 0
        st.metric("下线产品 (Inactivo)", inactivos)

    st.subheader("数据预览")
    st.dataframe(df.head(20), use_container_width=True)

# --- 2. Paises 页面 ---
elif page == "Paises":
    st.title("🌍 国家状态统计 (Paises)")
    
    if 'Pais' in df.columns and 'Estado' in df.columns and 'Producto' in df.columns:
        # 按国家分组，并统计 activo 和 inactivo 的产品数量
        pais_stats = df.groupby('Pais').apply(lambda x: pd.Series({
            'Activos': (x['Estado'] == 'activo').sum(),
            'Inactivos': (x['Estado'] == 'inactivo').sum(),
            'Total Productos': len(x)
        })).reset_index()
        
        st.write("以下是根据国家统计的产品状态分布：")
        st.dataframe(pais_stats.sort_values(by='Activos', ascending=False), use_container_width=True)
        
        # 搜索特定国家
        search_pais = st.selectbox("选择或搜索国家查看详情", ["所有"] + list(df['Pais'].unique()))
        if search_pais != "所有":
            filtered_df = df[df['Pais'] == search_pais]
            st.write(f"### {search_pais} 的产品详情")
            st.table(filtered_df[['Producto', 'Estado', 'Prioridad']])
    else:
        st.error("表格中缺少 'Pais', 'Estado' 或 'Producto' 列，请检查 Excel 文件。")

# --- 3. Productos 页面 ---
elif page == "Productos":
    st.title("📦 产品详情 (Productos)")
    
    # 过滤器
    search_query = st.text_input("搜索产品名称 (Producto)")
    status_filter = st.multiselect("筛选状态", options=df['Estado'].unique(), default=df['Estado'].unique())
    
    filtered_df = df[df['Estado'].isin(status_filter)]
    if search_query:
        filtered_df = filtered_df[filtered_df['Producto'].str.contains(search_query, case=False, na=False)]
    
    st.dataframe(filtered_df, use_container_width=True)

# --- 4. Prioridad 页面 ---
elif page == "Prioridad":
    st.title("⚡ 优先级排序 (Prioridad)")
    
    if 'Prioridad' in df.columns:
        # 按优先级排序，通常假设数字越小或特定等级越高
        sort_order = st.selectbox("排序方式", ["高到低", "低到高"])
        ascending = True if sort_order == "低到高" else False
        
        priority_df = df.sort_values(by='Prioridad', ascending=ascending)
        st.write("根据优先级排列的产品列表：")
        st.dataframe(priority_df[['Prioridad', 'Producto', 'Pais', 'Estado']], use_container_width=True)
    else:
        st.error("表格中未找到 'Prioridad' 列。")
