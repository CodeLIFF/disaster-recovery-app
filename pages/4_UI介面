import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="災後人力媒合平台", layout="wide")

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

data = sheet.get_all_records()
df = pd.DataFrame(data)

# ---------------- 頁面標題 ----------------
st.title("災後人力媒合平台（志工端）")
st.caption("以下為目前所有受災戶上傳的需求")

# ---------------- 篩選區 ----------------
col1, col2 = st.columns(2)

keyword = col1.text_input("搜尋地址 / 備註 / 提供資源 / 能力需求")
status = col2.selectbox("篩選名額狀態", ["全部", "未滿", "已滿"])

filtered = df.copy()

# 搜尋邏輯
if keyword:
    filtered = filtered[
        filtered["address"].str.contains(keyword, case=False) |
        filtered["note"].str.contains(keyword, case=False) |
        filtered["resources"].str.contains(keyword, case=False) |
        filtered["skills"].str.contains(keyword, case=False)
    ]

# 名額篩選
if status == "未滿":
    filtered = filtered[filtered["selected_people"] < filtered["need_people"]]
elif status == "已滿":
    filtered = filtered[filtered["selected_people"] >= filtered["need_people"]]

st.markdown("---")
st.write(f"共 {len(filtered)} 筆需求")

# ---------------- 卡片列表（重要 UI） ----------------
for idx, row in filtered.iterrows():

    left, right = st.columns([2, 1])

    # 左邊（資訊）
    with left:
        st.markdown(f"## 📍 {row['address']}")
        st.markdown(f"**🕒 工作時間：** {row['work_time']}")
        st.markdown(f"**👥 人數需求：** {row['selected_people']} / {row['need_people']}")
        st.markdown(f"**🧰 提供資源：** {row['resources']}")
        st.markdown(f"**💪 能力需求：** {row['skills']}")
        st.markdown(f"**🚗 建議交通方式：** {row['transport']}")
        st.markdown(f"**📝 備註：** {row['note']}")

        st.link_button("我要報名", "https://forms.gle/你的報名表單網址")

    # 右邊（照片）
    with right:
        if row["photo_url"]:
            st.image(row["photo_url"], use_column_width=True)
        else:
            st.info("尚未提供照片")

    st.markdown("---")
