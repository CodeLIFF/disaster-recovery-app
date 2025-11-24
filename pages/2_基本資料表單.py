import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ---------- Google Sheet 連線 ----------
creds = Credentials.from_service_account_info(
    st.secrets["google_sheet"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ],
)
gc = gspread.authorize(creds)

SHEET_ID = "1PbYajOLCW3p5vsxs958v-eCPgHC1_DnHf9G_mcFx9C0"
ws = gc.open_by_key(SHEET_ID).worksheet("vol")  # tab 名稱是 vol


# ---------- 小工具：取得下一個 id_number ----------
def get_next_id_number():
    # 讀取第 1 欄（id_number），跳過標題列
    col = ws.col_values(1)[1:]   # col[0] 是標題 id_number
    nums = []
    for v in col:
        v = str(v).strip()
        if v.isdigit():
            nums.append(int(v))
    return (max(nums) + 1) if nums else 1


# ---------- 小工具：查重（同 role + name + phone 視為重複） ----------
def is_duplicate(role, name, phone):
    data = ws.get_all_records()
    if not data:
        return False
    df = pd.DataFrame(data)
    mask = (df["role"] == role) & (df["name"] == name) & (df["phone"] == phone)
    return mask.any()


# ---------- Streamlit 表單本體 ----------
st.title("基本資料表單（志工 / 受災戶）")

role_display = st.selectbox("身分 role", ["志工 volunteer", "受災戶 victim"])
role = "volunteer" if "志工" in role_display else "victim"

name = st.text_input("姓名 name")
phone = st.text_input("電話 phone number")
line_id = st.text_input("Line ID")

if phone and (not phone.isdigit() or len(phone) != 10):
    st.warning("電話格式應為 10 位數字")

if role == "victim":
    st.caption("＊請先填這一張，受災需求細節會在下一張「受災需求表單」填寫。")
else:
    st.caption("＊請先填這一張，受災需求細節會在媒合介面呈現。")
if st.button("送出基本資料 submit"):
    if not phone.isdigit() or len(phone) != 10:
        st.error("❌ 電話格式應為 10 位數字，請修正後再送出。")
    
    elif not name or not phone:
        st.error("❌ 姓名與電話為必填欄位")
    else:
        if is_duplicate(role, name, phone):
            st.warning("⚠ 已有相同身分＋姓名＋電話的紀錄，請不要重複填寫。")
        else:
            id_number = get_next_id_number()
            row = [
                id_number,  # id_number
                role,       # role
                name,       # name
                phone,      # phone
                line_id,    # line_id
                "",         # mission_name
                "",         # address
                "",         # work_time
                "",         # demand_worker
                0,          # selected_worker（⚠ 這裡改成 0）
                "",         # accepted_volunteers（⚠ 新欄位）
                "",         # resources
                "",         # skills
                "",         # photo
                "",         # transport
                "",         # note
            ]

            

            try:
                ws.append_row(row)

                st.session_state["current_volunteer_id"] = id_number
                st.session_state["current_volunteer_name"] = name
                st.session_state["current_volunteer_phone"] = phone
                st.session_state["current_volunteer_line"] = line_id

                st.success("✅ 已成功送出基本資料！")

                if role == "victim":
                    st.info("請接著前往「受災需求表單」頁面填寫詳細需求。")
                else:
                    st.info("請接著前往「民眾媒合介面」頁面選擇任務。")

            except Exception as e:
                st.error("❌ 填寫失敗，請稍後再試。")
                st.error(str(e))
