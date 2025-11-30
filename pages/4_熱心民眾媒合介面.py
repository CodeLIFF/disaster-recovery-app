import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="志工媒合平台（熱心民眾）", layout="wide")

# ----- 緊湊模式 CSS（預設套用） -----
css = """
<style>
/* 卡片間距與 hr */
.stMarkdown hr, hr {
    margin-top: 1.0rem !important;
    margin-bottom: 1.0rem !important;
    height: 1px;
    background: #e6e6e6;
    border: none;
}
.card-spacer {
    height: 0.6rem !important;
    width: 100%;
}

/* 標籤 (tag) 樣式：保證每個標籤之間至少有一個字元寬度 */
.tag-label {
    display: inline-block;
    padding: 4px 8px;
    margin-right: 1ch; /* 至少一個字元寬度的空白 */
    border-radius: 6px;
    font-size: 14px;
    color: #333;
}

/* 緊湊模式的頁面間距微調（調整為原先的一半） */
.block-container {
    padding-top: 0.3rem !important;
    padding-bottom: 0.3rem !important;
}
.stApp .block-container > div {
    margin-top: 0.14rem !important;
    margin-bottom: 0.14rem !important;
}
.stButton>button {
    padding: 6px 10px !important;
    font-size: 0.95rem !important;
}
/* 工作時間 multiselect - 對應 #FFF8EC */
div[data-testid="stMultiSelect"]:nth-of-type(1) [data-baseweb="tag"] {
    background-color: #FFF8EC !important;
    color: #333 !important;
    border: 1px solid #FFF8EC !important;
}

/* 能力需求 multiselect - 對應 #ADEDCC */
div[data-testid="stMultiSelect"]:nth-of-type(2) [data-baseweb="tag"] {
    background-color: #ADEDCC !important;
    color: #333 !important;
    border: 1px solid #ADEDCC !important;
}

/* 提供資源 multiselect - 對應 #FFE3B3 */
div[data-testid="stMultiSelect"]:nth-of-type(3) [data-baseweb="tag"] {
    background-color: #FFE3B3 !important;
    color: #333 !important;
    border: 1px solid #FFE3B3 !important;
}

/* 建議交通 multiselect - 對應 #35D0C7 */
div[data-testid="stMultiSelect"]:nth-of-type(4) [data-baseweb="tag"] {
    background-color: #35D0C7 !important;
    color: white !important;
    border: 1px solid #35D0C7 !important;
}
/* 只針對搜尋按鈕 */
button[data-testid="baseButton-primary"][aria-label="search_btn"] {
    background-color: #e6e6e6 !important;
    color: #333 !important;
}
</style>
"""

st.markdown(css, unsafe_allow_html=True)

# ==========================================
# 1. 初始化設定與連線
# ==========================================

# 初始化 Session State (用來記住使用者身份與暫存報名狀態)
if "user_phone" not in st.session_state:
    st.session_state["user_phone"] = None  # 登入/報名後的電話
if "my_new_tasks" not in st.session_state:
    st.session_state["my_new_tasks"] = []  # 剛報名但還沒寫入 Sheet 的任務 ID

# Google Sheet 連線 (使用快取資源，避免重複連線)
@st.cache_resource
def get_sheet_connection():
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["google"],
        scopes=SCOPES
    )
    gc = gspread.authorize(creds)
    SHEET_ID = "1PbYajOLCW3p5vsxs958v-eCPgHC1_DnHf9G_mcFx9C0"
    return gc.open_by_key(SHEET_ID).sheet1

try:
    sheet = get_sheet_connection()
except Exception as e:
    st.error(f"無法連線至 Google Sheets，請檢查 secrets 設定: {e}")
    st.stop()

# ==========================================
# 2. 資料讀取與處理函式
# ==========================================

# 讀取資料 (設定 ttl=3 秒，3秒內重新整理不會真的去呼叫 Google API，保護額度)
@st.cache_data(ttl=3)
def load_data():
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # 清洗欄位名稱
        df.columns = df.columns.str.strip()
        
        # 轉型數值欄位
        for col in ["id_number", "selected_worker", "demand_worker"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        
        # 轉型文字欄位
        text_fields = ["phone", "line_id", "mission_name", "address", "work_time",
                       "skills", "resources", "transport", "note", "photo", "role", "name", "other"]
        for col in text_fields:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str).str.strip()
                
        return df
    except Exception as e:
        st.error(f"讀取資料失敗: {e}")
        return pd.DataFrame()

# 輔助函式：翻譯與標籤顯示
translate = {
    "morning": " 早上 (08-11) ",
    "noon": " 中午 (11-13) ",
    "afternoon": " 下午 (13-17) ",
    "night": " 晚上 (17-19) "
}
def t(value):
    value = str(value).strip()
    return f"{translate[value]} ({value})" if value in translate else value

def translate_list(text):
    parts = [p.strip() for p in str(text).split(",")]
    return "、".join([t(p) for p in parts if p])

def render_labels(text, mapping_dict, color="#FFD9C0"):
    # 以 class="tag-label" 並帶入背景色，確保標籤之間有至少一個字元的空間（CSS margin-right:1ch）
    parts = [p.strip() for p in str(text).split(",") if p.strip()]
    labels = []
    for p in parts:
        label = mapping_dict.get(p, p)
        # 使用 class + inline background color（可被 color 參數覆蓋）
        html = f'<span class="tag-label" style="background:{color};">{label}</span>'
        labels.append(html)
    return " ".join(labels)  # 用空白將 span 串起（使閱讀上更自然）

# UI 顯示字典
time_display = {
    "morning": " 早上 (08-11)",
    "noon": " 中午 (11-13)",
    "afternoon": " 下午 (13-17)",
    "night": " 晚上 (17-19)"
}
skills_display = {
    "supplies distribution": " 物資",
    "cleaning": " 清掃",
    "medical": " 醫療",
    "heavy lifting": " 搬運",
    "driver's license": " 駕照",
    "other": " 其他"
}
resources_display = {
    "tool": " 工具",
    "food": " 食物",
    "water": " 飲用水",
    "medical supplies": " 醫療",
    "hygiene supplies": " 清潔用品",
    "accommodation": " 住宿",
    "other": " 其他"
}
transport_display = {
    "train": " 火車",
    "bus": " 巴士",
    "walk": " 步行",
    "car": " 開車",
    "scooter": " 機車",
    "bike": " 單車",
    "other": " 其他"
}

# ==========================================
# 3. 程式主流程
# ==========================================

# --- 步驟 A: 讀取最新資料 ---
df = load_data()

# 分離任務與志工
if not df.empty:
    missions = df[(df["role"] == "victim") & (df["demand_worker"] > 0)].copy()
    volunteers = df[df["role"] == "volunteer"].copy()
else:
    missions = pd.DataFrame()
    volunteers = pd.DataFrame()

# --- 步驟 B: 處理報名頁面 (Signup Page) ---
if st.session_state.get("page") == "signup":
    st.title("📝 志工基本資料填寫")
    
    with st.form("signup_form"):
        st.info("感謝您的熱心！請填寫資料以完成報名。")
        name = st.text_input("姓名（必填）")
        phone = st.text_input("電話（必填，09開頭）")
        line_id = st.text_input("LINE ID（選填）")
        submitted = st.form_submit_button("確認送出")

    if submitted:
        # --- 1. 基礎格式驗證 ---
        if not name or not phone:
            st.warning("❌ 請完整填寫姓名與電話")
            st.stop()
        if not (phone.isdigit() and len(phone) == 10 and phone.startswith("09")):
            st.error("❌ 請輸入有效的台灣手機號碼（09開頭共10碼）")
            st.stop()
            
        task_id = st.session_state.get("selected_task_id")
        
        # --- 2. 定義手機號碼標準化函式 (讀取用) ---
        def normalize_phone(p):
            p = str(p).strip()
            # 如果是 9 開頭且長度為 9 (代表 0 被 Google 吃掉了)，補回 0
            if len(p) == 9 and p.startswith("9"):
                return "0" + p
            return p

        # --- 3. 強制即時檢查 (讀取 + 標準化) ---
        load_data.clear()  # 清除快取
        df_fresh = load_data() # 重新抓最新資料
        
        if not df_fresh.empty and "role" in df_fresh.columns:
            # 針對讀回來的資料，先做一次「補 0」動作，確保格式一致
            df_fresh["phone"] = df_fresh["phone"].apply(normalize_phone)
            
            vols_fresh = df_fresh[df_fresh["role"] == "volunteer"]
            
            # 檢查是否已報名此任務 (現在格式統一了，比對就會準確)
            is_duplicate = not vols_fresh[
                (vols_fresh["phone"] == phone) & 
                (vols_fresh["id_number"] == int(task_id))
            ].empty
            
            if is_duplicate:
                st.error("❌ 您已經報名過此任務，請勿重複提交！")
                if st.button("返回列表", key="dup_back"):
                    st.session_state["page"] = "task_list"
                    st.rerun()
                st.stop()

        # --- 4. 寫入資料 (強制保留 0)，並將該任務對應的受災戶聯絡資訊與提示一併寫入同一列（最後一欄）
        try:
            # 【關鍵修改】在 phone 前面加上 "'" (單引號)
            # 這會告訴 Google Sheets：「這是文字，不要把它變成數字！」
            phone_to_write = "'" + phone 

            # 先從剛抓回來的 df_fresh 找出該任務的受災戶資料（若有）
            victim_name = ""
            victim_phone = ""
            victim_line = ""
            victim_note = ""
            if not df_fresh.empty:
                victim_rows = df_fresh[(df_fresh["role"] == "victim") & (df_fresh["id_number"] == int(task_id))]
                if not victim_rows.empty:
                    vr = victim_rows.iloc[0]
                    victim_name = str(vr.get("name", "")).strip()
                    # 可能也要標準化 victim phone（如果 Google 吃掉 0）
                    victim_phone = normalize_phone(str(vr.get("phone", "")).strip())
                    victim_line = str(vr.get("line_id", "")).strip()
                    victim_note = str(vr.get("note", "")).strip()
            
            # 建立分行顯示的 contact_note（多行字串）
            if victim_name or victim_phone or victim_line or victim_note:
                contact_note = f"""這是你選擇幫忙的受災戶資料，可以自行連絡他了喔!
受災戶姓名：{victim_name}
電話：{victim_phone}
LineID：{victim_line}
備註：{victim_note}"""
            else:
                contact_note = "受災戶聯絡資料：無（目標任務未在 Sheet 找到對應受災戶）。"
            
            # 構造要寫入的 row：保留原本欄位數量的基礎上，把 contact_note 放在最後一欄（若你有固定欄位結構，可對應修改）
            row_data = [
                int(task_id), "volunteer", name, phone_to_write, line_id,
                "", "", "", "", "", "", contact_note
            ]
            sheet.append_row(row_data)
            
            # 更新 Session（但不要立刻 rerun/返回，先讓使用者看到訊息）
            st.session_state["user_phone"] = phone
            st.session_state["my_new_tasks"].append(task_id)
            load_data.clear()
            
            # 顯示成功訊息與聯絡資訊，並提供「返回列表」按鈕由使用者自行點擊以回到列表（避免訊息閃過）
            st.success("🎉 報名成功！")
            # 使用 st.markdown 以保留換行顯示（info 也可，但 markdown 更靈活）
            st.markdown(f"```\n{contact_note}\n```")
            st.write("")  # 空行做些間距
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("返回列表"):
                    st.session_state["page"] = "task_list"
                    st.rerun()
            with col2:
                if st.button("留在此頁", key="stay_on_signup"):
                    st.info("您仍停留在報名頁面，可複查資訊或按返回列表。")
            
        except Exception as e:
            st.error(f"連線錯誤: {e}")
            st.stop()
    if st.button("取消返回"):
        st.session_state["page"] = "task_list"
        st.rerun()
    
    st.stop() # 停止執行後面的程式碼

# --- 步驟 C: 任務列表頁面 (Task List Page) ---

st.title("災後人力媒合平台（熱心民眾端）")
st.caption("以下為受災戶上傳的最新需求")

# 1. 搜尋過濾
st.subheader("🔍 篩選條件")

col1, col2, col3, col4 = st.columns(4)

with col1:
    time_options = list(time_display.values())
    selected_times = st.multiselect("工作時間", time_options, placeholder="選擇時段")

with col2:
    skill_options = list(skills_display.values())
    selected_skills = st.multiselect("能力需求", skill_options, placeholder="選擇技能")

with col3:
    resource_options = list(resources_display.values())
    selected_resources = st.multiselect("提供資源", resource_options, placeholder="選擇資源")

with col4:
    transport_options = list(transport_display.values())
    selected_transports = st.multiselect("建議交通", transport_options, placeholder="選擇交通方式")

# 地址關鍵字搜尋
keyword = st.text_input("🔍 地址關鍵字搜尋", placeholder="輸入地址關鍵字")

# 搜尋按鈕
search_button = st.button("🔍 開始搜尋", type="primary", use_container_width=False, key="search_btn")

# 反向映射字典（從顯示文字找回原始 key）
time_reverse = {v: k for k, v in time_display.items()}
skills_reverse = {v: k for k, v in skills_display.items()}
resources_reverse = {v: k for k, v in resources_display.items()}
transport_reverse = {v: k for k, v in transport_display.items()}

# 初始化過濾結果
filtered_missions = missions.copy()

# 只有按下搜尋按鈕或有任何選項時才進行過濾
if search_button or selected_times or selected_skills or selected_resources or selected_transports or keyword:
    # 過濾工作時間（OR 邏輯：符合任一選項即可）
    if selected_times:
        time_keys = [time_reverse[t] for t in selected_times]
        time_filter = filtered_missions["work_time"].apply(
            lambda x: any(key in str(x) for key in time_keys)
        )
        filtered_missions = filtered_missions[time_filter]

    # 過濾技能（OR 邏輯：符合任一選項即可）
    if selected_skills:
        skill_keys = [skills_reverse[s] for s in selected_skills]
        skill_filter = filtered_missions["skills"].apply(
            lambda x: any(key in str(x) for key in skill_keys)
        )
        filtered_missions = filtered_missions[skill_filter]

    # 過濾資源（OR 邏輯：符合任一選項即可）
    if selected_resources:
        resource_keys = [resources_reverse[r] for r in selected_resources]
        resource_filter = filtered_missions["resources"].apply(
            lambda x: any(key in str(x) for key in resource_keys)
        )
        filtered_missions = filtered_missions[resource_filter]

    # 過濾交通方式（OR 邏輯：符合任一選項即可）
    if selected_transports:
        transport_keys = [transport_reverse[t] for t in selected_transports]
        transport_filter = filtered_missions["transport"].apply(
            lambda x: any(key in str(x) for key in transport_keys)
        )
        filtered_missions = filtered_missions[transport_filter]

    # 過濾地址關鍵字
    if keyword:
        k = keyword.strip()
        filtered_missions = filtered_missions[
            filtered_missions["address"].str.contains(k, case=False, na=False)
        ]

st.write(f"共 {len(filtered_missions)} 筆需求")
st.markdown("---")

# 2. 預先計算所有任務的「目前人數」 (避免在迴圈內算)
#    這會產出一個字典: {任務ID: 志工人數, 任務ID2: 志工人數...}
mission_counts = volunteers["id_number"].value_counts().to_dict()

# 3. 判斷「當前使用者」的狀態
current_user_phone = st.session_state.get("user_phone")

# 找出使用者在 Sheet 裡報名過的任務 ID
joined_in_sheet = []
if current_user_phone:
    joined_in_sheet = volunteers[volunteers["phone"] == current_user_phone]["id_number"].tolist()

# 合併「Sheet 裡的舊紀錄」和「剛按下報名的新紀錄」
# 使用 set 來去除重複，這是判斷按鈕狀態的唯一真理
all_my_joined_tasks = set(joined_in_sheet + st.session_state["my_new_tasks"])
has_joined_any = len(all_my_joined_tasks) > 0 # 是否已經報名過任一項

# 4. 顯示卡片迴圈 (這裡不再呼叫 API，速度極快)
for idx, row in filtered_missions.iterrows():
    tid = int(row["id_number"])
    
    # 取得該任務目前人數 (加上使用者剛報名但還沒同步到 sheet 的部分)
    # 如果使用者剛報名這個任務，人數要在顯示上 +1 (視覺優化)
    current_count = mission_counts.get(tid, 0)
    if tid in st.session_state["my_new_tasks"] and tid not in joined_in_sheet:
        current_count += 1
        
    left, right = st.columns([2, 1])
    
    with left:
        # 新增：以 Google Sheet 的 mission_name 當作每個任務的標題（若 mission_name 空白則顯示地址或任務編號）
        mission_title = str(row.get("mission_name", "")).strip()
        addr = str(row.get("address", "")).strip()
        if mission_title:
            st.markdown(f"### {mission_title}")
        else:
            # fallback 顯示 address 或任務編號
            if addr:
                st.markdown(f"### 任務地址：{addr}")
            else:
                st.markdown(f"### 任務 #{tid}")
        
        # 顯示 address（成為提供資訊之一）
        if addr:
            st.markdown(f"地址： {addr}")
        
        # 將小標與格子化標籤合在同一行：工作時間
        time_html = f'<span style="font-weight:600;margin-right:20px"> 工作時間：</span>{render_labels(row["work_time"], time_display, "#FFF8EC")}'
        st.markdown(time_html, unsafe_allow_html=True)

        st.markdown(f" 人數： {current_count} / {row['demand_worker']}")
        
        # 將小標與格子化標籤合在同一行：提供資源
        resources_html = f'<span style="font-weight:600;margin-right:25px"> 提供資源：</span>{render_labels(row["resources"], resources_display, "#FFE3B3")}'
        st.markdown(resources_html, unsafe_allow_html=True)

        # 將小標與格子化標籤合在同一行：能力需求
        skills_html = f'<span style="font-weight:600;margin-right:25px"> 能力需求：</span>{render_labels(row["skills"], skills_display, "#ADEDCC")}'
        st.markdown(skills_html, unsafe_allow_html=True)

        # 將小標與格子化標籤合在同一行：建議交通方式
        transport_html = f'<span style="font-weight:600;margin-right:25px"> 建議交通方式：</span>{render_labels(row["transport"], transport_display, "#35D0C7")}'
        st.markdown(transport_html, unsafe_allow_html=True)
        
        # 備註先顯示
        st.markdown(f" 備註： {row['note']}")

        # 把「已報名志工」移到備註下方顯示（如有）
        task_vols = volunteers[volunteers["id_number"] == tid]
        if not task_vols.empty:
            vols_display = []
            for _, v in task_vols.iterrows():
                v_phone = str(v.get('phone', ''))
                show_phone = v_phone[-3:] if len(v_phone) >= 3 else ""
                vols_display.append(f"{v.get('name','匿名')} ({show_phone})")
            st.markdown("**已報名志工：** " + "、".join(vols_display))

        # --- 按鈕邏輯 (核心修正) ---
        is_full = current_count >= row["demand_worker"]
        is_joined_this = tid in all_my_joined_tasks
        
        # 檢查時段衝突 (簡易版)
        task_slots = [s.strip() for s in str(row["work_time"]).split(",")]
        # 如果要檢查時段衝突，需撈出使用者已報名任務的時段... (此處省略複雜邏輯，先做基礎阻擋)

        if is_joined_this:
            st.success("✅ 您已報名此任務")
        elif has_joined_any:
            # 如果你希望一人只能報名一項：
            st.warning("⚠ 您已報名其他任務 (每人限一項)")
        elif is_full:
            st.error("❌ 已額滿")
        else:
            if st.button("我要報名", key=f"btn_{tid}"):
                st.session_state["page"] = "signup"
                st.session_state["selected_task_id"] = tid
                st.rerun()

    with right:
        photo = str(row.get("photo", "")).strip()
        if photo.startswith("http"):
            st.image(photo, use_column_width=True)
        else:
            st.info("尚無照片")
            
    # 用自定義 spacer 讓每個卡片之間有較多留白，視覺更舒適
    st.markdown("<div class='card-spacer'></div>", unsafe_allow_html=True)
