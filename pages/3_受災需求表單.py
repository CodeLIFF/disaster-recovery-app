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
name = st.text_input("姓名")
age = st.number_input("年齡", min_value=0)

if st.button("送出"):
    sheet.append_row([name, age])
    st.success("成功寫入 Google Sheets！")

# 讀取資料並顯示
data = sheet.get_all_records()
df = pd.DataFrame(data)
st.dataframe(df)
