import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 页面基础配置
st.set_page_config(page_title="控制面板 v2", layout="wide")

# 你在 GitHub 仓库中的统一主文件名称
FILE_NAME = 'Priority (1).xlsx'

# 核心数据加载函数
@st.cache_data
def load_data():
    try:
        # 读取从 GitHub 仓库加载的 Excel 主文件
        df = pd.read_excel(FILE_NAME)
    except FileNotFoundError:
        st.error(f"❌ 未在仓库中找到文件: {FILE_NAME}")
        st.stop()
    except Exception as e:
        st.error(f"❌ 打开 Excel 文件时出错: {e}")
        st.stop()
    
    # 强制将日期列转换为 datetime 对象，以便在表格组件中直接调出日历选择器
    date_cols = ['Actualización Completo', 'Actualización regla']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # 基础文本去空格清洗
    df['País'] = df['País'].astype(str).str.strip()
    df['Producto'] = df['Producto'].astype(str).str.strip()
    
    # 统一并清洗国家与产品的状态（将空值和无效值统一归类为 'No implementado'）
    status_map = {'nan': 'No implementado', 'Sin Estado': 'No implementado', 'None': 'No implementado'}
    valid_options = ["Activo", "Inactivo", "No implementado"]
    
    for col in ['Estado_País', 'Estado_Producto']:
        df[col] = df[col].astype(str).str.strip().replace(status_map).fillna('No implementado')
        df[col] = df[col].apply(lambda x: x if x in valid_options else "No implementado")
    
    return df

# 初始化 Streamlit 全局会话状态 (Session State)
if 'df' not in st.session_state:
    st.session_state.df = load_data()

valid_status = ["Activo", "Inactivo", "No implementado"]

# 辅助函数：仅用于在不可编辑的直观视图（如 Resumen 摘要页）中规范日期显示格式
def get_display_df(df_input):
    display_df = df_input.copy()
    for col in ['Actualización Completo', 'Actualización regla']:
        if col in display_df.columns:
            display_df[col] = display_df[col].dt.strftime('%Y-%m-%d').fillna("")
    return display_df

# 侧边栏菜单导航
menu = st.sidebar.radio("菜单", ["Países (国家)", "Productos (产品)", "Resumen (摘要)", "Prioridad (优先级)"])

# --- 1. Países (国家页面) ---
if menu == "Países (国家)":
    head_col1, head_col2 = st.columns([0.85, 0.15])
    with head_col1:
        st.title("🌍 Países - 各国数据统计")
    
    # 实时汇总各国的国家状态及旗下活跃/不活跃产品数量
    stats = st.session_state.df.groupby(['País', 'ISO3']).apply(lambda x: pd.Series({
        'Estado_País': x['Estado_País'].iloc[0],
        'Activos': ((x['Estado_Producto'] == 'Activo') & (x['Producto'].notna())).sum(),
        'Inactivos': ((x['Estado_Producto'] == 'Inactivo') & (x['Producto'].notna())).sum()
    })).reset_index()

    # 动态数据过滤器
    all_countries = sorted([c for c in st.session_state.df['País'].unique() if c.lower() != 'nan'])
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_countries = st.multiselect("选择国家", options=all_countries)
    with col_f2:
        status_filter = st.multiselect("按国家状态筛选", options=valid_status)

    if selected_countries:
        stats = stats[stats['País'].isin(selected_countries)]
    if status_filter:
        stats = stats[stats['Estado_País'].isin(status_filter)]

    with head_col2:
        st.write(" ") 
        if st.button("💾 保存修改", key="save_paises_btn"):
            st.session_state.trigger_save_paises = True

    # 国家状态可编辑表格
    edited_paises = st.data_editor(
        stats,
        column_config={
            "Estado_País": st.column_config.SelectboxColumn("国家状态", options=valid_status, required=True),
            "País": st.column_config.Column("国家", disabled=True),
            "ISO3": st.column_config.Column(disabled=True),
            "Activos": st.column_config.Column("活跃产品数", disabled=True),
            "Inactivos": st.column_config.Column("非活跃产品数", disabled=True),
        },
        use_container_width=True, hide_index=True, height=800
    )

    if st.session_state.get('trigger_save_paises'):
        for _, row in edited_paises.iterrows():
            st.session_state.df.loc[st.session_state.df['País'] == row['País'], 'Estado_País'] = row['Estado_País']
        
        # 持久化数据：直接重写覆盖回 Excel 文件
        try:
            st.session_state.df.to_excel(FILE_NAME, index=False)
            st.success(f"¡国家状态已成功保存至 {FILE_NAME}!")
            st.cache_data.clear()  # 清除缓存强制页面刷新读取最新数据
            del st.session_state.trigger_save_paises
            st.rerun()
        except Exception as e:
            st.error(f"保存文件时出错: {e}")

# --- 2. Productos (产品页面) ---
elif menu == "Productos (产品)":
    head_col1, head_col2 = st.columns([0.85, 0.15])
    with head_col1:
        st.title("📦 Productos - 产品细节管理")
    
    with head_col2:
        st.write(" ") 
        if st.button("💾 保存修改", key="save_prod_btn"):
            st.session_state.trigger_save_prod = True

    # 过滤掉空产品行
    df_prod = st.session_state.df[st.session_state.df['Producto'].notna() & (st.session_state.df['Producto'] != 'nan')].copy()
    
    # 过滤器
    c1, c2, c3 = st.columns(3)
    with c1:
        f_country = st.multiselect("按国家筛选", options=sorted(df_prod['País'].unique()))
    with c2:
        f_p_status = st.multiselect("按产品状态筛选", options=valid_status)
    with c3:
        f_c_status = st.multiselect("按国家状态筛选", options=valid_status)
    
    if f_country: df_prod = df_prod[df_prod['País'].isin(f_country)]
    if f_p_status: df_prod = df_prod[df_prod['Estado_Producto'].isin(f_p_status)]
    if f_c_status: df_prod = df_prod[df_prod['Estado_País'].isin(f_c_status)]

    # 核心：为了让 st.data_editor 展现日历组件，必须保持两列日期为原生的 datetime 对象
    display_cols = ['País', 'Estado_País', 'Producto', 'Estado_Producto', 
                    'Actualización Completo', 'Actualización regla', 'Nota_Producto']
    df_for_edit = df_prod[display_cols].copy()
    
    # 交互式表格配置：解锁日期编辑和网页链接跳转
    edited_prod = st.data_editor(
        df_for_edit,
        column_config={
            "Estado_Producto": st.column_config.SelectboxColumn("产品状态", options=valid_status, required=True),
            "Actualización Completo": st.column_config.DateColumn("完整更新日期", format="YYYY-MM-DD"), # 点击直接弹出日历选择
            "Actualización regla": st.column_config.DateColumn("规则更新日期", format="YYYY-MM-DD"), # 点击直接弹出日历选择
            "Nota_Producto": st.column_config.LinkColumn("产品备注 (网页链接)", help="点击按钮直接在新标签页中打开网页链接", display_text="🔗 打开链接"), # 可编辑且直接点击跳转
            "Estado_País": st.column_config.Column("国家状态 (锁定)", disabled=True), 
            "País": st.column_config.Column("国家", disabled=True),
            "Producto": st.column_config.Column("产品", disabled=True),
        },
        use_container_width=True, hide_index=True, height=1000
    )

    if st.session_state.get('trigger_save_prod'):
        # 将用户在高级数据表格中修改的行映射并更新回全局的 st.session_state.df 中
        for _, row in edited_prod.iterrows():
            mask = (st.session_state.df['Producto'] == row['Producto']) & (st.session_state.df['País'] == row['País'])
            st.session_state.df.loc[mask, 'Estado_Producto'] = row['Estado_Producto']
            
            # 安全更新日期（如果用户清空了日期，则保持为 NaT 空值）
            st.session_state.df.loc[mask, 'Actualización Completo'] = pd.to_datetime(row['Actualización Completo']) if pd.notna(row['Actualización Completo']) else pd.NaT
            st.session_state.df.loc[mask, 'Actualización regla'] = pd.to_datetime(row['Actualización regla']) if pd.notna(row['Actualización regla']) else pd.NaT
            
            # 更新文本或链接内容
            st.session_state.df.loc[mask, 'Nota_Producto'] = row['Nota_Producto']
            
        # 将所有的修改覆盖保存回 GitHub 上的 Excel 文件中
        try:
            st.session_state.df.to_excel(FILE_NAME, index=False)
            st.success(f"¡所有产品更改和网页链接已成功保存至 {FILE_NAME}!")
            st.cache_data.clear() # 清理缓存
            del st.session_state.trigger_save_prod
            st.rerun()
        except Exception as e:
            st.error(f"保存文件时出错: {e}")

# --- 3. Resumen (摘要页面) ---
elif menu == "Resumen (摘要)":
    st.title("📊 Resumen - 规则更新超期预警")
    df_res = st.session_state.df[st.session_state.df['Producto'].notna() & (st.session_state.df['Producto'] != 'nan')].copy()
    limit_date = datetime.now() - timedelta(days=180) # 6个月边界
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("⚠️ 规则过期 (> 6 个月未更新)")
        r_df = df_res[(df_res['Actualización regla'] < limit_date) | (df_res['Actualización regla'].isna())]
        st.dataframe(get_display_df(r_df)[['Producto', 'País', 'Actualización regla']], use_container_width=True, hide_index=True)
    with col2:
        st.subheader("⚠️ 完整数据过期 (> 6 个月未更新)")
        c_df = df_res[(df_res['Actualización Completo'] < limit_date) | (df_res['Actualización Completo'].isna())]
        st.dataframe(get_display_df(c_df)[['Producto', 'País', 'Actualización Completo']], use_container_width=True, hide_index=True)

# --- 4. Prioridad (优先级页面) ---
elif menu == "Prioridad (优先级)":
    st.title("⚡ Prioridad")
    st.info("该模块尚未发布开发。")
