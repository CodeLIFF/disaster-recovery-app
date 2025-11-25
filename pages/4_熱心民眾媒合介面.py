import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="志工媒合平台（熱心民眾）", layout="wide")

# ---------------- Google Sheet 連線 ----------------
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
sheet = gc.open_by_key(SHEET_ID).sheet1

# -----------------------------------
# 讀取資料（只讀一次，避免 df 被覆蓋）
# -----------------------------------
data = sheet.get_all_records()
df = pd.DataFrame(data)
missions = df[df["role"] == "victim"].copy()
volunteers = df[df["role"] == "volunteer"].copy()

missions["id_number"] = pd.to_numeric(missions["id_number"], errors="coerce").fillna(0).astype(int)
volunteers["id_number"] = pd.to_numeric(volunteers["id_number"], errors="coerce").fillna(0).astype(int)

text_fields = ["phone", "line_id", "mission_name", "address", "work_time",
               "skills", "resources", "transport", "note", "photo"]

for col in text_fields:
    if col in df.columns:
        df[col] = df[col].fillna("").astype(str)
translate = {
    "morning": "早上",
    "noon": "中午",
    "afternoon": "下午",
    "night": "晚上",
    "tool": "工具",
    "food": "食物",
    "water": "飲用水",
    "hygiene supplies": "清潔用品",
    "cleaning": "清潔",
    "heavy lifting": "粗重物品搬運",
    "train": "火車",
    "walk": "步行",
    "scooter": "機車",
}

def t(value):
    """把英文轉成 中文(英文) 的格式"""
    value = value.strip()
    if value in translate:
        return f"{translate[value]} ({value})"
    return value

def translate_list(text):
    parts = [p.strip() for p in text.split(",")]
    translated = [t(p) for p in parts if p]
    return "、".join(translated)

# 清欄位空白
df.columns = df.columns.str.strip()

# 修正欄位名（你的表格 id 是 id_number）
if "id_number" in df.columns:
    df["id_number"] = pd.to_numeric(df["id_number"], errors="coerce").fillna(0).astype(int)

df["selected_worker"] = pd.to_numeric(df["selected_worker"], errors="coerce").fillna(0).astype(int)
df["demand_worker"] = pd.to_numeric(df["demand_worker"], errors="coerce").fillna(0).astype(int)

# === 志工基本資料填寫頁 ===
if st.session_state.get("page") == "signup":
    st.title("志工基本資料填寫")

    name = st.text_input("姓名（必填）")
    phone = st.text_input("電話（必填）")
    line_id = st.text_input("LINE ID（選填）")

    if st.button("送出報名"):
        if not name or not phone:
            st.warning("請完整填寫姓名與電話")
            st.stop()

        # 記錄志工資料到 session
        st.session_state["current_volunteer_name"] = name
        st.session_state["current_volunteer_phone"] = phone
        st.session_state["current_volunteer_line"] = line_id

        # 🔥 取得報名的任務 ID
        task_id = st.session_state.get("selected_task_id")

        # 更新 Google Sheet 上 selected_worker 數量 + 新增志工
        if task_id:
            # 找出任務目前 selected_worker 欄位所在 row
            task_idx = df[df["id_number"] == task_id].index
            df.loc[task_idx, "selected_worker"] += 1

            # 新增一筆志工資料到 Google Sheet
            new_row = [
                "volunteer",
                task_id,
                name,
                phone,
                line_id,
                "", "", "", "", "", ""  # 填滿以避免欄位錯位
            ]
            sheet.append_row(new_row)

            # 把 updated 的 df 回寫回去（包含 selected_worker +1）
            update_sheet(df)

            st.success("🎉 報名成功！感謝您伸出援手 ❤️")
            st.session_state["page"] = "task_list"
            st.rerun()
    
        st.stop()



# -----------------------------------
# 過濾掉「只有註冊但未填需求」的人
# -----------------------------------
required_cols = ["mission_name", "address", "work_time", "demand_worker"]

df = df.dropna(subset=required_cols)

df = df[
    (df["mission_name"] != "") &
    (df["address"] != "") &
    (df["work_time"] != "") &
    (df["demand_worker"] != 0)
]

# -----------------------------------
# 前端 UI
# -----------------------------------
st.title("災後人力媒合平台（熱心民眾端）")
st.caption("以下為受災戶上傳的最新需求")

keyword = st.text_input("搜尋（地址、能力、備註、提供資源）")

filtered = df.copy()

if keyword:
    keyword = keyword.strip()
    filtered = filtered[
        filtered["address"].str.contains(keyword, case=False) |
        filtered["skills"].str.contains(keyword, case=False) |
        filtered["resources"].str.contains(keyword, case=False) |
        filtered["note"].str.contains(keyword, case=False)
    ]

st.write(f"共 {len(filtered)} 筆需求")
st.markdown("---")


# 取得目前志工身份驗證資訊（提前）
vol_id = st.session_state.get("current_volunteer_id")

st.markdown("""
<style>
.label {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 12px;
    margin: 2px;
    font-size: 14px;
    color: white;
}
.time { background-color: #4A90E2; }
.skill { background-color: #7B61FF; }
.resource { background-color: #F5A623; }
.transport { background-color: #50C878; }
</style>
""", unsafe_allow_html=True)

time_display = {
    "morning": "🌅 早上 (08:00–11:00)",
    "noon": "🌞 中午 (11:00–13:00)",
    "afternoon": "🌇 下午 (13:00–17:00)",
    "night": "🌃 晚上 (17:00–19:00)",
} 
skills_display = {
    "supplies distribution": "📦 物資發放",
    "cleaning": "🧹 清掃",
    "medical": "🩺 醫療",
    "heavy lifting": "🏋️ 搬運",
    "driver's license": "🚗 駕照",
    "other skills": "✨ 其他",
}
resources_display = {
    "tools": "🛠 工具",
    "food": "🍱 食物",
    "water": "🚰 水",
    "medical supplies": "💊 醫療用品",
    "hygiene supplies": "🧻 衛生用品",
    "accommodation": "🏠 住宿",
    "other resources": "➕ 其他",
}
transport_display = {
    "train": "🚆 火車",
    "bus": "🚌 巴士",
    "on foot": "🚶‍♀️ 步行",
    "car": "🚗 開車",
    "scooter": "🛵 機車",
    "bike": "🚲 腳踏車",
    "other transportation": "➕ 其他",
}
def render_labels(text, mapping_dict, color="#FFD9C0"):
    """
    text: 例如 "morning, afternoon"
    mapping_dict: 對應的翻譯字典
    color: 背景顏色（可自訂）
    """
    parts = [p.strip() for p in text.split(",") if p.strip()]
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
        ">{label}</span>
        """
        labels.append(html)

    return "".join(labels)

# -----------------------------------
# 卡片列表
# -----------------------------------
for idx, row in filtered.iterrows():
    left, right = st.columns([2, 1])

    with left:
        st.markdown(f"**🕒 工作時間：** {translate_list(row['work_time'])}", unsafe_allow_html=True)
        st.markdown(render_labels(row["work_time"], time_display, "#FFE6C7"), unsafe_allow_html=True)
        current_count = len(volunteers[volunteers["id_number"] == row["id_number"]])
        st.markdown(f"**👥 需求人數：** {current_count} / {row['demand_worker']}")
        # 顯示已報名志工名單
        vols = volunteers[volunteers["id_number"] == row["id_number"]]
        
        if not vols.empty:
            st.write("👥 已報名志工：")
            for _, vol in vols.iterrows():
                phone = vol["phone"]
                masked_phone = phone[:4] + "****"  # 遮蔽後四碼
                st.write(f"- {vol['name']}（{masked_phone}）")
        st.markdown(f"**🧰 提供資源：** {translate_list(row['resources'])}", unsafe_allow_html=True)
        st.markdown(render_labels(row["resources"], resources_display, "#FFF9C4"), unsafe_allow_html=True)
        st.markdown(f"**💪 能力需求：** {translate_list(row['skills'])}", unsafe_allow_html=True)
        st.markdown(render_labels(row["skills"], skills_display, "#E8F5E9"), unsafe_allow_html=True)
        st.markdown(f"**🚗 交通建議：** {translate_list(row['transport'])}", unsafe_allow_html=True)
        st.markdown(render_labels(row["transport"], transport_display, "#E3F2FD"), unsafe_allow_html=True)
        st.markdown(f"**📝 備註：** {row['note']}")

        vol_id = st.session_state.get("current_volunteer_id", "")
        vol_phone = st.session_state.get("current_volunteer_phone", "")
        already_joined = len(volunteers[
            (volunteers["phone"] == vol_phone) &
            (volunteers["id_number"] == row["id_number"])
        ]) > 0


        
        # 人數已滿
        if row["selected_worker"] >= row["demand_worker"]:
            st.error("❌ 此任務人數已足夠")
        elif already_joined:
            st.success("✔ 你已報名此任務")
        else:
            if st.button("我要報名", key=f"apply_{row['id_number']}"):
                st.session_state["page"] = "signup"  # 跳到填資料頁
                st.session_state["selected_task_id"] = row["id_number"]  # 記住是報哪個任務
                st.rerun()
        

    with right:
        #if row["photo"]:
            #st.image(row["photo"], use_column_width=True)
        #else:
            #st.info("尚無照片")
        
        photo_url = str(row.get("photo", "")).strip()

        # 只接受 HTTP 開頭的圖片連結
        if photo_url.startswith("http"):
            try:
                st.image(photo_url, use_column_width=True)
            except:
                st.warning("📷 照片載入失敗（連結格式可能錯誤）")
        else:
            st.info("尚無照片")

    st.markdown("---")
    
