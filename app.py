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
    
    aliases = {name_clean, iso_clean}
    
    translation_book = {
        "afg": ["afghanistan", "afganistán", "阿富汗", "afghanistan", "afghanistan", "アフガニスタン", "афганистан"],
        "ago": ["angola", "angola", "安哥拉", "angola", "angola", "アンゴラ", "ангола"],
        "alb": ["albania", "albania", "阿尔巴尼亚", "albanie", "albanien", "アルバニア", "албания"],
        "are": ["united arab emirates", "emiratos árabes unidos", "阿拉伯联合酋长国", "uae", "阿联酋", "émirats arabes unis", "vereinigte arabische emirate", "アラブ首長国連邦", "объединенные арабские эмираты", "оаэ"],
        "arg": ["argentina", "argentina", "阿根廷", "argentine", "argentinien", "アルゼンチン", "аргентина"],
        "arm": ["armenia", "armenia", "亚美尼亚", "arménie", "armenien", "アルメニア", "армения"],
        "aus": ["australia", "australia", "澳大利亚", "australie", "australien", "オーストラリア", "австралия"],
        "aut": ["austria", "austria", "奥地利", "autriche", "österreich", "オーストリア", "австрия"],
        "aze": ["azerbaijan", "azerbaiyán", "阿塞拜疆", "azerbaïdjan", "aserbaidschan", "アゼルバイジャン", "азербайджан"],
        "bdi": ["burundi", "burundi", "布隆迪", "burundi", "burundi", "ブルンジ", "бурунди"],
        "bel": ["belgium", "bélgica", "比利时", "belgique", "belgien", "ベルギー", "бельгия"],
        "ben": ["benin", "benín", "贝宁", "bénin", "benin", "ベナン", "бенин"],
        "bfa": ["burkina faso", "burkina faso", "布基纳法索", "burkina faso", "burkina faso", "ブルキナファソ", "буркина-фасо"],
        "bgd": ["bangladesh", "bangladesh", "孟加拉国", "bangladesh", "bangladesch", "バングラデシュ", "бангладеш"],
        "bgr": ["bulgaria", "bulgaria", "保加利亚", "bulgarie", "bulgarien", "ブルガリア", "болгария"],
        "bhr": ["bahrain", "bahréin", "巴林", "bahreïn", "bahrain", "バーレーン", "бахрейн"],
        "bhs": ["bahamas", "bahamas", "巴哈马", "bahamas", "bahamas", "バハマ", "багамы"],
        "bih": ["bosnia and herzegovina", "bosnia y herzegovina", "波斯尼亚和黑塞哥维那", "波黑", "bosnie-herzégovine", "bosnien und herzegowina", "ボスニア・ヘルツェゴビナ", "босния и герцеговина"],
        "blr": ["belarus", "bielorrusia", "白俄罗斯", "biélorussie", "belarus", "weißrussland", "ベラルーシ", "беларусь"],
        "blz": ["belize", "belice", "伯利兹", "belize", "belize", "ベリーズ", "белиз"],
        "bol": ["bolivia", "bolivia", "玻利维亚", "bolivie", "bolivien", "ボリビア", "боливия"],
        "bra": ["brazil", "brasil", "巴西", "brésil", "brasilien", "ブラジル", "бразилия"],
        "brb": ["barbados", "barbados", "巴巴多斯", "barbade", "barbados", "バルバドス", "барбадос"],
        "brn": ["brunei", "brunéi", "文莱", "brunei", "brunei", "ブルネイ", "бруней"],
        "btn": ["bhutan", "bután", "不丹", "bhoutan", "bhutan", "ブータン", "бутан"],
        "bwa": ["botswana", "botsuana", "博茨瓦纳", "botswana", "botsuana", "ボツワナ", "ботсвана"],
        "caf": ["central african republic", "república centroafricana", "中非共和国", "中非", "république centrafricaine", "zentralafrikanische republik", "中央アフリカ共和国", "центральноафриканская республика", "цар"],
        "can": ["canada", "canadá", "加拿大", "canada", "kanada", "カナダ", "канада"],
        "che": ["switzerland", "suiza", "瑞士", "suisse", "schweiz", "スイス", "швейцария"],
        "chl": ["chile", "chile", "智利", "chili", "chile", "チリ", "чили"],
        "chn": ["china", "china", "中国", "chine", "china", "中国", "китай"],
        "civ": ["cote d'ivoire", "ivory coast", "costa de marfil", "科特迪瓦", "côte d'ivoire", "elfenbeinküste", "コートジボワール", "кот-д'ивуар"],
        "cmr": ["cameroon", "camerún", "喀麦隆", "cameroun", "kamerun", "カメルーン", "камерун"],
        "cod": ["democratic republic of the congo", "república democrática del congo", "刚果（金）", "drc", "république démocratique du congo", "demokratische republik kongo", "コンゴ民主共和国", "демократическая республика конго"],
        "cog": ["congo", "congo", "刚果（布）", "congo", "kongo", "コンゴ共和国", "конго"],
        "col": ["colombia", "colombia", "哥伦比亚", "colombie", "kolumbien", "コロンビア", "колумбия"],
        "com": ["comoros", "comoras", "科摩罗", "comores", "komoren", "コモロ", "коморы"],
        "cpv": ["cape verde", "cabo verde", "佛得角", "cap-vert", "kap verde", "カーボベルデ", "кабо-верде"],
        "cri": ["costa rica", "costa rica", "哥斯达黎加", "costa rica", "costa rica", "コスタリカ", "коста-рика"],
        "cub": ["cuba", "cuba", "古巴", "cuba", "kuba", "キューバ", "куба"],
        "cyp": ["cyprus", "chipre", "塞浦路斯", "chypre", "zypern", "キプロス", "кипр"],
        "cze": ["czech republic", "czechia", "república checa", "捷克", "république tchèque", "tchéquie", "tschechien", "チェコ", "чехия"],
        "deu": ["germany", "alemania", "德国", "allemagne", "deutschland", "ドイツ", "германия"],
        "dji": ["djibouti", "yibuti", "吉布提", "djibouti", "dschibuti", "ジブチ", "джибути"],
        "dma": ["dominica", "dominica", "多米尼克", "dominique", "dominica", "ドミニカ国", "доминика"],
        "dnk": ["denmark", "dinamarca", "丹麦", "danemark", "dänemark", "デンマーク", "дания"],
        "dom": ["dominican republic", "república dominicana", "多米尼加共和国", "多米尼加", "république dominicaine", "dominikanische republik", "ドミニカ共和国", "доминиканская республика"],
        "dza": ["algeria", "argelia", "阿尔及利亚", "algérie", "algerien", "アルジェリア", "алжир"],
        "ecu": ["ecuador", "ecuador", "厄瓜多尔", "équateur", "ecuador", "エクアドル", "эквадор"],
        "egy": ["egypt", "egipto", "埃及", "égypte", "ägypten", "エジプト", "египет"],
        "eri": ["eritrea", "eritrea", "厄立特里亚", "érythrée", "eritrea", "エリトリア", "эритрея"],
        "esp": ["spain", "españa", "西班牙", "espagne", "spanien", "スペイン", "испания"],
        "est": ["estonia", "estonia", "爱沙尼亚", "estonie", "estland", "エストニア", "эстония"],
        "eth": ["ethiopia", "etiopía", "埃塞俄比亚", "éthiopie", "äthiopien", "エチオピア", "эфиопия"],
        "fin": ["finland", "finlandia", "芬兰", "finlande", "finnland", "フィンランド", "финляндия"],
        "fji": ["fiji", "fiyi", "斐济", "fidji", "fidschi", "フィジー", "фиджи"],
        "fra": ["france", "francia", "法国", "france", "frankreich", "フランス", "франция"],
        "fsm": ["micronesia", "micronesia", "密克罗尼西亚", "micronésie", "mikronesien", "ミクロネシア", "микронезия"],
        "gab": ["gabon", "gabón", "加蓬", "gabon", "gabun", "ガボン", "габон"],
        "gbr": ["united kingdom", "reino unido", "英国", "uk", "england", "royaume-uni", "vereinigtes königreich", "großbritannien", "イギリス", "великобритания"],
        "geo": ["georgia", "georgia", "格鲁吉亚", "géorgie", "georgien", "ジョージア", "грузия"],
        "gha": ["ghana", "ghana", "加纳", "ghana", "ghana", "ガーナ", "гана"],
        "gin": ["guinea", "guinea", "几内亚", "guinée", "guinea", "ギニア", "гвинея"],
        "gmb": ["gambia", "gambia", "冈比亚", "gambie", "gambia", "ガンビア", "гамбия"],
        "gnb": ["guinea-bissau", "guinea-bisáu", "几内亚比绍", "guinée-bissau", "guinea-bissau", "ギニアビサウ", "гвинея-бисау"],
        "gnq": ["equatorial guinea", "guinea ecuatorial", "赤道几内亚", "guinée équatoriale", "äquatorialguinea", "赤道ギニア", "экваториальная гвинея"],
        "grc": ["greece", "grecia", "希腊", "grèce", "griechenland", "ギリシャ", "греция"],
        "grd": ["grenada", "granada", "格林纳达", "grenade", "grenada", "グレナダ", "гренада"],
        "gtm": ["guatemala", "guatemala", "危地马拉", "guatemala", "guatemala", "グアテマラ", "гватемала"],
        "guy": ["guyana", "guyana", "圭亚那", "guyana", "guyana", "ガイアナ", "гайана"],
        "hnd": ["honduras", "honduras", "洪都拉斯", "honduras", "honduras", "ホンジュラス", "гондурас"],
        "hrv": ["croatia", "croacia", "克罗地亚", "croatie", "kroatien", "クロアチア", "хорватия"],
        "hti": ["haiti", "haití", "海地", "haïti", "haiti", "ハイチ", "гаити"],
        "hun": ["hungary", "hungría", "匈牙利", "hongrie", "ungarn", "ハンガリー", "венгрия"],
        "idn": ["indonesia", "indonesia", "印度尼西亚", "印尼", "indonésie", "indonesien", "インドネシア", "индонезия"],
        "ind": ["india", "india", "印度", "inde", "indien", "インド", "индия"],
        "irl": ["ireland", "irlanda", "爱尔兰", "irlande", "irland", "アイルランド", "ирландия"],
        "irn": ["iran", "irán", "伊朗", "iran", "iran", "イラン", "иран"],
        "irq": ["iraq", "irak", "伊拉克", "irak", "irak", "イラク", "ирак"],
        "isl": ["iceland", "islandia", "冰岛", "islande", "island", "アイスランド", "исландия"],
        "isr": ["israel", "israel", "以色列", "israël", "israel", "イスラエル", "израиль"],
        "ita": ["italy", "italia", "意大利", "italie", "italien", "イタリア", "италия"],
        "jam": ["jamaica", "jamaica", "牙买加", "jamaïque", "jamaika", "ジャマイカ", "ямайка"],
        "jor": ["jordan", "jordania", "约旦", "jordanie", "jordanien", "ヨルダン", "иордания"],
        "jpn": ["japan", "japón", "日本", "japon", "japan", "япония"],
        "kaz": ["kazakhstan", "kazajistán", "哈萨克斯坦", "kazakhstan", "kasachstan", "カザフスタン", "казахстан"],
        "ken": ["kenya", "kenia", "肯尼亚", "kenya", "kenia", "ケニア", "кения"],
        "kgz": ["kyrgyzstan", "kirguistán", "吉尔吉斯斯坦", "kirghizistan", "kirgisistan", "キルギス", "киргизия"],
        "khm": ["cambodia", "camboya", "柬埔寨", "cambodge", "kambodscha", "カンボジア", "камбоджа"],
        "kir": ["kiribati", "kiribati", "基里巴斯", "kiribati", "kiribati", "キリバス", "кирибати"],
        "kna": ["saint kitts and nevis", "san cristóbal y nieves", "圣基茨和尼维斯", "saint-kitts-et-nevis", "st. kitts und nevis", "セントクリストファー・ネイビス", "сент-китс и невис"],
        "kor": ["south korea", "corea del sur", "韩国", "korea", "korea, south", "corée du sud", "südkorea", "韓国", "южная корея"],
        "kwt": ["kuwait", "kuwait", "科威特", "koweït", "kuwait", "クウェート", "кувейт"],
        "lao": ["laos", "laos", "老挝", "laos", "laos", "ラオス", "лаос"],
        "lbn": ["lebanon", "líbano", "黎巴嫩", "liban", "libanon", "レバノン", "ливан"],
        "lbr": ["liberia", "liberia", "利比里亚", "libéria", "liberia", "リベリア", "либерия"],
        "lby": ["libya", "libia", "利比亚", "libye", "libyen", "リビア", "ливия"],
        "lca": ["saint lucia", "santa lucía", "圣卢西亚", "sainte-lucie", "st. lucia", "セントルシア", "сент-люсия"],
        "lie": ["liechtenstein", "liechtenstein", "列支敦士登", "liechtenstein", "liechtenstein", "リヒテンシュタイン", "лихтенштейн"],
        "lka": ["sri lanka", "sri lanka", "斯里兰卡", "sri lanka", "sri lanka", "スリランカ", "шри-ланка"],
        "lso": ["lesotho", "lesoto", "莱索托", "lesotho", "lesotho", "レソト", "лесото"],
        "ltu": ["lithuania", "lituania", "立陶宛", "lituanie", "litauen", "リトアニア", "литва"],
        "lux": ["luxembourg", "luxemburgo", "卢森堡", "luxembourg", "luxemburg", "ルクセンブルク", "люксембург"],
        "lva": ["latvia", "letonia", "拉脱维亚", "lettonie", "lettland", "ラトビア", "латвия"],
        "mar": ["morocco", "marruecos", "摩洛哥", "maroc", "marokko", "モロッコ", "марокко"],
        "mco": ["monaco", "mónaco", "摩纳哥", "monaco", "monaco", "モナコ", "монако"],
        "mda": ["moldova", "moldavia", "摩尔多瓦", "moldavie", "moldau", "モルドバ", "молдова"],
        "mdg": ["madagascar", "madagascar", "马达加斯加", "madagascar", "madagaskar", "マダガスカル", "мадагаскар"],
        "mdv": ["maldives", "maldivas", "马尔代夫", "maldives", "malediven", "モルディブ", "мальдивы"],
        "mex": ["mexico", "méxico", "墨西哥", "mexique", "mexiko", "メキシコ", "мексика"],
        "mhl": ["marshall islands", "islas marshall", "马绍尔群岛", "îles marshall", "marshallinseln", "マーシャル諸島", "маршалловы острова"],
        "mkd": ["north macedonia", "macedonia del norte", "北马其顿", "macédoine du nord", "nordmazedonien", "北マケドニア", "северная македония"],
        "mli": ["mali", "malí", "马里", "mali", "mali", "マリ", "мали"],
        "mlt": ["malta", "malta", "马耳他", "malte", "malta", "マルタ", "мальта"],
        "mmr": ["myanmar", "birmania", "缅甸", "myanmar", "birmanie", "myanmar", "ミャンマー", "мьянма"],
        "mne": ["montenegro", "montenegro", "黑山", "monténégro", "montenegro", "モンテネグロ", "черногория"],
        "mng": ["mongolia", "mongolia", "蒙古", "mongolie", "mongolei", "モンゴル", "монголия"],
        "moz": ["mozambique", "mozambique", "莫桑比克", "mozambique", "mosambik", "モザンビーク", "мозамбик"],
        "mrt": ["mauritania", "mauritania", "毛里塔尼亚", "mauritanie", "mauretanien", "モーリタニア", "мавритания"],
        "mus": ["mauritius", "mauricio", "毛里求斯", "maurice", "mauritius", "モーリシャス", "маврикий"],
        "mwi": ["malawi", "malaui", "马拉维", "malawi", "malawi", "マラウイ", "малави"],
        "mys": ["malaysia", "malasia", "马来西亚", "malaisie", "malaysia", "マレーシア", "малайзия"],
        "nam": ["namibia", "namibia", "纳米比亚", "namibie", "namibia", "ナミビア", "намибия"],
        "ner": ["niger", "níger", "尼日尔", "niger", "niger", "ニジェール", "нигер"],
        "nga": ["nigeria", "nigeria", "尼日利亚", "nigéria", "nigeria", "ナイジェリア", "нигерия"],
        "nic": ["nicaragua", "nicaragua", "尼加拉瓜", "nicaragua", "nicaragua", "ニカラグア", "никарагуа"],
        "nld": ["netherlands", "países bajos", "荷兰", "holanda", "pays-bas", "niederlande", "オランダ", "нидерланды"],
        "nor": ["norway", "noruega", "挪威", "norvège", "norwegen", "ノルウェー", "норвегия"],
        "npl": ["nepal", "nepal", "尼泊尔", "népal", "nepal", "ネパール", "непал"],
        "nru": ["nauru", "nauru", "瑙鲁", "nauru", "nauru", "ナウル", "науру"],
        "nzl": ["new zealand", "nueva zelanda", "新西兰", "nouvelle-zélande", "neuseeland", "ニュージーランド", "новая зеландия"],
        "omn": ["oman", "omán", "阿曼", "oman", "oman", "オマーン", "оман"],
        "pak": ["pakistan", "pakistán", "巴基斯坦", "pakistan", "pakistan", "パキスタン", "пакистан"],
        "pan": ["panama", "panamá", "巴拿马", "panama", "panama", "パナマ", "панама"],
        "per": ["peru", "perú", "秘鲁", "pérou", "peru", "ペルー", "перу"],
        "phl": ["philippines", "filipinas", "菲律宾", "philippines", "philippinen", "フィリピン", "филиппины"],
        "plw": ["palau", "palaos", "帕劳", "palaos", "palau", "パラオ", "палау"],
        "png": ["papua new guinea", "papúa nueva guinea", "巴布亚新几内亚", "papouasie-nouvelle-guinée", "papua-neuguinea", "パプアニューギニア", "папуа — новая гвинея"],
        "pol": ["poland", "polonia", "波兰", "pologne", "polen", "ポーランド", "польша"],
        "prk": ["north korea", "corea del norte", "朝鲜", "dprk", "corée du nord", "nordkorea", "北朝鮮", "северная корея"],
        "prt": ["portugal", "portugal", "葡萄牙", "portugal", "portugal", "ポルトガル", "португалия"],
        "pry": ["paraguay", "paraguay", "巴拉圭", "paraguay", "paraguay", "パラグアイ", "парагвай"],
        "qat": ["qatar", "catar", "卡塔尔", "qatar", "katar", "カタール", "катар"],
        "rou": ["romania", "rumania", "罗马尼亚", "roumanie", "rumänien", "ルーマニア", "румыния"],
        "rus": ["russia", "rusia", "俄罗斯", "russie", "russland", "ロシア", "россия"],
        "rwa": ["rwanda", "ruanda", "卢旺达", "rwanda", "ruanda", "ルワンダ", "руанда"],
        "sau": ["saudi arabia", "arabia saudita", "沙特阿拉伯", "沙特", "arabie saoudite", "saudi-arabien", "サウジアラビア", "саудовская аравия"],
        "sdn": ["sudan", "sudán", "苏丹", "soudan", "sudan", "スーダン", "судан"],
        "sen": ["senegal", "senegal", "塞内加尔", "sénégal", "senegal", "セネガル", "сенегал"],
        "sgp": ["singapore", "singapur", "新加坡", "singapour", "singapur", "シンガポール", "сингапур"],
        "slb": ["solomon islands", "islas salomón", "所罗门群岛", "îles salomon", "salomonen", "ソロモン諸島", "соломоновы острова"],
        "sle": ["sierra leone", "sierra leona", "塞拉利昂", "sierra leone", "sierra leone", "シエラレオネ", "сьерра-леоне"],
        "slv": ["el salvador", "el salvador", "萨尔瓦多", "el salvador", "el salvador", "エルサルバドル", "сальвадор"],
        "smr": ["san marino", "san marino", "圣马力诺", "saint-marin", "san marino", "サンマリノ", "сан-марино"],
        "som": ["somalia", "somalia", "索马里", "somalie", "somalia", "ソマリア", "сомали"],
        "srb": ["serbia", "serbia", "塞尔维亚", "serbie", "serbien", "セルビア", "сербия"],
        "ssd": ["south sudan", "sudán del sur", "南苏丹", "soudan du sud", "südsudan", "南スーダン", "южный судан"],
        "stp": ["sao tome and principe", "santo tomé y príncipe", "圣多美和普林西比", "sao tomé-et-principe", "são tomé und príncipe", "サントメ・プリンシペ", "сан-томе и принсипи"],
        "sur": ["suriname", "surinam", "苏里南", "suriname", "suriname", "スリナム", "суринам"],
        "svk": ["slovakia", "eslovaquia", "斯洛伐克", "slovaquie", "slowakei", "スロバキア", "словакия"],
        "svn": ["slovenia", "eslovenia", "斯洛文尼亚", "slovénie", "slowenien", "スロベニア", "словения"],
        "swe": ["sweden", "suecia", "瑞典", "suède", "schweden", "スウェーデン", "швеция"],
        "swz": ["eswatini", "esuatini", "swaziland", "斯威士兰", "eswatini", "swasiland", "エスワティニ", "эсватини"],
        "syc": ["seychelles", "seychelles", "塞舌尔", "seychelles", "seychellen", "セーシェル", "сейшельские острова"],
        "syr": ["syria", "siria", "叙利亚", "syrie", "syrien", "シリア", "сирия"],
        "tcd": ["chad", "chad", "乍得", "tchad", "tschad", "チャド", "чад"],
        "tgo": ["togo", "togo", "多哥", "togo", "togo", "トーゴ", "того"],
        "tha": ["thailand", "tailandia", "泰国", "thaïlande", "thailand", "タイ", "таиланд"],
        "tjk": ["tajikistan", "tayikistán", "塔吉克斯坦", "tadjikistan", "tadschikistan", "タジキスタン", "таджикистан"],
        "tkm": ["turkmenistan", "turkmenistán", "土库曼斯坦", "turkménistan", "turkmenistan", "トルクメニスタン", "туркменистан"],
        "tls": ["timor-leste", "timor oriental", "东帝汶", "timor oriental", "osttimor", "東ティモール", "восточный тимор"],
        "ton": ["tonga", "tonga", "汤加", "tonga", "tonga", "トンガ", "тонга"],
        "tto": ["trinidad and tobago", "trinidad y tobago", "特立尼达和多巴哥", "trinité-et-tobago", "trinidad und tobago", "トリニダード・トバゴ", "тринидад и тобаго"],
        "tun": ["tunisia", "túnez", "突尼斯", "tunisie", "tunesien", "チュニジア", "тунис"],
        "tur": ["turkey", "turquía", "土耳其", "turquie", "türkei", "トルコ", "турция"],
        "tuv": ["tuvalu", "tuvalu", "图瓦卢", "tuvalu", "tuvalu", "ツバル", "тувалу"],
        "twn": ["taiwan", "taiwán", "台湾", "taïwan", "taiwan", "台湾", "тайвань"],
        "tza": ["tanzania", "tanzania", "坦桑尼亚", "tanzanie", "tansania", "タンザニア", "танзания"],
        "uga": ["uganda", "uganda", "乌干达", "ouganda", "uganda", "ウガンダ", "уганда"],
        "ukr": ["ukraine", "ucrania", "乌克兰", "ukraine", "ukraine", "ウクライナ", "украина"],
        "ury": ["uruguay", "uruguay", "乌拉圭", "uruguay", "uruguay", "ウルグアイ", "уругвай"],
        "usa": ["united states", "estados unidos", "美国", "usa", "états-unis", "vereinigte staaten", "アメリカ", "сша"],
        "uzb": ["uzbekistan", "uzbekistán", "乌兹别克斯坦", "ouzbékistan", "usbekistan", "ウズベキスタン", "узбекистан"],
        "vat": ["vatican city", "ciudad del vaticano", "梵蒂冈", "vatican", "vatikanstadt", "バチカン", "ватикан"],
        "vct": ["saint vincent and the grenadines", "san vicente y las granadinas", "圣文森特和格林纳丁斯", "saint-vincent-et-les-grenadines", "st. vincent und die grenadinen", "セントビンセント・グレナディーン", "сент-винсент и гренадины"],
        "ven": ["venezuela", "venezuela", "委内瑞拉", "venezuela", "venezuela", "ベネズエラ", "венесуэла"],
        "vnm": ["vietnam", "vietnam", "越南", "vietnam", "vietnam", "ベトナム", "вьетнам"],
        "vut": ["vanuatu", "vanuatu", "瓦努阿图", "vanuatu", "vanuatu", "バヌアツ", "вануату"],
        "wsm": ["samoa", "samoa", "萨摩亚", "samoa", "samoa", "サモア", "самоа"],
        "yem": ["yemen", "yemen", "也门", "yémen", "jemen", "イエメン", "йемен"],
        "zaf": ["south africa", "sudáfrica", "南非", "afrique du sud", "südafrika", "南アフリカ", "южная африка"],
        "zmb": ["zambia", "zambia", "赞比亚", "zambie", "sambia", "ザンビア", "замбия"],
        "zwe": ["zimbabwe", "zimbabue", "津巴布韦", "zimbabwe", "simbabwe", "ジンバブエ", "зимбабве"]
    }
    
    if iso_clean in translation_book:
        aliases.update(translation_book[iso_clean])
        
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
    # 【上传 Jira 文件自动更新模块】带智能三级规则匹配
    # -------------------------------------------------------------------------
    st.markdown("### 📥 Sincronización Automática con Jira")
    uploaded_file = st.file_uploader("请上传由 Jira 导出的 CSV（分号分隔）或 Excel 文件：", type=["csv", "xlsx"])
    
    if 'modified_rows' not in st.session_state:
        st.session_state.modified_rows = []

    if uploaded_file is not None:
        try:
            # 自动识别格式并读取
            if uploaded_file.name.endswith('.csv'):
                jira_df = pd.read_csv(uploaded_file, sep=';', engine='python')
            else:
                jira_df = pd.read_excel(uploaded_file)
            
            # 清洗列标题的空格
            jira_df.columns = jira_df.columns.str.strip()
            
            # 兼容读取 Clave de incidencia 和 用于判定更新类型的 ID 列
            actual_cols = jira_df.columns.tolist()
            clave_col = 'Clave de incidencia' if 'Clave de incidencia' in actual_cols else ('Clave de incidence' if 'Clave de incidence' in actual_cols else None)
            id_col = 'ID de la incidencia' if 'ID de la incidencia' in actual_cols else ('Producto' if 'Producto' in actual_cols else None)
            
            if clave_col and 'Actualizada' in actual_cols and 'Resumen' in actual_cols and id_col:
                
                if st.button("⚡ 预解析并执行多语言 Jira 规则匹配"):
                    st.session_state.modified_rows = [] 
                    
                    # 遍历主数据库中的每一个（国家，产品）组合
                    for index, row in st.session_state.df.iterrows():
                        p_name = str(row['Producto']).strip()
                        c_name = str(row['País']).strip()
                        iso3_val = str(row['ISO3']).strip() if 'ISO3' in row else ""
                        
                        if pd.isna(row['Producto']) or p_name == 'nan':
                            continue
                        
                        # -----------------------------------------------------
                        # 1. 根据多语言和ISO3，找出所有属于这个国家的 Jira 任务
                        # -----------------------------------------------------
                        country_aliases = get_country_aliases(c_name, iso3_val)
                        
                        matched_jiras = pd.DataFrame()
                        for alias in country_aliases:
                            temp_match = jira_df[
                                jira_df['Resumen'].astype(str).str.contains(r'\b' + alias + r'\b|' + alias, case=False, na=False)
                            ]
                            if not temp_match.empty:
                                matched_jiras = pd.concat([matched_jiras, temp_match])
                        
                        if not matched_jiras.empty:
                            # 剔除重复匹配的任务
                            matched_jiras = matched_jiras.drop_duplicates()
                            
                            # -----------------------------------------------------
                            # 2. 遍历该国家的所有任务，严格按照 3 个级别判定归属
                            # -----------------------------------------------------
                            for _, jira_row in matched_jiras.iterrows():
                                jira_id_val = str(jira_row[id_col]).strip()
                                jira_id_val_lower = jira_id_val.lower()
                                
                                # 检查内容是否为空
                                is_empty_id = pd.isna(jira_row[id_col]) or jira_id_val == "" or jira_id_val_lower == "nan"
                                
                                # 解析该 Jira 任务的更新日期和链接
                                raw_date = str(jira_row['Actualizada']).split()[0]
                                parsed_date = pd.to_datetime(raw_date, dayfirst=True, errors='coerce')
                                clave = str(jira_row[clave_col]).strip()
                                new_link = f"https://visagov.atlassian.net/browse/{clave}"
                                
                                # 💡 【核心三级判定规则】：
                                if is_empty_id:
                                    # 规则A: 空白 ID -> 代表该国家所有产品的 Completa 更新
                                    st.session_state.df.at[index, 'Última actualización completa'] = parsed_date
                                    st.session_state.df.at[index, 'Nota_Producto'] = new_link
                                    st.session_state.modified_rows.append((c_name, p_name))
                                    break # 应用成功，不再看旧任务
                                    
                                elif jira_id_val_lower == 'parcial':
                                    # 规则B: 写了 'parcial' -> 代表该国家所有产品的 Parcial 更新
                                    st.session_state.df.at[index, 'Última actualización parcial'] = parsed_date
                                    st.session_state.df.at[index, 'Nota_Producto'] = new_link
                                    st.session_state.modified_rows.append((c_name, p_name))
                                    break # 应用成功，不再看旧任务
                                    
                                elif jira_id_val_lower == p_name.lower():
                                    # 规则C: 写了具体产品名 (且跟当前循环的产品名一致) -> 代表该单一产品的 Parcial 更新
                                    st.session_state.df.at[index, 'Última actualización parcial'] = parsed_date
                                    st.session_state.df.at[index, 'Nota_Producto'] = new_link
                                    st.session_state.modified_rows.append((c_name, p_name))
                                    break # 应用成功，不再看旧任务
                                    
                                # 如果都不符合（比如写了别的产品的名字），则自动 pass，去看下一条 Jira 记录

                    st.success(f"🎉 成功应用三级智能规则！共发现 {len(st.session_state.modified_rows)} 项数据变更，已在下方用蓝色高亮并为您置顶。请核对后点击下方 'Guardar Cambios' 保存。")
            else:
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
