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

# 清欄位空白
df.columns = df.columns.str.strip()

# 修正欄位名（你的表格 id 是 id_number）
if "id_number" in df.columns:
    df["id_number"] = pd.to_numeric(df["id_number"], errors="coerce").fillna(0).astype(int)

df["selected_worker"] = pd.to_numeric(df["selected_worker"], errors="coerce").fillna(0).astype(int)
df["demand_worker"] = pd.to_numeric(df["demand_worker"], errors="coerce").fillna(0).astype(int)

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
# 更新 Google Sheet 函式
# -----------------------------------
def update_sheet(updated_df):
    sheet.clear()
    sheet.update([updated_df.columns.values.tolist()] + updated_df.values.tolist())

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

# 初始化 session state
if "accepted_task" not in st.session_state:
    st.session_state.accepted_task = None

# -----------------------------------
# 卡片列表
# -----------------------------------
for idx, row in filtered.iterrows():
    left, right = st.columns([2, 1])

    with left:
        st.markdown(f"## 📍 {row['mission_name']} — {row['address']}")
        st.markdown(f"**🕒 工作時間：** {row['work_time']}")
        st.markdown(f"**👥 需求人數：** {row['selected_worker']} / {row['demand_worker']}")
        st.markdown(f"**🧰 提供資源：** {row['resources']}")
        st.markdown(f"**💪 能力需求：** {row['skills']}")
        st.markdown(f"**🚗 交通建議：** {row['transport']}")
        st.markdown(f"**📝 備註：** {row['note']}")

        # 人數已滿
        if row["selected_worker"] >= row["demand_worker"]:
            st.error("❌ 此任務人數已足夠，無法再報名")
        else:
            # 用 id_number 當 key
            if st.button("我要報名", key=f"apply_{row['id_number']}"):
                st.session_state.accepted_task = row["id_number"]
                st.rerun()

    with right:
        if row["photo"]:
            st.image(row["photo"], use_column_width=True)
        else:
            st.info("尚無照片")

    st.markdown("---")

# -------------------------------------------------
# 接受任務後：更新 Google Sheet
# -------------------------------------------------
if st.session_state.accepted_task is not None:

    task_id = st.session_state.accepted_task

    # 找出該任務
    target_row = df[df["id_number"] == task_id].iloc[0]

    # 更新 selected_worker
    df.loc[df["id_number"] == task_id, "selected_worker"] += 1

    # 回寫 Google Sheet
    update_sheet(df)

    st.success("🎉 你已成功接取此任務！")

    st.write(f"📌 任務名稱：{target_row['mission_name']}")
    st.write(f"📍 地址：{target_row['address']}")
    st.write(f"☎️ 電話：{target_row['phone']}")
    st.write(f"LINE：{target_row['line_id']}")

    updated = df[df["id_number"] == task_id].iloc[0]
    st.write(f"🎯 更新後已選志工：{updated['selected_worker']} 人")

    # 觸發結束後重整頁面，不重複顯示
    st.session_state.accepted_task = None
    st.rerun()
