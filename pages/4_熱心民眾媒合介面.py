import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="志工媒合平台（熱心民眾）", layout="wide")

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
                       "skills", "resources", "transport", "note", "photo", "role", "name"]
        for col in text_fields:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str).str.strip()
                
        return df
    except Exception as e:
        st.error(f"讀取資料失敗: {e}")
        return pd.DataFrame()

# 輔助函式：翻譯與標籤顯示
translate = {
    "morning": "早上", "noon": "中午", "afternoon": "下午", "night": "晚上",
    "tool": "工具", "food": "食物", "water": "飲用水",
    "hygiene supplies": "清潔用品", "cleaning": "清潔",
    "heavy lifting": "粗重物品搬運", "train": "火車", "walk": "步行", "scooter": "機車",
}
def t(value):
    value = str(value).strip()
    return f"{translate[value]} ({value})" if value in translate else value

def translate_list(text):
    parts = [p.strip() for p in str(text).split(",")]
    return "、".join([t(p) for p in parts if p])

def render_labels(text, mapping_dict, color="#FFD9C0"):
    parts = [p.strip() for p in str(text).split(",") if p.strip()]
    labels = []
    for p in parts:
        label = mapping_dict.get(p, p)
        html = f'<span style="background:{color};padding:4px 8px;margin-right:6px;border-radius:6px;display:inline-block;font-size:14px;color:#333;">{label}</span>'
        labels.append(html)
    return "".join(labels)

# UI 顯示字典
time_display = {"morning": "🌅 早上 (08-11)", "noon": "🌞 中午 (11-13)", "afternoon": "🌇 下午 (13-17)", "night": "🌃 晚上 (17-19)"}
skills_display = {"supplies distribution": "📦 物資", "cleaning": "🧹 清掃", "medical": "🩺 醫療", "heavy lifting": "🏋️ 搬運", "driver's license": "🚗 駕照", "other skills": "✨ 其他"}
resources_display = {"tools": "🛠 工具", "food": "🍱 食物", "water": "🚰 水", "medical supplies": "💊 醫療", "hygiene supplies": "🧻 衛生", "accommodation": "🏠 住宿", "other resources": "➕ 其他"}
transport_display = {"train": "🚆 火車", "bus": "🚌 巴士", "walk": "🚶 步行", "car": "🚗 開車", "scooter": "🛵 機車", "bike": "🚲 單車", "other transportation": "➕ 其他"}

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

        # --- 4. 寫入資料 (強制保留 0) ---
        try:
            # 【關鍵修改】在 phone 前面加上 "'" (單引號)
            # 這會告訴 Google Sheets：「這是文字，不要把它變成數字！」
            phone_to_write = "'" + phone 
            
            row_data = [
                int(task_id), "volunteer", name, phone_to_write, line_id, 
                "", "", "", "", "", "", "" 
            ]
            sheet.append_row(row_data)
            
            # 更新 Session
            st.session_state["user_phone"] = phone
            st.session_state["my_new_tasks"].append(task_id)
            load_data.clear()
            
            st.success("🎉 報名成功！")
            st.session_state["page"] = "task_list"
            st.rerun()
            
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
keyword = st.text_input("🔍 搜尋（地址、能力、資源、備註）")
filtered_missions = missions.copy()
if keyword:
    k = keyword.strip()
    filtered_missions = filtered_missions[
        filtered_missions["address"].str.contains(k, case=False) |
        filtered_missions["skills"].str.contains(k, case=False) |
        filtered_missions["resources"].str.contains(k, case=False) |
        filtered_missions["note"].str.contains(k, case=False)
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
        st.markdown(f"**🕒 時間：** {translate_list(row['work_time'])}")
        st.markdown(render_labels(row["work_time"], time_display, "#FFE6C7"), unsafe_allow_html=True)
        
        st.markdown(f"**👥 人數：** {current_count} / {row['demand_worker']}")
        
        # 顯示志工名單 (針對該任務 ID)
        task_vols = volunteers[volunteers["id_number"] == tid]
        if not task_vols.empty:
            st.caption("已報名志工：")
            for _, v in task_vols.iterrows():
                v_phone = str(v['phone'])
                show_phone = v_phone[-3:] if len(v_phone) >= 3 else "***"
                st.caption(f"- {v['name']} (***{show_phone})")
        
        st.markdown(f"**🧰 資源：** {translate_list(row['resources'])}")
        st.markdown(render_labels(row["resources"], resources_display, "#FFF9C4"), unsafe_allow_html=True)
        
        st.markdown(f"**💪 能力：** {translate_list(row['skills'])}")
        st.markdown(render_labels(row["skills"], skills_display, "#E8F5E9"), unsafe_allow_html=True)
        
        st.markdown(f"**🚗 交通：** {translate_list(row['transport'])}")
        st.markdown(render_labels(row["transport"], transport_display, "#E3F2FD"), unsafe_allow_html=True)
        
        st.markdown(f"**📝 備註：** {row['note']}")

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
            
    st.markdown("---")
    
