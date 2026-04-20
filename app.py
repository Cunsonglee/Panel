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
    # 保持日期格式为标准字符串
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
view = st.sidebar.radio("Menú", ["Países (Base)", "Productos (Detalle)", "Prioridad (Cálculo)", "Resumen"])

# 获取当前内存中的主表
df_master = st.session_state["df_master"]

# ==================== 视图 1: PAÍSES (去重编辑) ====================
if view == "Países (Base)":
    st.title("Gestión de Países")
    st.info("💡 Los cambios aquí actualizarán todas las filas de productos asociadas.")
    
    country_cols = ['País', 'ISO3', 'Estado_País', 'Implementación', 'Nota_País']
    df_countries = df_master[country_cols].drop_duplicates(subset=['País']).copy()
    
    edited_countries = st.data_editor(
        df_countries,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Estado_País": st.column_config.SelectboxColumn(
                "Estado", options=["Activo", "Inactivo", "No implementado"], required=True
            )
        }
    )
    
    if not edited_countries.equals(df_countries):
        for index, row in edited_countries.iterrows():
            pais_name = row['País']
            df_master.loc[df_master['País'] == pais_name, country_cols] = row.values
        save_master(df_master)
        st.success("¡Datos de países actualizados!")
        st.rerun()

# ==================== 视图 2: PRODUCTOS (全量编辑) ====================
elif view == "Productos (Detalle)":
    st.title("Detalle de Productos")
    
    edited_master = st.data_editor(
        df_master,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Estado_Producto": st.column_config.SelectboxColumn("Estado Producto", options=["Activo", "Inactivo"]),
            "Actualización Completo": st.column_config.DateColumn("Actualización Completo", format="DD/MM/YYYY"),
            "Actualización regla": st.column_config.DateColumn("Actualización regla", format="DD/MM/YYYY"),
            "Estado_País": st.column_config.SelectboxColumn("Estado País", options=["Activo", "Inactivo", "No implementado"])
        }
    )
    
    if not edited_master.equals(df_master):
        save_master(edited_master)
        st.success("¡Base Maestra guardada!")
        st.rerun()

# ==================== 视图 3: PRIORIDAD (计算逻辑) ====================
elif view == "Prioridad (Cálculo)":
    st.title("Cálculo de Prioridades")
    
    w_col1, w_col2, w_col3, w_col4 = st.columns(4)
    w_c1 = w_col1.number_input("Clientes (W1)", value=0.45)
    w_c2 = w_col2.number_input("Productos (W2)", value=0.15) # 注意：这里可以根据需要加w_c2逻辑
    w_c3 = w_col3.number_input("Complejidad (C3)", value=0.25)
    w_c4 = w_col4.number_input("Recencia (C4)", value=0.15)
    
    prio_cols = ['País', 'ISO3', 'Estado_País', 'clientes365', 'complejidadScore', 'daysSince']
    df_prio = df_master[prio_cols].drop_duplicates(subset=['País']).copy()
    
    # 核心计算函数
    def apply_scoring(df):
        temp = df.copy()
        for c in ['clientes365', 'complejidadScore', 'daysSince']:
            temp[c] = pd.to_numeric(temp[c], errors='coerce').fillna(0)
        
        # HTML 原始公式逻辑
        score01 = (temp['clientes365']*w_c1 + temp['complejidadScore']*w_c3 - (temp['daysSince']/180)*w_c4)
        temp['score100'] = (score01 * 100).round()
        
        def assign_p(s):
            if s >= 80: return "P0"
            if s >= 60: return "P1"
            if s >= 40: return "P2"
            return "P3"
        
        temp['nivel'] = temp['score100'].apply(assign_p)
        return temp

    df_prio_result = apply_scoring(df_prio).sort_values("score100", ascending=False)
    
    st.data_editor(
        df_prio_result,
        use_container_width=True,
        hide_index=True,
        disabled=["score100", "nivel", "País", "ISO3"]
    )

# ==================== 视图 4: RESUMEN (带规格统计) ====================
elif view == "Resumen":
    st.title("Resumen del Panel")

    # 1. 顶部基础指标 (按国家去重)
    df_unique_countries = df_master.drop_duplicates(subset=['País'])
    
    total_p = len(df_unique_countries)
    p_activos = len(df_unique_countries[df_unique_countries['Estado_País'] == 'Activo'])
    total_prod = len(df_master[df_master['Producto'].notna()])

    m1, m2, m3 = st.columns(3)
    m1.metric("Países Únicos", total_p)
    m2.metric("Países Activos", p_activos)
    m3.metric("Total Productos", total_prod)

    st.divider()

    # 2. 优先级分布统计 (遵循 HTML 规格)
    st.subheader("🎯 Distribución de Prioridad (Niveles)")
    
    # 使用默认权重进行后台计算
    w_c1, w_c3, w_c4 = 0.45, 0.25, 0.15
    
    calc_df = df_unique_countries.copy()
    for c in ['clientes365', 'complejidadScore', 'daysSince']:
        calc_df[c] = pd.to_numeric(calc_df[c], errors='coerce').fillna(0)
        
    s01 = (calc_df['clientes365']*w_c1 + calc_df['complejidadScore']*w_c3 - (calc_df['daysSince']/180)*w_c4)
    calc_df['score100'] = (s01 * 100).round()

    def get_p_resumen(s):
        if s >= 80: return "P0"
        if s >= 60: return "P1"
        if s >= 40: return "P2"
        return "P3"

    calc_df['nivel'] = calc_df['score100'].apply(get_p_resumen)
    
    # 统计图表
    nivel_counts = calc_df['nivel'].value_counts().reindex(["P0", "P1", "P2", "P3"], fill_value=0)
    st.bar_chart(nivel_counts)

    # 3. 详细等级指标
    n1, n2, n3, n4 = st.columns(4)
    n1.metric("P0 (Crítico)", nivel_counts["P0"])
    n2.metric("P1 (Alto)", nivel_counts["P1"])
    n3.metric("P2 (Medio)", nivel_counts["P2"])
    n4.metric("P3 (Bajo)", nivel_counts["P3"])

    # 4. 高优先级预览
    st.subheader("🔥 Top 10 Países Prioritarios")
    top_10 = calc_df.sort_values("score100", ascending=False).head(10)
    st.dataframe(top_10[['País', 'ISO3', 'Estado_País', 'score100', 'nivel']], use_container_width=True, hide_index=True)
