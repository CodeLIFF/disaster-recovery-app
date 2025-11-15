

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# Google API 權限
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# 載入你的 JSON 金鑰
creds = ServiceAccountCredentials.from_json_keyfile_name(
    "你的金鑰.json",   # ⚠️ 請改成你的 JSON 檔名
    SCOPE
)

client = gspread.authorize(creds)

# 打開 Google Sheet
sheet_id = "1PbYajOLCW3p5vsxs958v-eCPgHC1_DnHf9G_mcFx9C0"  # 從網址取得
sheet = gc.open_by_key(sheet_id).sheet1

st.title("Google Sheets × Streamlit 本機測試")

name = st.text_input("姓名")
age = st.number_input("年齡", min_value=0)

if st.button("送出"):
    sheet.append_row([name, age])
    st.success("成功寫入 Google Sheets！")

# 顯示所有資料
data = sheet.get_all_records()
df = pd.DataFrame(data)
st.dataframe(df)
