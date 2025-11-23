import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

st.title("Streamlit Cloud × Google Sheets")

# 設定 Google Sheets 權限
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# 從 Secret 讀取 Google 金鑰
creds = Credentials.from_service_account_info(
    st.secrets["google"], 
    scopes=SCOPE
)

# 授權 Google Sheets
client = gspread.authorize(creds)

# 打開 Google Sheet（使用 Sheet ID，更穩定）
sheet_id = "1PbYajOLCW3p5vsxs958v-eCPgHC1_DnHf9G_mcFx9C0"  # 從網址取得
sheet = client.open_by_key(sheet_id).sheet1  # ← 修正這裡

# 建立表單
name = st.text_input("請輸入您的姓名（與註冊基本資料表單時相同）")
phone = st.text_input("請輸入您的電話（與註冊基本資料表單時相同）")

if st.button("確認身分"):
    # 檢查姓名與電話是否存在
    matched_user = users[(users["姓名"] == name) & (users["電話"] == phone)]
    if len(matched_user) == 0:
        st.error("查無此使用者，請先到基本資料表單註冊。")
    else:
        st.success("身分驗證成功，請填寫您的需求。")
if st.button("送出"):
    sheet.append_row([name, ])
    st.success("成功寫入 Google Sheets！")

# 讀取資料並顯示
data = sheet.get_all_records()
df = pd.DataFrame(data)
st.dataframe(df)
