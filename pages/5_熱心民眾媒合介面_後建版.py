import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="志工媒合平台（熱心民眾）", layout="wide")

# ---------------- Google Sheet 連線 ----------------
# 使用 @st.cache_resource 避免每次操作都重新連線
@st.cache_resource
def get_google_sheet_client():
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["google"],
        scopes=SCOPES
    )
    gc = gspread.authorize(creds)
    return gc

try:
    gc = get_google_sheet_client()
    SHEET_ID = "1PbYajOLCW3p5vsxs958v-eCPgHC1_DnHf9G_mcFx9C0"
    sheet = gc.open_by_key(SHEET_ID).sheet1
except Exception as e:
    st.error(f"連線失敗，請檢查 secrets 設定: {e}")
    st.stop()

# ---------------- 輔助函式 ----------------
translate = {
    "morning": "早上", "noon": "中午", "afternoon": "下午", "night": "晚上",
    "tool": "工具", "food": "食物", "water": "飲用水",
    "hygiene supplies": "清潔用品", "cleaning": "清潔",
    "heavy lifting": "粗重物品搬運", "train": "火車",
    "walk": "步行", "scooter": "機車",
}

def t(value):
    value = str(value).strip()
    if value in translate:
        return f"{translate[value]} ({value})"
    return value

def translate_list(text):
    parts = [p.strip() for p in str(text).split(",")]
    translated = [t(p) for p in parts if p]
    return "、".join(translated)

def render_labels(text, mapping_dict, color="#FFD9C0"):
    parts = [p.strip() for p in str(text).split(",") if p.strip()]
    labels = []
    for p in parts:
        label = mapping_dict.get(p, p)
        html = f"""
        <span style="
            background:{color};
            padding:4px 8px;
            margin-right:6px;
            border-radius:6px;
            display:inline-block;
            font-size: 14px;
            color: #333;
        ">{label}</span>
        """
        labels.append(html)
    return "".join(labels)

# 定義顯示字典
time_display = {
    "morning": "🌅 早上 (08:00–11:00)", "noon": "🌞 中午 (11:00–13:00)",
    "afternoon": "🌇 下午 (13:00–17:00)", "night": "🌃 晚上 (17:00–19:00)",
} 
skills_display = {
    "supplies distribution": "📦 物資發放", "cleaning": "🧹 清掃",
    "medical": "🩺 醫療", "heavy lifting": "🏋️ 搬運",
    "driver's license": "🚗 駕照", "other skills": "✨ 其他",
}
resources_display = {
    "tools": "🛠 工具", "food": "🍱 食物", "water": "🚰 水",
    "medical supplies": "💊 醫療用品", "hygiene supplies": "🧻 衛生用品",
    "accommodation": "🏠 住宿", "other resources": "➕ 其他",
}
transport_display = {
    "train": "🚆 火車", "bus": "🚌 巴士", "on foot": "🚶‍♀️ 步行",
    "car": "🚗 開車", "scooter": "🛵 機車", "bike": "🚲 腳踏車",
    "other transportation": "➕ 其他",
}

# -----------------------------------
# 讀取資料（每次頁面重整讀取一次，不做快取以確保數據即時）
# -----------------------------------
data = sheet.get_all_records()
df = pd.DataFrame(data)

# 清欄位空白
df.columns = df.columns.str.strip()

# 數值欄位處理
numeric_cols = ["id_number", "selected_worker", "demand_worker"]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

# 文字欄位處理
text_fields = ["phone", "line_id", "mission_name", "address", "work_time",
               "skills", "resources", "transport", "note", "photo", "role", "name"]
for col in text_fields:
    if col in df.columns:
        df[col] = df[col].fillna("").astype(str).str.strip()

# === 志工基本資料填寫頁 ===
if st.session_state.get("page") == "signup":
    st.title("志工基本資料填寫")

    with st.form("signup_form"):
        name = st.text_input("姓名（必填）")
        phone = st.text_input("電話（必填）")
        line_id = st.text_input("LINE ID（選填）")
        submitted = st.form_submit_button("送出報名")

    if submitted:
        if not name or not phone:
            st.warning("請完整填寫姓名與電話")
            st.stop()
    
        # 📌 台灣手機號碼驗證
        if not (phone.isdigit() and len(phone) == 10 and phone.startswith("09")):
            st.error("⚠ 請輸入有效的台灣手機號碼（必須為 09 開頭且共 10 碼）")
            st.stop()
    
        # 儲存 Session 供前端判斷
        st.session_state["current_volunteer_name"] = name
        st.session_state["current_volunteer_phone"] = phone
        st.session_state["current_volunteer_line"] = line_id
    
        task_id = st.session_state.get("selected_task_id")
        
        if task_id:
            # 檢查是否重複報名 (直接用記憶體中的 df 檢查，節省 API)
            existing_signup = df[
                (df["role"] == "volunteer") & 
                (df["phone"] == phone)
            ]

            if not existing_signup.empty:
                st.error("⚠ 每位志工限報一項任務，請勿重複報名 🙏")
                if st.button("回首頁"):
                    st.session_state["page"] = "task_list"
                    st.rerun()
                st.stop()
            
            # 寫入 Google Sheet
            # 注意：這裡 append_row 的順序必須跟 Google Sheet 欄位順序完全一致
            # 假設順序: id_number, role, name, phone, line_id, ... (後面放空值)
            
            # 為了安全，建議補滿空字串以符合欄位數
            row_data = [
                int(task_id), "volunteer", name, phone, line_id, 
                "", "", "", "", "", "", "" # 根據你的欄位數量補齊空字串
            ]
            
            try:
                sheet.append_row(row_data)
                
                # 更新計數器 (選用: 如果你的前端依賴 selected_worker 欄位)
                # 建議：未來可以直接用程式計算 row 數量，不用更新這個 cell，避免並發衝突
                # 這裡為了相容舊邏輯先保留，但做錯誤處理
                try:
                    task_idx = df[df["id_number"] == task_id].index
                    if not task_idx.empty:
                        # 找到實際在 Sheet 中的行數 (index + 2 因為 header 是 row 1)
                        real_row_idx = task_idx[0] + 2 
                        col_idx = df.columns.get_loc("selected_worker") + 1
                        current_val = df.loc[task_idx[0], "selected_worker"]
                        sheet.update_cell(real_row_idx, col_idx, int(current_val) + 1)
                except Exception as ex:
                    print(f"更新計數失敗，但不影響報名: {ex}")

                st.success("🎉 報名成功！感謝您伸出援手 ❤️")
                st.session_state["page"] = "task_list"
                st.rerun()
            except Exception as e:
                st.error(f"寫入資料失敗: {e}")
                st.stop()

    if st.button("取消返回"):
        st.session_state["page"] = "task_list"
        st.rerun()
    
    st.stop()

# ==========================================
# 主頁面：任務列表
# ==========================================

# 1. 資料前處理：分離需求 (Mission) 與志工 (Volunteer)
df_missions = df[
    (df["role"] == "victim") & 
    (df["mission_name"] != "") & 
    (df["demand_worker"] > 0)
].copy()

df_volunteers = df[df["role"] == "volunteer"].copy()

# 2. UI 標題
st.title("災後人力媒合平台（熱心民眾端）")
st.caption("以下為受災戶上傳的最新需求")

keyword = st.text_input("搜尋（地址、能力、備註、提供資源）")

# 3. 搜尋過濾
if keyword:
    keyword = keyword.strip()
    df_missions = df_missions[
        df_missions["address"].str.contains(keyword, case=False) |
        df_missions["skills"].str.contains(keyword, case=False) |
        df_missions["resources"].str.contains(keyword, case=False) |
        df_missions["note"].str.contains(keyword, case=False)
    ]

st.write(f"共 {len(df_missions)} 筆需求")
st.markdown("---")

# 4. 取得目前使用者的 Session 資訊 (用於判斷是否已報名)
current_user_phone = st.session_state.get("current_volunteer_phone", "")

# 找出使用者已參加的任務 (全域)
my_tasks = df_volunteers[df_volunteers["phone"] == current_user_phone]
my_task_slots = []
for _, row in my_tasks.iterrows():
    # 假設 row 關聯回 mission 的時間，這裡簡化處理：
    # 因為志工資料列沒有 work_time，我們需要用 id_number 去對應 mission
    mission_detail = df_missions[df_missions["id_number"] == row["id_number"]]
    if not mission_detail.empty:
        slots = str(mission_detail.iloc[0]["work_time"]).split(",")
        my_task_slots.extend([s.strip() for s in slots])

# 5. 渲染卡片 (優化版：不在此處呼叫 API)
for idx, row in df_missions.iterrows():
    mission_id = row["id_number"]
    
    # 計算目前志工人數 (直接用 Pandas 算，不呼叫 Google Sheet)
    current_volunteers = df_volunteers[df_volunteers["id_number"] == mission_id]
    current_count = len(current_volunteers)
    
    left, right = st.columns([2, 1])

    with left:
        st.markdown(f"**🕒 工作時間：** {translate_list(row['work_time'])}", unsafe_allow_html=True)
        st.markdown(render_labels(row["work_time"], time_display, "#FFE6C7"), unsafe_allow_html=True)
        
        st.markdown(f"**👥 需求人數：** {current_count} / {row['demand_worker']}")
        
        # 顯示已報名志工 (隱碼處理)
        if current_count > 0:
            st.write("👥 已報名志工：")
            for _, vol in current_volunteers.iterrows():
                v_phone = str(vol['phone'])
                display_phone = v_phone[-3:] if len(v_phone) >= 3 else v_phone
                st.caption(f"- {vol['name']} (***{display_phone})")

        st.markdown(f"**🧰 提供資源：** {translate_list(row['resources'])}", unsafe_allow_html=True)
        st.markdown(render_labels(row["resources"], resources_display, "#FFF9C4"), unsafe_allow_html=True)
        
        st.markdown(f"**💪 能力需求：** {translate_list(row['skills'])}", unsafe_allow_html=True)
        st.markdown(render_labels(row["skills"], skills_display, "#E8F5E9"), unsafe_allow_html=True)
        
        st.markdown(f"**🚗 交通建議：** {translate_list(row['transport'])}", unsafe_allow_html=True)
        st.markdown(render_labels(row["transport"], transport_display, "#E3F2FD"), unsafe_allow_html=True)
        
        st.markdown(f"**📝 備註：** {row['note']}")

        # ---- 按鈕狀態邏輯 ----
        is_full = current_count >= row["demand_worker"]
        
        # 是否已報名此任務
        is_joined_this = not current_volunteers[current_volunteers["phone"] == current_user_phone].empty
        
        # 是否時段衝突 (簡單檢查)
        mission_slots = [s.strip() for s in str(row["work_time"]).split(",")]
        is_conflict = any(slot in my_task_slots for slot in mission_slots) and not is_joined_this

        if is_joined_this:
            st.success("✔ 您已報名此任務")
        elif is_full:
            st.error("❌ 此任務人數已額滿")
        elif is_conflict:
            st.warning("⚠ 時段與您已報名的任務衝突")
        else:
            if st.button("我要報名", key=f"btn_{mission_id}"):
                st.session_state["page"] = "signup"
                st.session_state["selected_task_id"] = mission_id
                st.rerun()

    with right:
        photo_url = str(row.get("photo", "")).strip()
        if photo_url.startswith("http"):
            st.image(photo_url, use_column_width=True)
        else:
            st.info("尚無照片")

    st.markdown("---")
    updated = df[df["id"] == task_id].iloc[0]
    st.write(f"🎯 更新後已選志工：{updated['selected_people']} 人")

    # 清除狀態（避免重新載入時重複顯示）
    st.session_state.accepted_task = None
