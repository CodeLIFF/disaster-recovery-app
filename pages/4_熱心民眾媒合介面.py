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

data = sheet.get_all_records()
df = pd.DataFrame(data)

# 清理欄位（避免空白、大小寫問題）
df.columns = df.columns.str.strip()

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

    # 右邊照片
    with right:
        if row["photo"]:
            st.image(row["photo"], use_column_width=True)
        else:
            st.info("尚無照片")

    st.markdown("---")

