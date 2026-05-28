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

# --- 4. Página de Prioridad (优先级计算页面) ---
elif menu == "Prioridad":
    st.title("⚡ Prioridad - Matriz de Prioridades Automatizada")
    st.write("根据您提供的严密嵌套公式链，系统实时在后台进行递进式矩阵运算，并默认按最终得分从大到小降序排列。")

    # 1. 复制一份计算专用的 DataFrame，防止污染基础数据状态
    df_calc = st.session_state.df[st.session_state.df['Producto'].notna() & (st.session_state.df['Producto'] != 'nan')].copy()

    # 2. 调节与筛选器功能（与其他界面保持一致）
    c1, c2, c3 = st.columns(3)
    with c1:
        f_country = st.multiselect("Filtrar por País", options=sorted(df_calc['País'].unique()), key="prioridad_f_country")
    with c2:
        f_p_status = st.multiselect("Filtrar por Estado de Producto", options=valid_status, key="prioridad_f_p_status")
    with c3:
        f_c_status = st.multiselect("Filtrar por Estado de País", options=valid_status, key="prioridad_f_c_status")
    
    if f_country: df_calc = df_calc[df_calc['País'].isin(f_country)]
    if f_p_status: df_calc = df_calc[df_calc['Estado_Producto'].isin(f_p_status)]
    if f_c_status: df_calc = df_calc[df_calc['Estado_País'].isin(f_c_status)]

    # =========================================================================
    # 3. 完美绑定：您提供的真实列名
    # =========================================================================
    COL_A = 'País'                             # 对应用于条件分组（SUMAR.SI / CONTAR.SI）的列
    COL_I = 'K (Conversión %)'                 # 公式1的 I 输入
    COL_J = 'P (Point)'                        # 公式1的 J 输入（注意：公式1会产出全新的COL_P，不要冲突）
    COL_K = 'E (Extra Keys)'                   # 公式1的 K 输入
    COL_L = 'F (Documentos)'                   # 公式1的 L 输入
    COL_M = 'L (Lógica Dinámica)'              # 公式1的 M 输入
    COL_N = 'S (Tipo de County details)'       # 公式1的 N 输入
    COL_O = 'M (Impacto Precio)'               # 公式1的 O 输入
    
    COL_Q = 'Última actualización parcial'      # 公式2的 Q 输入（日期时间）
    COL_R = 'Última actualización completa'     # 公式2的 R 输入（日期时间）
    
    COL_S_name = 'Factor de Tiempo'            # 公式2最终产出的新列名（取代原表格数值）
    COL_T_name = 'Score Total País'            # 公式3最终产出的新列名（取代原表格数值）
    COL_U_name = 'Cantidad Prod'               # 公式4最终产出的新列名（取代原表格数值）
    # =========================================================================

    # 将涉及数字运算的列强转为数值型，防止夹杂非法字符
    input_fields = [COL_I, COL_J, COL_K, COL_L, COL_M, COL_N, COL_O]
    for col in input_fields:
        if col in df_calc.columns:
            df_calc[col] = pd.to_numeric(df_calc[col], errors='coerce').fillna(0)

    try:
        # ---------------------------------------------------------------------
        # 递进层级一：【计算公式 1 ➡ 生成全新的 COL_P】
        # =(SI(I4=0; 0; SI(I4<=100; 1; SI(I4<=1000; 3; SI(I4<=10000; 6; 10)))) * (1 + J4)) * ((1 + SI(K4<=20; 1; ...)))
        # ---------------------------------------------------------------------
        cond_I = [df_calc[COL_I] == 0, df_calc[df_calc.columns[0]] == "NEVER_MATCH_THIS_STUB", df_calc[COL_I] <= 100, df_calc[COL_I] <= 1000, df_calc[COL_I] <= 10000]
        # 修复逻辑，精准映射阶梯评分
        cond_I_actual = [df_calc[COL_I] == 0, df_calc[COL_I] <= 100, df_calc[COL_I] <= 1000, df_calc[COL_I] <= 10000]
        score_I = np.select(cond_I_actual, [0, 1, 3, 6], default=10)
        
        score_K = np.select([df_calc[COL_K] <= 20, df_calc[COL_K] <= 40], [1, 3], default=5)
        score_L = np.select([df_calc[COL_L] <= 4, df_calc[COL_L] <= 6], [2, 4], default=6)
        
        # 算出的结果直接代表最新的 COL_P 变量 (P (Point))，不再读取表格里的原数值
        NEW_COL_P = (score_I * (1 + df_calc[COL_J])) * ((1 + score_K + score_L + df_calc[COL_M] * 5) * (df_calc[COL_N] * df_calc[COL_O]))
        df_calc['CALC_P_POINT'] = NEW_COL_P

        # ---------------------------------------------------------------------
        # 递进层级二：【计算公式 2 ➡ 生成全新的 COL_S】
        # =(SI(R4=""; 730; HOY()-R4) * 1) + (SI(O(Q4=""; R4>Q4); SI(R4=""; 730; HOY()-R4); HOY()-Q4) * 0,3)
        # ---------------------------------------------------------------------
        today_date = pd.to_datetime(datetime.now().date())
        
        days_R = (today_date - pd.to_datetime(df_calc[COL_R], errors='coerce')).dt.days.fillna(730)
        days_Q = (today_date - pd.to_datetime(df_calc[COL_Q], errors='coerce')).dt.days.fillna(730)
        
        condition_or = (df_calc[COL_Q].isna()) | (df_calc[COL_R] > df_calc[COL_Q])
        formula_2_sub = np.where(condition_or, days_R, days_Q)
        
        # 计算结果直接代表最新的 COL_S (Factor de Tiempo)
        NEW_COL_S = (days_R * 1) + (formula_2_sub * 0.3)
        df_calc['CALC_S_FACTOR'] = NEW_COL_S

        # ---------------------------------------------------------------------
        # 递进层级三：【计算公式 4 ➡ 生成全新的 COL_U】
        # =CONTAR.SI(A:A; A4)
        # ---------------------------------------------------------------------
        NEW_COL_U = df_calc.groupby(COL_A)[COL_A].transform('count')
        df_calc['CALC_U_CANTIDAD'] = NEW_COL_U

        # ---------------------------------------------------------------------
        # 递进层级四：【计算公式 3 ➡ 生成全新的 COL_T】
        # =SUMAR.SI(A:A; A4; P:P) ⚠️ 注意：这里的 P:P 必须使用上面刚刚算出来的全新 NEW_COL_P
        # ---------------------------------------------------------------------
        NEW_COL_T = df_calc.groupby(COL_A)['CALC_P_POINT'].transform('sum')
        df_calc['CALC_T_SCORE'] = NEW_COL_T

        # ---------------------------------------------------------------------
        # 递进层级五：【计算公式 5 ➡ 算出最终的优先级总得分 COL_V】
        # =T4 * (1 + LOG10(U4)) * (1 + (S4 / 90))
        # ⚠️ 必须采用刚刚上面新鲜算出来的组件：T4 -> NEW_COL_T, U4 -> NEW_COL_U, S4 -> NEW_COL_S
        # ---------------------------------------------------------------------
        # 用 .clip(lower=1) 保护对数函数，避免 log10(0) 导致程序红屏崩溃
        FINAL_COL_V = df_calc['CALC_T_SCORE'] * (1 + np.log10(df_calc['CALC_U_CANTIDAD'].clip(lower=1))) * (1 + (df_calc['CALC_S_FACTOR'] / 90))
        df_calc['Final_Priority_Score'] = FINAL_COL_V

        # 4. 提取需要展示给用户的最终精简列，并默认按得分从高到低（降序）排序
        df_priority_view = df_calc[['País', 'Producto', 'Final_Priority_Score']].sort_values(by='Final_Priority_Score', ascending=False)

        # 5. 渲染展示表格
        st.subheader("🔥 全自动化优先级排期结果 (默认从大到小降序)")
        st.dataframe(
            df_priority_view,
            column_config={
                "País": st.column_config.Column("国家名称"),
                "Producto": st.column_config.Column("国家产品"),
                "Final_Priority_Score": st.column_config.NumberColumn("优先级综合得分 (公式5值)", format="%.2f"),
            },
            use_container_width=True,
            hide_index=True,
            height=800
        )

    except Exception as error:
        st.error(f"⚠️ 链式公式实时计算失败。请检查您的 Excel 文件表头是否与代码中的变量完全对齐。")
        st.info(f"系统报错调试日志: {error}")
