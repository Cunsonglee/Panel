import streamlit as st
import pandas as pd
import os
from datetime import date

# 页面配置
st.set_page_config(page_title="Panel Maestro Países & Productos", layout="wide")

# ==================== 数据初始化与保存逻辑 ====================
MASTER_FILE = "Vista Maestra.csv"

def save_master(df):
    """保存主表数据"""
    df_save = df.copy()
    # 保持日期格式为标准字符串存储
    for col in ['Actualización Completo', 'Actualización regla']:
        if col in df_save.columns:
            df_save[col] = pd.to_datetime(df_save[col], errors='coerce').dt.strftime('%Y-%m-%d').fillna("")
    
    df_save.to_csv(MASTER_FILE, index=False)
    st.session_state["df_master"] = df

def init_data():
    """初始化加载主表"""
    if "df_master" not in st.session_state:
        if os.path.exists(MASTER_FILE):
            df = pd.read_csv(MASTER_FILE)
            # 转换日期列
            for col in ['Actualización Completo', 'Actualización regla']:
                if col in df.columns:
                    temp = pd.to_datetime(df[col], errors='coerce')
                    df[col] = [d.date() if pd.notnull(d) else None for d in temp]
            st.session_state["df_master"] = df
        else:
            st.error(f"⚠️ No se encontró el archivo: {MASTER_FILE}.")

init_data()

def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

# 左侧导航
st.sidebar.title("Panel Maestro")
view = st.sidebar.radio("Menú", ["Países", "Productos", "Prioridad", "Resumen"])

# 获取当前内存中的主表
df_master = st.session_state["df_master"]

# ==================== 视图 1: PAÍSES (全部展示) ====================
if view == "Países":
    st.title("Gestión de Países")
    st.info("💡 Se muestran todos los países. Los cambios aquí actualizarán todas las filas de productos asociadas.")
    
    # 提取国家维度的核心列
    country_cols = ['País', 'ISO3', 'Estado_País', 'Implementación', 'Nota_País']
    df_countries = df_master[country_cols].drop_duplicates(subset=['País']).copy()
    
    edited_countries = st.data_editor(
        df_countries,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Estado_País": st.column_config.SelectboxColumn(
                "Estado País", options=["Activo", "Inactivo", "No implementado"], required=True
            )
        }
    )
    
    if not edited_countries.equals(df_countries):
        # 批量更新主表
        for index, row in edited_countries.iterrows():
            pais_name = row['País']
            df_master.loc[df_master['País'] == pais_name, country_cols] = row.values
        save_master(df_master)
        st.success("¡Países actualizados!")
        st.rerun()

# ==================== 视图 2: PRODUCTOS (精简列 & 全部展示) ====================
elif view == "Productos":
    st.title("Listado de Productos")
    
    # 指定展示的 9 列
    target_cols = [
        'País', 'ISO3', 'Estado_País', 'Estado_Producto', 
        'Implementación', 'Producto', 'Actualización Completo', 
        'Actualización regla', 'Nota_Producto'
    ]
    
    # 只提取存在的列，防止报错
    df_display = df_master[[c for c in target_cols if c in df_master.columns]].copy()

    edited_display = st.data_editor(
        df_display,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Estado_Producto": st.column_config.SelectboxColumn("Estado Producto", options=["Activo", "Inactivo"]),
            "Estado_País": st.column_config.SelectboxColumn("Estado País", options=["Activo", "Inactivo", "No implementado"]),
            "Actualización Completo": st.column_config.DateColumn("Actualización Completo", format="DD/MM/YYYY"),
            "Actualización regla": st.column_config.DateColumn("Actualización regla", format="DD/MM/YYYY")
        }
    )
    
    if not edited_display.equals(df_display):
        # 将修改合并回主表
        df_master.update(edited_display)
        # 如果有新行，这里也需要处理，但通常建议在主表直接操作
        save_master(df_master)
        st.success("¡Base de productos actualizada!")
        st.rerun()

# ==================== 视图 3: PRIORIDAD (Cálculo Refinado) ====================
elif view == "Prioridad":
    st.title("Cálculo de Prioridad y Mantenimiento")
    
    # 1. 业务逻辑说明 (提取自 Word 文档)
    with st.expander("📖 Metodología de Cálculo (Basado en documentación oficial)"):
        st.markdown("""
        * **C1 - Clientes/Año:** Basado en el volumen de visas tramitadas (reporte Stroper). Idealmente actualización semanal.
        * **C2 - Nº Productos:** Cantidad de productos o variaciones de visado por país.
        * **C3 - Complejidad del Formulario:** No contabiliza todas las preguntas, sino la **combinación máxima posible** de cada formulario, sumado a la media de documentos requeridos (Ej: India requiere un cálculo especial).
        * **C4 - Recencia:** Días transcurridos desde la última revisión o finalización de tarea en Jira.
        """)
    
    # 2. 权重设定 (Ajuste de Pesos)
    st.markdown("### ⚖️ Ajuste de Pesos (W)")
    w_col1, w_col2, w_col3, w_col4 = st.columns(4)
    w_c1 = w_col1.number_input("C1: Clientes (W1)", value=0.45, step=0.05)
    w_c2 = w_col2.number_input("C2: Productos (W2)", value=0.15, step=0.05)
    w_c3 = w_col3.number_input("C3: Complejidad (W3)", value=0.25, step=0.05)
    w_c4 = w_col4.number_input("C4: Recencia (W4)", value=0.15, step=0.05)
    
    # 3. 提取相关列
    # 我们定义理想的列名。如果你的 CSV 里列名不同（比如叫 Clientes/año），程序会自动映射或忽略
    prio_cols = [
        'País', 'ISO3', 'Estado_País', 
        'clientes365', 'n_productos', # C1 y C2
        'n_preguntas', 'n_documentos', 'complejidadScore', # C3 desglosado
        'ultima_revision', 'daysSince' # C4
    ]
    
    # 仅提取存在于主表中的列，防止报错
    exist_cols = [c for c in prio_cols if c in df_master.columns]
    
    # 确保最基础的列在计算名单里，如果缺少就用 0 补全
    df_prio = df_master[exist_cols].drop_duplicates(subset=['País']).copy()
    
    for required_col in ['clientes365', 'n_productos', 'complejidadScore', 'daysSince']:
        if required_col not in df_prio.columns:
            df_prio[required_col] = 0
            
    # 4. 核心分数计算
    def get_scores(df):
        temp = df.copy()
        
        # 确保用于计算的列都是数字格式
        for c in ['clientes365', 'n_productos', 'complejidadScore', 'daysSince']:
            temp[c] = pd.to_numeric(temp[c], errors='coerce').fillna(0)
        
        # 完整公式：(C1*W1) + (C2*W2) + (C3*W3) - (C4*W4)
        # 注意：这里天数 (daysSince) 除以 180 是为了归一化惩罚系数
        s01 = (
            (temp['clientes365'] * w_c1) + 
            (temp['n_productos'] * w_c2) + 
            (temp['complejidadScore'] * w_c3) - 
            (temp['daysSince'] / 180 * w_c4)
        )
        
        temp['score100'] = (s01 * 100).round()
        
        # 阈值划分
        def assign_p(s):
            if s >= 80: return "P0 (Urgente)"
            if s >= 60: return "P1 (Alto)"
            if s >= 40: return "P2 (Medio)"
            return "P3 (Bajo)"
        
        temp['nivel'] = temp['score100'].apply(assign_p)
        return temp

    df_prio_calc = get_scores(df_prio).sort_values("score100", ascending=False)
    
    # 5. 界面展示
    st.markdown("### 📊 Tabla de Prioridades")
    
    # 将需要锁定的计算列和基础列设为 disabled
    disabled_columns = ["score100", "nivel", "País", "ISO3"]
    
    edited_prio = st.data_editor(
        df_prio_calc,
        use_container_width=True,
        hide_index=True,
        disabled=disabled_columns,
        column_config={
            "Estado_País": st.column_config.SelectboxColumn("Estado País", options=["Activo", "Inactivo", "No implementado"]),
            "score100": st.column_config.ProgressColumn("Score", format="%f", min_value=0, max_value=100),
            "ultima_revision": st.column_config.DateColumn("Última Revisión", format="DD/MM/YYYY")
        }
    )

    # 6. 保存逻辑
    if not edited_prio.equals(df_prio_calc):
        # 去掉计算出的列，防止污染源数据
        clean_prio = edited_prio.drop(columns=["score100", "nivel"], errors='ignore')
        
        # 匹配国家并更新主表
        for index, row in clean_prio.iterrows():
            pais_name = row['País']
            update_cols = clean_prio.columns
            df_master.loc[df_master['País'] == pais_name, update_cols] = row.values
            
        save_master(df_master)
        st.success("¡Métricas de prioridad actualizadas y guardadas en el Maestro!")
        st.rerun()

# ==================== 视图 4: RESUMEN ====================
elif view == "Resumen":
    st.title("Resumen del Panel")

    df_unique = df_master.drop_duplicates(subset=['País'])
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Países Únicos", len(df_unique))
    m2.metric("Países Activos", len(df_unique[df_unique['Estado_País'] == 'Activo']))
    m3.metric("Total Productos", len(df_master[df_master['Producto'].notna()]))

    st.divider()

    # 优先级分布计算
    calc_df = df_unique.copy()
    for c in ['clientes365', 'complejidadScore', 'daysSince']:
        calc_df[c] = pd.to_numeric(calc_df[c], errors='coerce').fillna(0)
    
    s01 = (calc_df['clientes365']*0.45 + calc_df['complejidadScore']*0.25 - (calc_df['daysSince']/180)*0.15)
    calc_df['score100'] = (s01 * 100).round()
    calc_df['nivel'] = calc_df['score100'].apply(lambda s: "P0" if s>=80 else ("P1" if s>=60 else ("P2" if s>=40 else "P3")))
    
    nivel_counts = calc_df['nivel'].value_counts().reindex(["P0", "P1", "P2", "P3"], fill_value=0)
    st.bar_chart(nivel_counts)

    n1, n2, n3, n4 = st.columns(4)
    n1.metric("P0", nivel_counts["P0"])
    n2.metric("P1", nivel_counts["P1"])
    n3.metric("P2", nivel_counts["P2"])
    n4.metric("P3", nivel_counts["P3"])
