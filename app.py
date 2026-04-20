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

# ==================== 视图 3: PRIORIDAD (仅计算活跃产品) ====================
elif view == "Prioridad":
    st.title("Cálculo de Prioridad y Mantenimiento")
    
    with st.expander("📖 Metodología de Cálculo (Refinada)"):
        st.markdown("""
        * **C1 - Clientes/Año:** Volumen de visas tramitadas (Stroper).
        * **C2 - Nº Productos Activos:** (¡Automático!) Solo se cuentan los productos con estado **'Activo'** en la base maestra.
        * **C3 - Complejidad:** Basado en la combinación máxima de preguntas y documentos.
        * **C4 - Recencia:** Días desde la última actualización en Jira.
        """)
    
    st.markdown("### ⚖️ Ajuste de Pesos (W)")
    w_col1, w_col2, w_col3, w_col4 = st.columns(4)
    w_c1 = w_col1.number_input("C1: Clientes (W1)", value=0.45, step=0.05)
    w_c2 = w_col2.number_input("C2: Prod. Activos (W2)", value=0.15, step=0.05)
    w_c3 = w_col3.number_input("C3: Complejidad (W3)", value=0.25, step=0.05)
    w_c4 = w_col4.number_input("C4: Recencia (W4)", value=0.15, step=0.05)
    
    # 1. 提取基础列
    prio_cols = [
        'País', 'ISO3', 'Estado_País', 
        'clientes365', 'n_preguntas', 'n_documentos', 'complejidadScore', 
        'ultima_revision', 'daysSince' 
    ]
    
    exist_cols = [c for c in prio_cols if c in df_master.columns]
    df_prio = df_master[exist_cols].drop_duplicates(subset=['País']).copy()
    
    # ==========================================
    # 🚀 核心更新：仅统计 Estado_Producto == 'Activo' 的数量
    # ==========================================
    # 先筛选活跃产品
    df_activos_only = df_master[df_master['Estado_Producto'] == 'Activo']
    # 统计数量
    conteo_activos = df_activos_only.groupby('País')['Producto'].count().reset_index(name='n_productos')
    # 合并回优先级表，缺失的国家填充为 0
    df_prio = pd.merge(df_prio, conteo_activos, on='País', how='left')
    df_prio['n_productos'] = df_prio['n_productos'].fillna(0)
    
    # 2. 核心分数计算
    def get_scores(df):
        temp = df.copy()
        # 确保计算列为数值
        calc_cols = ['clientes365', 'n_productos', 'complejidadScore', 'daysSince']
        for c in calc_cols:
            temp[c] = pd.to_numeric(temp[c], errors='coerce').fillna(0)
        
        # 优先级公式
        s01 = (
            (temp['clientes365'] * w_c1) + 
            (temp['n_productos'] * w_c2) + 
            (temp['complejidadScore'] * w_c3) - 
            (temp['daysSince'] / 180 * w_c4)
        )
        
        temp['score100'] = (s01 * 100).round()
        
        def assign_p(s):
            if s >= 80: return "P0 (Urgente)"
            if s >= 60: return "P1 (Alto)"
            if s >= 40: return "P2 (Medio)"
            return "P3 (Bajo)"
        
        temp['nivel'] = temp['score100'].apply(assign_p)
        return temp

    df_prio_calc = get_scores(df_prio).sort_values("score100", ascending=False)
    
    # 3. 界面展示
    st.markdown("### 📊 Tabla de Prioridades")
    
    disabled_columns = ["score100", "nivel", "País", "ISO3", "n_productos"]
    
    edited_prio = st.data_editor(
        df_prio_calc,
        use_container_width=True,
        hide_index=True,
        disabled=disabled_columns,
        column_config={
            "Estado_País": st.column_config.SelectboxColumn("Estado País", options=["Activo", "Inactivo", "No implementado"]),
            "score100": st.column_config.ProgressColumn("Score", format="%d", min_value=0, max_value=100),
            "n_productos": st.column_config.NumberColumn("Prod. Activos (C2)", help="Contatización automática de productos 'Activo' en el Maestro")
        }
    )

    # 4. 保存逻辑 (保存时自动剔除动态计算列)
    if not edited_prio.equals(df_prio_calc):
        clean_prio = edited_prio.drop(columns=["score100", "nivel", "n_productos"], errors='ignore')
        for index, row in clean_prio.iterrows():
            pais_name = row['País']
            update_target = clean_prio.columns
            df_master.loc[df_master['País'] == pais_name, update_target] = row.values
            
        save_master(df_master)
        st.success("¡Métricas guardadas! El Score se ha recalculado basándose en productos activos.")
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
