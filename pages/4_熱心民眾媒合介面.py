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
# 讀取資料（分割任務與志工）
# -----------------------------------
data = sheet.get_all_records()
df = pd.DataFrame(data)

missions = df[df["role"] == "victim"].copy()
volunteers = df[df["role"] == "volunteer"].copy()

missions["id_number"] = pd.to_numeric(missions["id_number"], errors="coerce").fillna(0).astype(int)
volunteers["id_number"] = pd.to_numeric(volunteers["id_number"], errors="coerce").fillna(0).astype(int)

for col in ["phone", "line_id", "skills", "resources", "transport", "note", "photo"]:
    if col in df.columns:
        df[col] = df[col].fillna("").astype(str)
        
# === 志工基本資料填寫頁 ===
if st.session_state.get("page") == "signup":
    st.title("志工基本資料填寫")

    name = st.text_input("姓名（必填）")
    phone = st.text_input("電話（必填）")
    line_id = st.text_input("LINE ID（選填）")

    if st.button("送出報名"):
        if not name or not phone:
            st.warning("⚠ 請完整填寫姓名與電話")
            st.stop()

        st.session_state["current_volunteer_name"] = name
        st.session_state["current_volunteer_phone"] = phone
        st.session_state["current_volunteer_line"] = line_id
        st.session_state["page"] = "task_list"
        st.rerun()

    st.stop()
    
# -----------------------------------
# 前端 UI
# -----------------------------------
st.title("災後人力媒合平台（熱心民眾端）")
st.caption("以下為受災戶上傳的最新需求")

keyword = st.text_input("搜尋（地址、能力、備註、提供資源）")
filtered = missions.copy()

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

if "selected_task_id" not in st.session_state:
    st.session_state.selected_task_id = None

vol_phone = st.session_state.get("current_volunteer_phone", "")

for idx, row in filtered.iterrows():
    left, right = st.columns([2, 1])

    with left:
        st.markdown(f"**🕒 工作時間：** {row['work_time']}")
        current_count = len(volunteers[volunteers["id_number"] == row["id_number"]])
        st.markdown(f"**👥 需求人數：** {current_count} / {row['demand_worker']}")

        # 顯示已報名志工名單
        vols = volunteers[volunteers["id_number"] == row["id_number"]]
        if not vols.empty:
            st.write("👥 已報名志工：")
            for _, vol in vols.iterrows():
                masked_phone = vol["phone"][:4] + "****"
                st.write(f"- {vol['name']}（{masked_phone}）")

        st.markdown(f"**📝 備註：** {row['note']}")

        already_joined = len(volunteers[
            (volunteers["phone"] == vol_phone) &
            (volunteers["id_number"] == row["id_number"])
        ]) > 0

        if current_count >= row["demand_worker"]:
            st.error("❌ 此任務人數已足夠")
        elif already_joined:
            st.success("✔ 你已報名此任務")
        else:
            if st.button("我要報名", key=f"apply_{row['id_number']}"):
                st.session_state["page"] = "signup"
                st.session_state["selected_task_id"] = row["id_number"]
                st.rerun()

    with right:
        photo_url = str(row.get("photo", "")).strip()
        if photo_url.startswith("http"):
            st.image(photo_url, use_column_width=True)
        else:
            st.info("尚無照片")

    st.markdown("---")

# 使用者填完資料回到任務頁 → 寫入 Google Sheet
if st.session_state.get("page") == "task_list" and st.session_state.get("selected_task_id"):
    task_id = st.session_state["selected_task_id"]
    name = st.session_state.get("current_volunteer_name")
    phone = st.session_state.get("current_volunteer_phone")
    line_id = st.session_state.get("current_volunteer_line")

    new_row = ["volunteer", task_id, name, phone, line_id]
    while len(new_row) < len(df.columns):
        new_row.append("")

    sheet.append_row(new_row)

    st.success("🎉 報名成功！")
    st.session_state["selected_task_id"] = None
    st.rerun()

