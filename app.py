import streamlit as st
import pandas as pd
import os
from datetime import date

# 页面配置
st.set_page_config(page_title="Panel Maestro Países & Productos", layout="wide")

# ==================== 数据初始化与保存逻辑 ====================
MASTER_FILE = "Vista Maestra.csv"

def save_master(df):
    """保存主表数据，并确保日期格式正确"""
    df_save = df.copy()
    # 转换日期为字符串以便存储
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
            # 转换日期列为 date 对象
            for col in ['Actualización Completo', 'Actualización regla']:
                if col in df.columns:
                    temp = pd.to_datetime(df[col], errors='coerce')
                    df[col] = [d.date() if pd.notnull(d) else None for d in temp]
            st.session_state["df_master"] = df
        else:
            st.error(f"⚠️ No se encontró el archivo: {MASTER_FILE}. Asegúrate de que el nombre sea exacto.")

init_data()

def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

# 左侧导航
st.sidebar.title("Panel Maestro")
view = st.sidebar.radio("Menú", ["Países (Base)", "Productos (Detalle)", "Prioridad (Cálculo)", "Resumen"])

# 获取当前内存中的主表
df_master = st.session_state["df_master"]

# ==================== 视图 1: PAÍSES ====================
if view == "Países (Base)":
    st.title("Gestión de Países")
    st.info("💡 Los cambios aquí actualizarán todas las filas de productos asociadas a ese país.")
    
    # 提取国家维度的列并去重
    country_cols = ['País', 'ISO3', 'Estado_País', 'Implementación', 'Nota_País']
    df_countries = df_master[country_cols].drop_duplicates(subset=['País']).copy()
    
    edited_countries = st.data_editor(
        df_countries,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Estado_País": st.column_config.SelectboxColumn(
                "Estado",
                options=["Activo", "Inactivo", "No implementado"],
                required=True
            )
        }
    )
    
    if not edited_countries.equals(df_countries):
        # 将修改应用回主表：通过 País 匹配更新所有相关行
        for index, row in edited_countries.iterrows():
            pais_name = row['País']
            # 更新主表中所有属于该国家的信息
            df_master.loc[df_master['País'] == pais_name, country_cols] = row.values
        
        save_master(df_master)
        st.success("¡Países actualizados en el Maestro!")
        st.rerun()

# ==================== 视图 2: PRODUCTOS ====================
elif view == "Productos (Detalle)":
    st.title("Detalle de Productos")
    
    # 直接编辑大表的所有行
    edited_master = st.data_editor(
        df_master,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Estado_Producto": st.column_config.SelectboxColumn(
                "Estado Producto",
                options=["Activo", "Inactivo"],
                required=True
            ),
            "Actualización Completo": st.column_config.DateColumn("Actualización Completo", format="DD/MM/YYYY"),
            "Actualización regla": st.column_config.DateColumn("Actualización regla", format="DD/MM/YYYY"),
            "Estado_País": st.column_config.SelectboxColumn("Estado País", options=["Activo", "Inactivo", "No implementado"])
        }
    )
    
    if not edited_master.equals(df_master):
        save_master(edited_master)
        st.success("¡Base Maestra guardada!")
        st.rerun()

# ==================== 视图 3: PRIORIDAD ====================
elif view == "Prioridad (Cálculo)":
    st.title("Cálculo de Prioridades")
    
    # 权重调节
    w_col1, w_col2, w_col3, w_col4 = st.columns(4)
    w_c1 = w_col1.number_input("Clientes (W1)", value=0.45)
    w_c2 = w_col2.number_input("Productos (W2)", value=0.15)
    w_c3 = w_col3.number_input("Complejidad (W3)", value=0.25)
    w_c4 = w_col4.number_input("Recencia (W4)", value=0.15)
    
    # 提取优先级相关的国家行
    prio_cols = ['País', 'ISO3', 'Estado_País', 'clientes365', 'complejidadScore', 'daysSince']
    df_prio = df_master[prio_cols].drop_duplicates(subset=['País']).copy()
    
    # 计算分数逻辑
    def calc_prio(df):
        temp = df.copy()
        for c in ['clientes365', 'complejidadScore', 'daysSince']:
            temp[c] = pd.to_numeric(temp[c], errors='coerce').fillna(0)
        
        # 简单计算
        s = (temp['clientes365']*w_c1 + temp['complejidadScore']*w_c3 - temp['daysSince']/180*w_c4)*100
        temp['score100'] = s.round()
        
        def get_nivel(val):
            if val >= 80: return "P0"
            if val >= 60: return "P1"
            if val >= 40: return "P2"
            return "P3"
        
        temp['nivel'] = temp['score100'].apply(get_nivel)
        return temp

    df_prio_calc = calc_prio(df_prio)
    
    st.data_editor(
        df_prio_calc.sort_values("score100", ascending=False),
        use_container_width=True,
        hide_index=True,
        disabled=["score100", "nivel", "País", "ISO3"]
    )
    
    st.caption("Nota: Los cambios de métricas se guardan en el Maestro.")

# ==================== 视图 4: RESUMEN ====================
elif view == "Resumen":
    st.title("Estadísticas Globales")
    
    # 基础统计
    total_p = df_master['País'].nunique()
    activos = df_master[df_master['Estado_País'] == 'Activo']['País'].nunique()
    prod_total = len(df_master[df_master['Producto'].notna()])
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Países Únicos", total_p)
    m2.metric("Países Activos", activos)
    m3.metric("Total Productos", prod_total)
    
    st.divider()
    st.subheader("Distribución de Estados")
    st.bar_chart(df_master.drop_duplicates('País')['Estado_País'].value_counts())
