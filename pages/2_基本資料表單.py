import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ---------- Google Sheet 連線 ----------
creds = Credentials.from_service_account_info(
    st.secrets["google"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)
gc = gspread.authorize(creds)

sheet_id = "1PbYajOLCW3p5vsxs958v-eCPgHC1_DnHf9G_mcFx9C0"
ws = gc.open_by_key(sheet_id).worksheet("vol")   # ← 用你給的 tab 名稱


# ---------- 欄位定義（固定順序） ----------
columns = [
    "identity",
    "role",
    "name",
    "phone",
    "line_id",
    "address",
    "work_time",
    "need_people",
    "selected_people",
    "resources"
]


# ---------- Streamlit 表單 ----------
st.title("志工 / 受災戶 登記表單")

identity = st.selectbox("身份", ["victim", "volunteer"])
name = st.text_input("姓名")
phone = st.text_input("電話")
line_id = st.text_input("LINE ID (選填)")

# 依身份顯示不同欄位
address = ""
work_time = ""
need_people = ""
resources = ""

if identity == "victim":
    address = st.text_input("受災地址（必填）")
    need_people = st.number_input("需要人力數量", min_value=1, step=1)
    resources = st.text_area("需要的資源（例如：食物、飲用水、藥品等）")

elif identity == "volunteer":
    address = st.text_input("服務地點（可選填）")
    work_time = st.text_input("可提供服務時段（例如：09:00-17:00）")


# ---------- 查重 （姓名 + 電話） ----------
def is_duplicate(name, phone):
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    if df.empty:
        return False
    return ((df["name"] == name) & (df["phone"] == phone)).any()


# ---------- 儲存按鈕 ----------
if st.button("送出"):
    if not name or not phone:
        st.error("❌ 姓名與電話為必填欄位")
        st.stop()

    # victim 必填地址
    if identity == "victim" and not address:
        st.error("❌ 受災戶必填：地址")
        st.stop()

    if is_duplicate(name, phone):
        st.warning("⚠ 資料重複！相同姓名+電話已存在。")
        st.stop()

    # 自動組成 row（確保所有欄位齊全）
    row = [
        identity,
        identity,     # role 與 identity 一樣
        name,
        phone,
        line_id,
        address,
        work_time,
        need_people,
        0,            # selected_people 初始為 0
        resources
    ]

    try:
        ws.append_row(row)
        st.success("✅ 已成功送出！")
    except Exception as e:
        st.error("❌ Google Sheet 寫入失敗")
        st.error(str(e))
