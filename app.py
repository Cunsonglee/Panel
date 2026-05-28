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
        # 读取从 GitHub 仓库加载的 Excel 主文件
        df = pd.read_excel(FILE_NAME)
    except FileNotFoundError:
        st.error(f"❌ No se encontró el archivo: {FILE_NAME}")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error al abrir el archivo Excel: {e}")
        st.stop()
    
    # 强制将日期列转换为 datetime 对象，以便进行日期差公式计算和日历挑选
    date_cols = ['Actualización Completo', 'Actualización regla']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # 基础文本去空格清洗
    df['País'] = df['País'].astype(str).str.strip()
    df['Producto'] = df['Producto'].astype(str).str.strip()
    
    # 统一并清洗国家与产品的状态
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

# 辅助函数：用于规范表格中的显示日期格式
def get_display_df(df_input):
    display_df = df_input.copy()
    for col in ['Actualización Completo', 'Actualización regla']:
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

    # 国家状态可编辑表格
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
    head_col1, head_col2 = st.columns([0.85, 0.15])
    with head_col1:
        st.title("📦 Productos - Detalles por Producto")
    
    with head_col2:
        st.write(" ") 
        if st.button("💾 Guardar Cambios", key="save_prod"):
            st.session_state.trigger_save_prod = True

    # 过滤掉空产品行
    df_prod = st.session_state.df[st.session_state.df['Producto'].notna() & (st.session_state.df['Producto'] != 'nan')].copy()
    
    # 过滤器
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

    # 保持两列日期为原生的 datetime 对象以供编辑
    display_cols = ['País', 'Estado_País', 'Producto', 'Estado_Producto', 
                    'Actualización Completo', 'Actualización regla', 'Nota_Producto']
    df_for_edit = df_prod[display_cols].copy()
    
    # 解锁日期和网页链接的可编辑数据表
    edited_prod = st.data_editor(
        df_for_edit,
        column_config={
            "Estado_Producto": st.column_config.SelectboxColumn("Estado Producto", options=valid_status, required=True),
            "Actualización Completo": st.column_config.DateColumn("Actualización Completo", format="YYYY-MM-DD"),
            "Actualización regla": st.column_config.DateColumn("Actualización regla", format="YYYY-MM-DD"),
            "Nota_Producto": st.column_config.LinkColumn("Nota_Producto", help="Haz clic para abrir el enlace", display_text="🔗 Abrir Enlace"),
            "Estado_País": st.column_config.Column("Estado País (Bloqueado)", disabled=True), 
            "País": st.column_config.Column(disabled=True),
            "Producto": st.column_config.Column(disabled=True),
        },
        use_container_width=True, hide_index=True, height=1000
    )

    if st.session_state.get('trigger_save_prod'):
        for _, row in edited_prod.iterrows():
            mask = (st.session_state.df['Producto'] == row['Producto']) & (st.session_state.df['País'] == row['País'])
            st.session_state.df.loc[mask, 'Estado_Producto'] = row['Estado_Producto']
            st.session_state.df.loc[mask, 'Actualización Completo'] = pd.to_datetime(row['Actualización Completo']) if pd.notna(row['Actualización Completo']) else pd.NaT
            st.session_state.df.loc[mask, 'Actualización regla'] = pd.to_datetime(row['Actualización regla']) if pd.notna(row['Actualización regla']) else pd.NaT
            st.session_state.df.loc[mask, 'Nota_Producto'] = row['Nota_Producto']
            
        try:
            st.session_state.df.to_excel(FILE_NAME, index=False)
            st.success("¡Estados de producto guardados exitosamente!")
            st.cache_data.clear()
            del st.session_state.trigger_save_prod
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar: {e}")

# --- 3. Página de Resumen ---
elif menu == "Resumen":
    st.title("📊 Resumen - Alertas de Actualización")
    df_res = st.session_state.df[st.session_state.df['Producto'].notna() & (st.session_state.df['Producto'] != 'nan')].copy()
    limit_date = datetime.now() - timedelta(days=180)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("⚠️ Regla Vencida (> 6 meses)")
        r_df = df_res[(df_res['Actualización regla'] < limit_date) | (df_res['Actualización regla'].isna())]
        st.dataframe(get_display_df(r_df)[['Producto', 'País', 'Actualización regla']], use_container_width=True, hide_index=True)
    with col2:
        st.subheader("⚠️ Completo Vencido (> 6 meses)")
        c_df = df_res[(df_res['Actualización Completo'] < limit_date) | (df_res['Actualización Completo'].isna())]
        st.dataframe(get_display_df(c_df)[['Producto', 'País', 'Actualización Completo']], use_container_width=True, hide_index=True)

# --- 4. Página de Prioridad (优先级计算页面) ---
elif menu == "Prioridad":
    st.title("⚡ Prioridad - Matrix de Prioridades Automatizada")
    st.write("根据预设的复杂业务公式，系统已自动计算出所有产品组合的优先级得分，并默认按从大到小进行降序排列。")

    # 1. 复制一份计算专用的 DataFrame，防止污染基础 Session 状态
    df_calc = st.session_state.df[st.session_state.df['Producto'].notna() & (st.session_state.df['Producto'] != 'nan')].copy()

    # 2. 调节与筛选器功能（与 Productos 界面一致）
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
    # 3. 核心计算映射区域：请将下方的英文字母字符串替换为您 Excel 中对应的真实列标题名称！
    # =========================================================================
    COL_A = 'País'                    # 对应公式3, 4中用于条件分组统计的列 (如：A列为国家)
    COL_I = 'K (Conversión %)'           # 对应公式1中的 I 列数字
    COL_J = 'P (Point)'           # 对应公式1中的 J 列数字
    COL_K = 'E (Extra Keys)'           # 对应公式1中的 K 列数字
    COL_L = 'F (Documentos)'           # 对应公式1中的 L 列数字
    COL_M = 'L (Lógica Dinámica)'           # 对应公式1中的 M 列数字
    COL_N = 'S (Tipo de County details)'           # 对应公式1中的 N 列数字
    COL_O = 'M (Impacto Precio)'           # 对应公式1中的 O 列数字
    COL_P = 'P (Point)'           # 对应公式3中被条件求和的 P 列数字
    COL_Q = 'Última actualización parcial'     # 对应公式2中的 Q 列日期时间
    COL_R = 'Última actualización completa'  # 对应公式2中的 R 列日期时间
    COL_S = 'Factor de Tiempo'           # 对应公式5中的 S 列数字
    COL_T = 'Score Total País'           # 对应公式5中的 T 列数字
    COL_U = 'Cantidad Prod'           # 对应公式5中的 U 列数字
    # =========================================================================

    # 自动安全检查与类型强转（防止 Excel 中夹杂的文本字符破坏数值公式计算）
    numeric_fields = [COL_I, COL_J, COL_K, COL_L, COL_M, COL_N, COL_O, COL_P, COL_S, COL_T, COL_U]
    for col in numeric_fields:
        if col in df_calc.columns and col not in ['Actualización Completo', 'Actualización regla', 'País', 'Producto']:
            df_calc[col] = pd.to_numeric(df_calc[col], errors='coerce').fillna(0)

    try:
        # ---- 【公式 1 代码化实现】 ----
        # =(SI(I4=0; 0; SI(I4<=100; 1; SI(I4<=1000; 3; SI(I4<=10000; 6; 10)))) * (1 + J4)) * ((1 + SI(K4<=20; 1; ... )))
        cond_I = [df_calc[COL_I] == 0, df_calc[COL_I] <= 100, df_calc[COL_I] <= 1000, df_calc[COL_I] <= 10000]
        score_I = np.select(cond_I, [0, 1, 3, 6], default=10)
        
        score_K = np.select([df_calc[COL_K] <= 20, df_calc[COL_K] <= 40], [1, 3], default=5)
        score_L = np.select([df_calc[COL_L] <= 4, df_calc[COL_L] <= 6], [2, 4], default=6)
        
        formula_1_res = (score_I * (1 + df_calc[COL_J])) * ((1 + score_K + score_L + df_calc[COL_M] * 5) * (df_calc[COL_N] * df_calc[COL_O]))

        # ---- 【公式 2 代码化实现】 ----
        # =(SI(R4=""; 730; HOY()-R4) * 1) + (SI(O(Q4=""; R4>Q4); SI(R4=""; 730; HOY()-R4); HOY()-Q4) * 0,3)
        today_date = pd.to_datetime(datetime.now().date())
        
        # 计算距离今天的具体天数差，如果原本日期为空则默认赋予 730 天
        days_R = (today_date - pd.to_datetime(df_calc[COL_R], errors='coerce')).dt.days.fillna(730)
        days_Q = (today_date - pd.to_datetime(df_calc[COL_Q], errors='coerce')).dt.days.fillna(730)
        
        condition_or = (df_calc[COL_Q].isna()) | (df_calc[COL_R] > df_calc[COL_Q])
        formula_2_sub = np.where(condition_or, days_R, days_Q)
        
        formula_2_res = (days_R * 1) + (formula_2_sub * 0.3)

        # ---- 【公式 3 & 4 代码化实现 (SUMAR.SI & CONTAR.SI)】 ----
        # 计算 A 列中相同元素出现的次数，并将结果分发回原位置
        df_calc['CONTAR_SI_RES'] = df_calc.groupby(COL_A)[COL_A].transform('count')
        
        # 依据 A 列条件对 P 列求和（仅在 P 列存在于 Excel 中且为数值时生效，默认先注保留意保护）
        if COL_P in df_calc.columns:
            df_calc['SUMAR_SI_RES'] = df_calc.groupby(COL_A)[COL_P].transform('sum')

        # ---- 【公式 5 代码化实现】 ----
        # =T4 * (1 +LOG10(U4)) * (1 + (S4 / 90))
        # 使用 .clip(lower=1) 避免对数 log10(0) 或负数引发系统级运行时报错
        formula_5_res = df_calc[COL_T] * (1 + np.log10(df_calc[COL_U].clip(lower=1))) * (1 + (df_calc[COL_S] / 90))

        # 4. 将计算出的核心综合指标塞入展现表格
        df_calc['Prioridad得分'] = formula_5_res

        # 5. 按照用户需求：提炼出“国家名”、“国家产品”、“优先级的数字大小”三列，并默认从大到小降序排列
        df_priority_view = df_calc[['País', 'Producto', 'Prioridad得分']].sort_values(by='Prioridad得分', ascending=False)

        # 6. 渲染前端高级数据表格视图
        st.subheader("🔥 实时优先级排期视图 (默认降序排序)")
        st.dataframe(
            df_priority_view,
            column_config={
                "País": st.column_config.Column("国家名称"),
                "Producto": st.column_config.Column("国家产品"),
                "Prioridad得分": st.column_config.NumberColumn("优先级得分 (Score)", format="%.2f"),
            },
            use_container_width=True,
            hide_index=True,
            height=800
        )

    except Exception as error:
        st.error(f"⚠️ 优先级矩阵公式计算失败。原因通常是配置文件中的列名称与实际 Excel 文件不匹配，或计算列包含了非数字文本。")
        st.info(f"详细错误调试日志: {error}")
        st.warning("💡 请在代码第 140 行到 154 行之间，将类似 'Col_I_Ejemplo' 的变量名修改为您 `Priority (1).xlsx` 表格中真正的第一行标题名字。")
