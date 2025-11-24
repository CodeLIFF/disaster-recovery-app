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

# 讀取資料
data = sheet.get_all_records()
df = pd.DataFrame(data)

# 清理欄位（避免空白、大小寫問題）
df.columns = df.columns.str.strip()

# 型別轉換 新加
df["selected_worker"] = pd.to_numeric(df["selected_worker"], errors="coerce").fillna(0).astype(int)
df["demand_worker"] = pd.to_numeric(df["demand_worker"], errors="coerce").fillna(0).astype(int)
df["id"] = pd.to_numeric(df["id"], errors="coerce").astype(int)

required_cols = ["mission_name", "address", "work_time", "demand_worker"]

df = df.dropna(subset=required_cols)  # 去掉 NA
df = df[
    (df["mission_name"] != "") &
    (df["address"] != "") &
    (df["work_time"] != "") &
    (df["demand_worker"] != "")
]

# ---------------- 更新 Google Sheet 函式 ----------------新加
def update_sheet(updated_df):
    sheet.clear()
    sheet.update([updated_df.columns.values.tolist()] + updated_df.values.tolist())


# ---------------- UI ----------------
st.title("災後人力媒合平台（志工端）")
st.caption("以下為受災戶上傳的最新需求")

keyword = st.text_input("搜尋（地址、能力、備註、提供資源）")

filtered = df.copy()

# 搜尋邏輯
if keyword:
    filtered = filtered[
        filtered["address"].str.contains(keyword, case=False) |
        filtered["skills"].str.contains(keyword, case=False) |
        filtered["resources"].str.contains(keyword, case=False) |
        filtered["note"].str.contains(keyword, case=False)
    ]

st.write(f"共 {len(filtered)} 筆需求")
st.markdown("---")

# 初始化 session_state 新加
if "accepted_task" not in st.session_state:
    st.session_state.accepted_task = None

# ---------------- 卡片列表 ----------------
for idx, row in filtered.iterrows():
    left, right = st.columns([2, 1])

    # 左邊資訊文字
    with left:
        st.markdown(f"## 📍 {row['address']}")
        st.markdown(f"**🕒 工作時間：** {row['work_time']}")
        st.markdown(f"**👥 需求人數：** {row['selected_worker']} / {row['demand_worker']}")
        st.markdown(f"**🧰 提供資源：** {row['resources']}")
        st.markdown(f"**💪 能力需求：** {row['skills']}")
        st.markdown(f"**🚗 交通建議：** {row['transport']}")
        st.markdown(f"**📝 備註：** {row['note']}")

        st.link_button("我要報名", "https://forms.gle/your-form-url")
        # 判斷是否還能報名 新加
        if row["selected_worker"] >= row["demand_worker"]:
            st.error("❌ 此任務人數已足夠，無法再報名")
        else:
            if st.button("我要報名", key=f"apply_{row['id']}"):
                st.session_state.accepted_task = row["id"]
                st.rerun()


    # 右邊照片
    with right:
        if row["photo"]:
            st.image(row["photo"], use_column_width=True)
        else:
            st.info("尚無照片")

    st.markdown("---")
# =============================
# 顯示接取結果 + 更新資料
# =============================
if st.session_state.accepted_task is not None:

    task_id = st.session_state.accepted_task

    task = df[df["id"] == task_id].iloc[0]

    # 更新數量
    df.loc[df["id"] == task_id, "selected_worker"] += 1

    # 回寫 Google Sheet
    update_sheet(df)

    st.success("🎉 你已成功接取此任務！")
    st.info(f"📞 受災戶聯絡資訊：{task['contact']}")

    updated = df[df["id"] == task_id].iloc[0]
    st.write(f"🎯 更新後已選志工：{updated['selected_worker']} 人")

    # 清除狀態避免重複顯示
    st.session_state.accepted_task = None
