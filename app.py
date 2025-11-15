import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ---------- Google Sheet 連線 ----------
# 從 Streamlit Secrets 讀取 Service Account 資訊
from google.oauth2.service_account import Credentials
creds = Credentials.from_service_account_info(
    st.secrets["google"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)

# 授權
gc = gspread.authorize(creds)

# 打開你的 Google Sheet，假設名稱為 "志工受災戶表單"
sheet = gc.open("disasterVictims").sheet1

# ---------- Streamlit 表單 ----------
st.title("志工與受災戶登記表單")

role = st.selectbox("身份", ["志工", "受災戶"])
name = st.text_input("姓名")
phone = st.text_input("電話")
line_id = st.text_input("Line ID (選填)")
extra = st.text_area("受災戶需求 / 可提供資源 (選填)")

csv_file = "local_backup.csv"  # 本地備份用，可選

if st.button("送出"):
    if name and phone:  # 必填驗證
        # 1️⃣ 新增資料
        new_data = pd.DataFrame([[role, name, phone, line_id, extra]],
                                columns=["身份", "姓名", "電話", "Line ID", "需求/資源"])
        
        # 2️⃣ 寫入 Google Sheet
        sheet.append_row([role, name, phone, line_id, extra])
        
        # 3️⃣ 本地備份 CSV（可選）
        import os
        if os.path.exists(csv_file):
            new_data.to_csv(csv_file, mode='a', index=False, header=False, encoding='utf-8-sig')
        else:
            new_data.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        st.success(f"✅ 已收到資料：{role} - {name}")
    else:
        st.error("請填寫姓名與電話")
