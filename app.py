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

# -------------------------------------------------------------------------
# 【全球国家多语言/ISO3智能映射字典】
# -------------------------------------------------------------------------
def get_country_aliases(country_name, iso3):
    """根据输入的国家名和ISO3，返回可能出现在Jira Resumen里的多语言别名列表"""
    name_clean = str(country_name).strip().lower()
    iso_clean = str(iso3).strip().lower()
    
    # 基础别名池，把当前名字和ISO加入
    aliases = {name_clean, iso_clean}
    
    # 全球国家英文/西班牙语/中文跨语言字典
    translation_book = {
        "afg": ["afghanistan", "afganistán", "阿富汗"],
        "ago": ["angola", "angola", "安哥拉"],
        "alb": ["albania", "albania", "阿尔巴尼亚"],
        "are": ["united arab emirates", "emiratos árabes unidos", "阿拉伯联合酋长国", "uae", "阿联酋"],
        "arg": ["argentina", "argentina", "阿根廷"],
        "arm": ["armenia", "armenia", "亚美尼亚"],
        "aus": ["australia", "australia", "澳大利亚"],
        "aut": ["austria", "austria", "奥地利"],
        "aze": ["azerbaijan", "azerbaiyán", "阿塞拜疆"],
        "bdi": ["burundi", "burundi", "布隆迪"],
        "bel": ["belgium", "bélgica", "比利时"],
        "ben": ["benin", "benín", "贝宁"],
        "bfa": ["burkina faso", "burkina faso", "布基纳法索"],
        "bgd": ["bangladesh", "bangladesh", "孟加拉国"],
        "bgr": ["bulgaria", "bulgaria", "保加利亚"],
        "bhr": ["bahrain", "bahréin", "巴林"],
        "bhs": ["bahamas", "bahamas", "巴哈马"],
        "bih": ["bosnia and herzegovina", "bosnia y herzegovina", "波斯尼亚和黑塞哥维那", "波黑"],
        "blr": ["belarus", "bielorrusia", "白俄罗斯"],
        "blz": ["belize", "belice", "伯利兹"],
        "bol": ["bolivia", "bolivia", "玻利维亚"],
        "bra": ["brazil", "brasil", "巴西"],
        "brb": ["barbados", "barbados", "巴巴多斯"],
        "brn": ["brunei", "brunéi", "文莱"],
        "btn": ["bhutan", "bután", "不丹"],
        "bwa": ["botswana", "botsuana", "博茨瓦纳"],
        "caf": ["central african republic", "república centroafricana", "中非共和国", "中非"],
        "can": ["canada", "canadá", "加拿大"],
        "che": ["switzerland", "suiza", "瑞士"],
        "chl": ["chile", "chile", "智利"],
        "chn": ["china", "china", "中国"],
        "civ": ["cote d'ivoire", "ivory coast", "costa de marfil", "科特迪瓦"],
        "cmr": ["cameroon", "camerún", "喀麦隆"],
        "cod": ["democratic republic of the congo", "república democrática del congo", "刚果（金）", "drc"],
        "cog": ["congo", "congo", "刚果（布）"],
        "col": ["colombia", "colombia", "哥伦比亚"],
        "com": ["comoros", "comoras", "科摩罗"],
        "cpv": ["cape verde", "cabo verde", "佛得角"],
        "cri": ["costa rica", "costa rica", "哥斯达黎加"],
        "cub": ["cuba", "cuba", "古巴"],
        "cyp": ["cyprus", "chipre", "塞浦路斯"],
        "cze": ["czech republic", "czechia", "república checa", "捷克"],
        "deu": ["germany", "alemania", "德国"],
        "dji": ["djibouti", "yibuti", "吉布提"],
        "dma": ["dominica", "dominica", "多米尼克"],
        "dnk": ["denmark", "dinamarca", "丹麦"],
        "dom": ["dominican republic", "república dominicana", "多米尼加共和国", "多米尼加"],
        "dza": ["algeria", "argelia", "阿尔及利亚"],
        "ecu": ["ecuador", "ecuador", "厄瓜多尔"],
        "egy": ["egypt", "egipto", "埃及"],
        "eri": ["eritrea", "eritrea", "厄立特里亚"],
        "esp": ["spain", "españa", "西班牙"],
        "est": ["estonia", "estonia", "爱沙尼亚"],
        "eth": ["ethiopia", "etiopía", "埃塞俄比亚"],
        "fin": ["finland", "finlandia", "芬兰"],
        "fji": ["fiji", "fiyi", "斐济"],
        "fra": ["france", "francia", "法国"],
        "fsm": ["micronesia", "micronesia", "密克罗尼西亚"],
        "gab": ["gabon", "gabón", "加蓬"],
        "gbr": ["united kingdom", "reino unido", "英国", "uk", "england"],
        "geo": ["georgia", "georgia", "格鲁吉亚"],
        "gha": ["ghana", "ghana", "加纳"],
        "gin": ["guinea", "guinea", "几内亚"],
        "gmb": ["gambia", "gambia", "冈比亚"],
        "gnb": ["guinea-bissau", "guinea-bisáu", "几内亚比绍"],
        "gnq": ["equatorial guinea", "guinea ecuatorial", "赤道几内亚"],
        "grc": ["greece", "grecia", "希腊"],
        "grd": ["grenada", "granada", "格林纳达"],
        "gtm": ["guatemala", "guatemala", "危地马拉"],
        "guy": ["guyana", "guyana", "圭亚那"],
        "hnd": ["honduras", "honduras", "洪都拉斯"],
        "hrv": ["croatia", "croacia", "克罗地亚"],
        "hti": ["haiti", "haití", "海地"],
        "hun": ["hungary", "hungría", "匈牙利"],
        "idn": ["indonesia", "indonesia", "印度尼西亚", "印尼"],
        "ind": ["india", "india", "印度"],
        "irl": ["ireland", "irlanda", "爱尔兰"],
        "irn": ["iran", "irán", "伊朗"],
        "irq": ["iraq", "irak", "伊拉克"],
        "isl": ["iceland", "islandia", "冰岛"],
        "isr": ["israel", "israel", "以色列"],
        "ita": ["italy", "italia", "意大利"],
        "jam": ["jamaica", "jamaica", "牙买加"],
        "jor": ["jordan", "jordania", "约旦"],
        "jpn": ["japan", "japón", "日本"],
        "kaz": ["kazakhstan", "kazajistán", "哈萨克斯坦"],
        "ken": ["kenya", "kenia", "肯尼亚"],
        "kgz": ["kyrgyzstan", "kirguistán", "吉尔吉斯斯坦"],
        "khm": ["cambodia", "camboya", "柬埔寨"],
        "kir": ["kiribati", "kiribati", "基里巴斯"],
        "kna": ["saint kitts and nevis", "san cristóbal y nieves", "圣基茨和尼维斯"],
        "kor": ["south korea", "corea del sur", "韩国", "korea", "korea, south"],
        "kwt": ["kuwait", "kuwait", "科威特"],
        "lao": ["laos", "laos", "老挝"],
        "lbn": ["lebanon", "líbano", "黎巴嫩"],
        "lbr": ["liberia", "liberia", "利比里亚"],
        "lby": ["libya", "libia", "利比亚"],
        "lca": ["saint lucia", "santa lucía", "圣卢西亚"],
        "lie": ["liechtenstein", "liechtenstein", "列支敦士登"],
        "lka": ["sri lanka", "sri lanka", "斯里兰卡"],
        "lso": ["lesotho", "lesoto", "莱索托"],
        "ltu": ["lithuania", "lituania", "立陶宛"],
        "lux": ["luxembourg", "luxemburgo", "卢森堡"],
        "lva": ["latvia", "letonia", "拉脱维亚"],
        "mar": ["morocco", "marruecos", "摩洛哥"],
        "mco": ["monaco", "mónaco", "摩纳哥"],
        "mda": ["moldova", "moldavia", "摩尔多瓦"],
        "mdg": ["madagascar", "madagascar", "马达加斯加"],
        "mdv": ["maldives", "maldivas", "马尔代夫"],
        "mex": ["mexico", "méxico", "墨西哥"],
        "mhl": ["marshall islands", "islas marshall", "马绍尔群岛"],
        "mkd": ["north macedonia", "macedonia del norte", "北马其顿"],
        "mli": ["mali", "malí", "马里"],
        "mlt": ["malta", "malta", "马耳他"],
        "mmr": ["myanmar", "birmania", "缅甸"],
        "mne": ["montenegro", "montenegro", "黑山"],
        "mng": ["mongolia", "mongolia", "蒙古"],
        "moz": ["mozambique", "mozambique", "莫桑比克"],
        "mrt": ["mauritania", "mauritania", "毛里塔尼亚"],
        "mus": ["mauritius", "mauricio", "毛里求斯"],
        "mwi": ["malawi", "malaui", "马拉维"],
        "mys": ["malaysia", "malasia", "马来西亚"],
        "nam": ["namibia", "namibia", "纳米比亚"],
        "ner": ["niger", "níger", "尼日尔"],
        "nga": ["nigeria", "nigeria", "尼日利亚"],
        "nic": ["nicaragua", "nicaragua", "尼加拉瓜"],
        "nld": ["netherlands", "países bajos", "荷兰", "holanda"],
        "nor": ["norway", "noruega", "挪威"],
        "npl": ["nepal", "nepal", "尼泊尔"],
        "nru": ["nauru", "nauru", "瑙鲁"],
        "nzl": ["new zealand", "nueva zelanda", "新西兰"],
        "omn": ["oman", "omán", "阿曼"],
        "pak": ["pakistan", "pakistán", "巴基斯坦"],
        "pan": ["panama", "panamá", "巴拿马"],
        "per": ["peru", "perú", "秘鲁"],
        "phl": ["philippines", "filipinas", "菲律宾"],
        "plw": ["palau", "palaos", "帕劳"],
        "png": ["papua new guinea", "papúa nueva guinea", "巴布亚新几内亚"],
        "pol": ["poland", "polonia", "波兰"],
        "prk": ["north korea", "corea del norte", "朝鲜", "dprk"],
        "prt": ["portugal", "portugal", "葡萄牙"],
        "pry": ["paraguay", "paraguay", "巴拉圭"],
        "qat": ["qatar", "catar", "卡塔尔"],
        "rou": ["romania", "rumania", "罗马尼亚"],
        "rus": ["russia", "rusia", "俄罗斯"],
        "rwa": ["rwanda", "ruanda", "卢旺达"],
        "sau": ["saudi arabia", "arabia saudita", "沙特阿拉伯", "沙特"],
        "sdn": ["sudan", "sudán", "苏丹"],
        "sen": ["senegal", "senegal", "塞内加尔"],
        "sgp": ["singapore", "singapur", "新加坡"],
        "slb": ["solomon islands", "islas salomón", "所罗门群岛"],
        "sle": ["sierra leone", "sierra leona", "塞拉利昂"],
        "slv": ["el salvador", "el salvador", "萨尔瓦多"],
        "smr": ["san marino", "san marino", "圣马力诺"],
        "som": ["somalia", "somalia", "索马里"],
        "srb": ["serbia", "serbia", "塞尔维亚"],
        "ssd": ["south sudan", "sudán del sur", "南苏丹"],
        "stp": ["sao tome and principe", "santo tomé y príncipe", "圣多美和普林西比"],
        "sur": ["suriname", "surinam", "苏里南"],
        "svk": ["slovakia", "eslovaquia", "斯洛伐克"],
        "svn": ["slovenia", "eslovenia", "斯洛文尼亚"],
        "swe": ["sweden", "suecia", "瑞典"],
        "swz": ["eswatini", "esuatini", "swaziland", "斯威士兰"],
        "syc": ["seychelles", "seychelles", "塞舌尔"],
        "syr": ["syria", "siria", "叙利亚"],
        "tcd": ["chad", "chad", "乍得"],
        "tgo": ["togo", "togo", "多哥"],
        "tha": ["thailand", "tailandia", "泰国"],
        "tjk": ["tajikistan", "tayikistán", "塔吉克斯坦"],
        "tkm": ["turkmenistan", "turkmenistán", "土库曼斯坦"],
        "tls": ["timor-leste", "timor oriental", "东帝汶"],
        "ton": ["tonga", "tonga", "汤加"],
        "tto": ["trinidad and tobago", "trinidad y tobago", "特立尼达和多巴哥"],
        "tun": ["tunisia", "túnez", "突尼斯"],
        "tur": ["turkey", "turquía", "土耳其"],
        "tuv": ["tuvalu", "tuvalu", "图瓦卢"],
        "twn": ["taiwan", "taiwán", "台湾"],
        "tza": ["tanzania", "tanzania", "坦桑尼亚"],
        "uga": ["uganda", "uganda", "乌干达"],
        "ukr": ["ukraine", "ucrania", "乌克兰"],
        "ury": ["uruguay", "uruguay", "乌拉圭"],
        "usa": ["united states", "estados unidos", "美国", "usa"],
        "uzb": ["uzbekistan", "uzbekistán", "乌兹别克斯坦"],
        "vat": ["vatican city", "ciudad del vaticano", "梵蒂冈"],
        "vct": ["saint vincent and the grenadines", "san vicente y las granadinas", "圣文森特和格林纳丁斯"],
        "ven": ["venezuela", "venezuela", "委内瑞拉"],
        "vnm": ["vietnam", "vietnam", "越南"],
        "vut": ["vanuatu", "vanuatu", "瓦努阿图"],
        "wsm": ["samoa", "samoa", "萨摩亚"],
        "yem": ["yemen", "yemen", "也门"],
        "zaf": ["south africa", "sudáfrica", "南非"],
        "zmb": ["zambia", "zambia", "赞比亚"],
        "zwe": ["zimbabwe", "zimbabue", "津巴布韦"]
    }
    
    if iso_clean in translation_book:
        aliases.update(translation_book[iso_clean])
        
    # 返回有效的名称列表
    return [a for a in aliases if a and a != 'nan']

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
    # 【上传 Jira 文件自动更新模块】带全球国家多语言识别与动态列兼容
    # -------------------------------------------------------------------------
    st.markdown("### 📥 Sincronización Automática con Jira")
    uploaded_file = st.file_uploader("请上传由 Jira 导出的 CSV（分号分隔）或 Excel 文件：", type=["csv", "xlsx"])
    
    if 'modified_rows' not in st.session_state:
        st.session_state.modified_rows = []

    if uploaded_file is not None:
        try:
            # 自动识别格式并读取
            if uploaded_file.name.endswith('.csv'):
                # 处理你提供的用分号(;)分割的 Jira CSV 文件
                jira_df = pd.read_csv(uploaded_file, sep=';', engine='python')
            else:
                jira_df = pd.read_excel(uploaded_file)
            
            # 清洗列标题的空格
            jira_df.columns = jira_df.columns.str.strip()
            
            # 兼容读取 Clave de incidencia 和 用于判定更新类型的 ID 列
            actual_cols = jira_df.columns.tolist()
            clave_col = 'Clave de incidencia' if 'Clave de incidencia' in actual_cols else ('Clave de incidence' if 'Clave de incidence' in actual_cols else None)
            
            # 💡核心修改：兼容 'ID de la incidencia' 和 'Producto'，只要存在任何一个即可作为判定列
            id_col = 'ID de la incidencia' if 'ID de la incidencia' in actual_cols else ('Producto' if 'Producto' in actual_cols else None)
            
            if clave_col and 'Actualizada' in actual_cols and 'Resumen' in actual_cols and id_col:
                
                if st.button("⚡ 预解析并执行多语言 Jira 规则匹配"):
                    st.session_state.modified_rows = [] # 重置上一次的修改高亮标记
                    
                    # 遍历我们主表格数据库（Priority (1).xlsx）里的每一行
                    for index, row in st.session_state.df.iterrows():
                        p_name = str(row['Producto']).strip()
                        c_name = str(row['País']).strip()
                        iso3_val = str(row['ISO3']).strip() if 'ISO3' in row else ""
                        
                        if pd.isna(row['Producto']) or p_name == 'nan':
                            continue
                        
                        # -----------------------------------------------------
                        # 核心多语言匹配调用
                        # -----------------------------------------------------
                        country_aliases = get_country_aliases(c_name, iso3_val)
                        
                        matched_jira = pd.DataFrame()
                        for alias in country_aliases:
                            # 使用正则避免匹配错乱 (例如印尼 Indonesia 不会被 India 错误捕获)
                            temp_match = jira_df[
                                jira_df['Resumen'].astype(str).str.contains(r'\b' + alias + r'\b|' + alias, case=False, na=False)
                            ]
                            if not temp_match.empty:
                                matched_jira = temp_match
                                break
                        
                        if not matched_jira.empty:
                            # 拿到最上面最新的一条 Jira 任务
                            jira_row = matched_jira.iloc[0]
                            
                            # 提取并解析更新日期
                            raw_date = str(jira_row['Actualizada']).split()[0]
                            parsed_date = pd.to_datetime(raw_date, dayfirst=True, errors='coerce')
                            
                            # 自动生成固定的 Atlassian 任务超链接
                            clave = str(jira_row[clave_col]).strip()
                            new_link = f"https://visagov.atlassian.net/browse/{clave}"
                            
                            # 获取判定列（ID 或 Producto）的值用于规则判定
                            jira_id_val = jira_row[id_col]
                            is_empty_id = pd.isna(jira_id_val) or str(jira_id_val).strip() == "" or str(jira_id_val).lower() == "nan"
                            
                            # 【严格执行判定规则】：
                            if is_empty_id:
                                # 1. 内容为空，对应更新：Última actualización completa
                                st.session_state.df.at[index, 'Última actualización completa'] = parsed_date
                            else:
                                # 2. 内容不为空，对应更新：Última actualización parcial
                                st.session_state.df.at[index, 'Última actualización parcial'] = parsed_date
                            
                            # 统一更新链接列
                            st.session_state.df.at[index, 'Nota_Producto'] = new_link
                            
                            # 将被修改的这行存入高亮置顶缓存
                            st.session_state.modified_rows.append((c_name, p_name))
                            
                    st.success(f"🎉 成功完成多语言智能匹配！共发现 {len(st.session_state.modified_rows)} 项数据变更，已在下方用蓝色高亮并为您置顶。请核对后点击下方 'Guardar Cambios' 保存。")
            else:
                # 友好的报错提示，指出缺失的具体列
                st.error(f"❌ 上传的文件缺少必要列。系统目前检测到的表头为：{actual_cols}。请确保存在 'Actualizada', 'Resumen'，以及 'ID de la incidencia' 或 'Producto'。")
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
    # 【置顶逻辑控制】
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
    # 【蓝色标记高亮样式映射】
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

    df_calc = st.session_state.df[st.session_state.df['Producto'].notna() & (st.session_state.df['Producto'] != 'nan')].copy()

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
    COL_A = 'País'                             
    COL_I = 'O (Pedidos)'                  
    COL_J = 'K (Conversión %)'                         
    COL_K = 'E (Extra Keys)'                   
    COL_L = 'F (Documentos)'                   
    COL_M = 'L (Lógica Dinámica)'              
    COL_N = 'S (Tipo de County details)'       
    COL_O = 'M (Impacto Precio)'               
    
    COL_Q = 'Última actualización parcial'      
    COL_R = 'Última actualización completa'     
    
    COL_S_name = 'Factor de Tiempo'            
    COL_T_name = 'Score Total País'            
    COL_U_name = 'Cantidad Prod'               
    # =========================================================================

    input_fields = [COL_I, COL_J, COL_K, COL_L, COL_M, COL_N, COL_O]
    for col in input_fields:
        if col in df_calc.columns:
            df_calc[col] = pd.to_numeric(df_calc[col], errors='coerce').fillna(0)

    try:
        cond_I_actual = [df_calc[COL_I] == 0, df_calc[COL_I] <= 100, df_calc[COL_I] <= 1000, df_calc[COL_I] <= 10000]
        score_I = np.select(cond_I_actual, [0, 1, 3, 6], default=10)
        
        score_K = np.select([df_calc[COL_K] <= 20, df_calc[COL_K] <= 40], [1, 3], default=5)
        score_L = np.select([df_calc[COL_L] <= 4, df_calc[COL_L] <= 6], [2, 4], default=6)
        
        NEW_COL_P = (score_I * (1 + df_calc[COL_J])) * ((1 + score_K + score_L + df_calc[COL_M] * 5) * (df_calc[COL_N] * df_calc[COL_O]))
        df_calc['CALC_P_POINT'] = NEW_COL_P

        today_date = pd.to_datetime(datetime.now().date())
        
        days_R = (today_date - pd.to_datetime(df_calc[COL_R], errors='coerce')).dt.days.fillna(730)
        days_Q = (today_date - pd.to_datetime(df_calc[COL_Q], errors='coerce')).dt.days.fillna(730)
        
        condition_or = (df_calc[COL_Q].isna()) | (df_calc[COL_R] > df_calc[COL_Q])
        formula_2_sub = np.where(condition_or, days_R, days_Q)
        
        NEW_COL_S = (days_R * 1) + (formula_2_sub * 0.3)
        df_calc['CALC_S_FACTOR'] = NEW_COL_S

        NEW_COL_U = df_calc.groupby(COL_A)[COL_A].transform('count')
        df_calc['CALC_U_CANTIDAD'] = NEW_COL_U

        NEW_COL_T = df_calc.groupby(COL_A)['CALC_P_POINT'].transform('sum')
        df_calc['CALC_T_SCORE'] = NEW_COL_T

        FINAL_COL_V = df_calc['CALC_T_SCORE'] * (1 + np.log10(df_calc['CALC_U_CANTIDAD'].clip(lower=1))) * (1 + (df_calc['CALC_S_FACTOR'] / 90))
        df_calc['Final_Priority_Score'] = FINAL_COL_V

        df_priority_view = df_calc[['País', 'Producto', 'Final_Priority_Score']].sort_values(by='Final_Priority_Score', ascending=False)

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
