import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 页面基础配置
st.set_page_config(page_title="Panel de Control v2", layout="wide")

# 你在 GitHub 仓库中的统一主文件名称
FILE_NAME = 'Priority (1).xlsx'

# 核心数据加载函数
@st.cache_data
def load_data():
    try:
        df = pd.read_excel(FILE_NAME)
    except FileNotFoundError:
        st.error(f"❌ No se encontró el archivo: {FILE_NAME}")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error al abrir el archivo Excel: {e}")
        st.stop()
    
    # 强制将日期列转换为 datetime 对象
    date_cols = ['Última actualización completa', 'Última actualización parcial', 'Actualización Completo', 'Actualización regla']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    if 'País' in df.columns:
        df['País'] = df['País'].astype(str).str.strip()
    if 'Producto' in df.columns:
        df['Producto'] = df['Producto'].astype(str).str.strip()
    
    status_map = {'nan': 'No implementado', 'Sin Estado': 'No implementado', 'None': 'No implementado'}
    valid_options = ["Activo", "Inactivo", "No implementado"]
    
    for col in ['Estado_País', 'Estado_Producto']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().replace(status_map).fillna('No implementado')
            df[col] = df[col].apply(lambda x: x if x in valid_options else "No implementado")
    
    return df

# 初始化 Streamlit 全局会话状态
if 'df' not in st.session_state:
    st.session_state.df = load_data()

valid_status = ["Activo", "Inactivo", "No implementado"]

# 规范显示日期的辅助函数
def get_display_df(df_input):
    display_df = df_input.copy()
    date_cols = ['Última actualización completa', 'Última actualización parcial', 'Actualización Completo', 'Actualización regla']
    for col in date_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].dt.strftime('%d-%m-%Y').fillna("")
    return display_df

# 侧边栏菜单导航
menu = st.sidebar.radio("Menú", ["Países", "Productos", "Resumen", "Prioridad"])

# --- 1. Página de Países ---
if menu == "Países":
    head_col1, head_col2 = st.columns([0.85, 0.15])
    with head_col1:
        st.title("🌍 Países - Estadísticas por Nación")
    
    stats = st.session_state.df.groupby(['País', 'ISO3']).apply(lambda x: pd.Series({
        'Estado_País': x['Estado_País'].iloc[0] if 'Estado_País' in x.columns else "No implementado",
        'Activos': ((x['Estado_Producto'] == 'Activo') & (x['Producto'].notna())).sum() if 'Estado_Producto' in x.columns else 0,
        'Inactivos': ((x['Estado_Producto'] == 'Inactivo') & (x['Producto'].notna())).sum() if 'Estado_Producto' in x.columns else 0
    })).reset_index()

    all_countries = sorted([c for c in st.session_state.df['País'].unique() if c.lower() != 'nan'])
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_countries = st.multiselect("Seleccionar País", options=all_countries)
    with col_f2:
        status_filter = st.multiselect("Filtrar por Estado de País", options=valid_status)

    if selected_countries:
        stats = stats[stats['País'].isin(selected_countries)]
    if status_filter:
        stats = stats[stats['Estado_País'].isin(status_filter)]

    with head_col2:
        st.write(" ") 
        if st.button("💾 Guardar Cambios", key="save_paises"):
            st.session_state.trigger_save_paises = True

    edited_paises = st.data_editor(
        stats,
        column_config={
            "Estado_País": st.column_config.SelectboxColumn("Estado País", options=valid_status, required=True),
            "País": st.column_config.Column(disabled=True),
            "ISO3": st.column_config.Column(disabled=True),
            "Activos": st.column_config.Column(disabled=True),
            "Inactivos": st.column_config.Column(disabled=True),
        },
        use_container_width=True, hide_index=True, height=800
    )

    if st.session_state.get('trigger_save_paises'):
        for _, row in edited_paises.iterrows():
            st.session_state.df.loc[st.session_state.df['País'] == row['País'], 'Estado_País'] = row['Estado_País']
        
        try:
            st.session_state.df.to_excel(FILE_NAME, index=False)
            st.success("¡Estados de país guardados exitosamente!")
            st.cache_data.clear()
            del st.session_state.trigger_save_paises
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar: {e}")

# --- 2. Página de Productos ---
elif menu == "Productos":
    st.title("📦 Productos - Detalles por Producto")
    
    # -------------------------------------------------------------------------
    # 【上传 Jira 文件自动更新模块】
    # -------------------------------------------------------------------------
    st.markdown("### 📥 Sincronización Automática con Jira")
    uploaded_file = st.file_uploader("请上传由 Jira 导出的 CSV（分号分隔）或 Excel 文件：", type=["csv", "xlsx"])
    
    # 使用 Session State 记录被 Jira 更新的（国家，产品）键值对
    if 'modified_rows' not in st.session_state:
        st.session_state.modified_rows = []

    if uploaded_file is not None:
        try:
            # 自动识别格式并读取
            if uploaded_file.name.endswith('.csv'):
                jira_df = pd.read_csv(uploaded_file, sep=None, engine='python')
            else:
                jira_df = pd.read_excel(uploaded_file)
            
            # 清洗列标题的空格
            jira_df.columns = jira_df.columns.str.strip()
            
            # 检查 Jira 核心必备列
            required_jira_cols = ['Clave de incidencia', 'Actualizada', 'Resumen', 'ID de la incidencia']
            if all(col in jira_df.columns for col in required_jira_cols):
                
                if st.button("⚡ 预解析并执行 Jira 规则匹配"):
                    st.session_state.modified_rows = [] # 重置上一次的修改高亮标记
                    
                    # 遍历我们主表格数据库（Priority (1).xlsx）里的每一行
                    for index, row in st.session_state.df.iterrows():
                        p_name = str(row['Producto']).strip()
                        c_name = str(row['País']).strip()
                        
                        if pd.isna(row['Producto']) or p_name == 'nan':
                            continue
                        
                        # 第一步：根据国家名称过滤 Jira 任务（因为 Resumen 里总有国家名）
                        matched_jira = jira_df[
                            jira_df['Resumen'].astype(str).str.contains(c_name, case=False, na=False)
                        ]
                        
                        if not matched_jira.empty:
                            # 拿到最上面最新的一条 Jira 任务
                            jira_row = matched_jira.iloc[0]
                            
                            # 提取并解析更新日期（形如 28/05/2026 7:54 提取前段日期）
                            raw_date = str(jira_row['Actualizada']).split()[0]
                            parsed_date = pd.to_datetime(raw_date, dayfirst=True, errors='coerce')
                            
                            # 自动生成固定的 Atlassian 任务超链接
                            clave = str(jira_row['Clave de incidencia']).strip()
                            new_link = f"https://visagov.atlassian.net/browse/{clave}"
                            
                            # 获取 ID de la incidencia 值用于规则判定
                            jira_id_val = jira_row['ID de la incidencia']
                            is_empty_id = pd.isna(jira_id_val) or str(jira_id_val).strip() == "" or str(jira_id_val).lower() == "nan"
                            
                            # 【严格执行用户的判定规则】：
                            if is_empty_id:
                                # 1. ID 为空，对应更新：Última actualización completa
                                st.session_state.df.at[index, 'Última actualización completa'] = parsed_date
                            else:
                                # 2. ID 不为空（有产品标记），对应更新：Última actualización parcial
                                st.session_state.df.at[index, 'Última actualización parcial'] = parsed_date
                            
                            # 统一更新链接列
                            st.session_state.df.at[index, 'Nota_Producto'] = new_link
                            
                            # 将被修改的这行存入高亮置顶缓存
                            st.session_state.modified_rows.append((c_name, p_name))
                            
                    st.success(f"🎉 成功完成规则筛选！共发现 {len(st.session_state.modified_rows)} 项数据变更，已在下方用蓝色高亮并为您置顶。请核对后点击下方 'Guardar Cambios' 保存。")
            else:
                st.error(f"❌ 上传的文件格式不正确。必须包含以下列名：{required_jira_cols}")
        except Exception as e:
            st.error(f"处理文件时发生意外错误: {e}")

    st.write("---")

    # 核心数据管理操作表头
    head_col1, head_col2 = st.columns([0.85, 0.15])
    with head_col1:
        st.subheader("📋 产品详细数据列表")
    with head_col2:
        st.write(" ") 
        if st.button("💾 Guardar Cambios", key="save_prod"):
            st.session_state.trigger_save_prod = True

    # 主表基础过滤
    df_prod = st.session_state.df[st.session_state.df['Producto'].notna() & (st.session_state.df['Producto'] != 'nan')].copy()
    
    # 前端三大过滤器
    c1, c2, c3 = st.columns(3)
    with c1:
        f_country = st.multiselect("Filtrar por País", options=sorted(df_prod['País'].unique()))
    with c2:
        f_p_status = st.multiselect("Filtrar por Estado de Producto", options=valid_status)
    with c3:
        f_c_status = st.multiselect("Filtrar por Estado de País", options=valid_status)
    
    if f_country: df_prod = df_prod[df_prod['País'].isin(f_country)]
    if f_p_status: df_prod = df_prod[df_prod['Estado_Producto'].isin(f_p_status)]
    if f_c_status: df_prod = df_prod[df_prod['Estado_País'].isin(f_c_status)]

    # -------------------------------------------------------------------------
    # 【置顶逻辑控制】：让被 Jira 更新修改的行，Is_Modified 为 True，并排序到最上方
    # -------------------------------------------------------------------------
    if st.session_state.modified_rows:
        df_prod['Is_Modified'] = df_prod.apply(lambda r: (str(r['País']).strip(), str(r['Producto']).strip()) in st.session_state.modified_rows, axis=1)
        df_prod = df_prod.sort_values(by='Is_Modified', ascending=False)
    else:
        df_prod['Is_Modified'] = False

    display_cols = ['País', 'Estado_País', 'Producto', 'Estado_Producto', 
                    'Última actualización completa', 'Última actualización parcial', 'Nota_Producto', 'Is_Modified']
    df_for_edit = df_prod[display_cols].copy()
    
    # -------------------------------------------------------------------------
    # 【蓝色标记高亮样式映射：背景淡蓝，字体深蓝加粗】
    # -------------------------------------------------------------------------
    def style_blue_highlight(row):
        if row['Is_Modified'] == True:
            return ['background-color: #DCE6F1; color: #1F497D; font-weight: bold;'] * len(row)
        return [''] * len(row)
    
    styled_df = df_for_edit.style.apply(style_blue_highlight, axis=1)

    # 前端高级可编辑数据表组件
    edited_prod = st.data_editor(
        styled_df,
        column_config={
            "Estado_Producto": st.column_config.SelectboxColumn("Estado Producto", options=valid_status, required=True),
            "Última actualización completa": st.column_config.DateColumn("Última actualización completa", format="YYYY-MM-DD"),
            "Última actualización parcial": st.column_config.DateColumn("Última actualización parcial", format="YYYY-MM-DD"),
            "Nota_Producto": st.column_config.LinkColumn("Nota_Producto", help="Haz clic para abrir el enlace", display_text="🔗 Abrir Enlace"),
            "Estado_País": st.column_config.Column("Estado País (Bloqueado)", disabled=True), 
            "País": st.column_config.Column(disabled=True),
            "Producto": st.column_config.Column(disabled=True),
            "Is_Modified": st.column_config.Column("已被 Jira 更新", disabled=True),
        },
        use_container_width=True, hide_index=True, height=1000
    )

    # 真正执行 Guardar Cambios 写入 Excel 块
    if st.session_state.get('trigger_save_prod'):
        for _, row in pd.DataFrame(edited_prod).iterrows():
            mask = (st.session_state.df['Producto'] == row['Producto']) & (st.session_state.df['País'] == row['País'])
            if 'Estado_Producto' in row: st.session_state.df.loc[mask, 'Estado_Producto'] = row['Estado_Producto']
            if 'Última actualización completa' in row: st.session_state.df.loc[mask, 'Última actualización completa'] = pd.to_datetime(row['Última actualización completa']) if pd.notna(row['Última actualización completa']) else pd.NaT
            if 'Última actualización parcial' in row: st.session_state.df.loc[mask, 'Última actualización parcial'] = pd.to_datetime(row['Última actualización parcial']) if pd.notna(row['Última actualización parcial']) else pd.NaT
            if 'Nota_Producto' in row: st.session_state.df.loc[mask, 'Nota_Producto'] = row['Nota_Producto']
            
        try:
            st.session_state.df.to_excel(FILE_NAME, index=False)
            st.success("¡Los cambios se han guardado permanentemente en la base de datos Excel!")
            st.session_state.modified_rows = [] # 写入后清空高亮缓存
            st.cache_data.clear()
            del st.session_state.trigger_save_prod
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar en el archivo Excel: {e}")

# --- 3. Página de Resumen ---
elif menu == "Resumen":
    st.title("📊 Resumen - Alertas de Actualización")
    df_res = st.session_state.df[st.session_state.df['Producto'].notna() & (st.session_state.df['Producto'] != 'nan')].copy()
    limit_date = datetime.now() - timedelta(days=180)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("⚠️ Regla Vencida (> 6 meses)")
        r_col = 'Última actualización parcial' if 'Última actualización parcial' in df_res.columns else 'Actualización regla'
        r_df = df_res[(df_res[r_col] < limit_date) | (df_res[r_col].isna())]
        st.dataframe(get_display_df(r_df)[['Producto', 'País', r_col]], use_container_width=True, hide_index=True)
    with col2:
        st.subheader("⚠️ Completo Vencido (> 6 meses)")
        c_col = 'Última actualización completa' if 'Última actualización completa' in df_res.columns else 'Actualización Completo'
        c_df = df_res[(df_res[c_col] < limit_date) | (df_res[c_col].isna())]
        st.dataframe(get_display_df(c_df)[['Producto', 'País', c_col]], use_container_width=True, hide_index=True)

# --- 4. Página de Prioridad ---
elif menu == "Prioridad":
    # 这里保持上一步为您定制的 5 个公式链式递进排序逻辑即可
    st.title("⚡ Prioridad - Matriz de Prioridades Automatizada")
    # ...
