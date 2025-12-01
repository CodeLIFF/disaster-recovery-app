import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re

# ---------- Google Sheet 連線 ----------
creds = Credentials.from_service_account_info(
    st.secrets["google"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ],
)
gc = gspread.authorize(creds)

SHEET_ID = "1PbYajOLCW3p5vsxs958v-eCPgHC1_DnHf9G_mcFx9C0"
ws = gc.open_by_key(SHEET_ID).worksheet("vol")  # tab 名稱是 vol


# ---------- 工具函式：電話標準化 ----------
def normalize_phone(s: str) -> str:
    """
    統一電話格式：
    - 移除單引號 (Google Sheets 的文字前綴)
    - 去掉空白、破折號等非數字字元
    - 9 碼且 9 開頭則補 0
    - 回傳標準 10 碼電話號碼
    """
    if s is None or s == "":
        return ""
    
    # 移除單引號 (Google Sheets 的文字格式前綴)
    s = str(s).replace("'", "").strip()
    
    # 只保留數字
    s = re.sub(r"\D", "", s)
    
    # 若長度 9 且 9 開頭，補 0
    if len(s) == 9 and s.startswith("9"):
        s = "0" + s
    
    return s

# ---------- 取得下一個 id_number ----------
def get_next_id_number():
    col = ws.col_values(1)[1:]  # 跳過標題列
    nums = []
    for v in col:
        v = str(v).strip()
        if v.isdigit():
            nums.append(int(v))
    return (max(nums) + 1) if nums else 1


# ---------- 查重（同 role + name + phone 視為同一人） ----------
def is_duplicate(role: str, name: str, phone: str) -> bool:
    data = ws.get_all_records()
    if not data:
        return False

    df = pd.DataFrame(data)

    # 統一格式：全部轉成字串＋strip
    df["role"] = df["role"].astype(str).str.strip().str.lower()
    df["name"] = df["name"].astype(str).str.strip()
    df["phone"] = df["phone"].astype(str).apply(normalize_phone)

    role_norm = role.strip().lower()
    name_norm = name.strip()
    phone_norm = normalize_phone(phone)

    mask = (
        (df["role"] == role_norm)
        & (df["name"] == name_norm)
        & (df["phone"] == phone_norm)
    )
    return mask.any()


# ---------- Streamlit 表單本體 ----------
st.title("註冊 / 登入 basic registration")

role_display = st.selectbox("身分 role", ["志工 volunteer", "受災戶 victim"])
role = "volunteer" if "志工" in role_display else "victim"

name = st.text_input("姓名 name")
phone = st.text_input("電話 phone number")
line_id = st.text_input("Line ID（選填）")

# 即時檢查電話格式
if phone:
    phone_norm = normalize_phone(phone)
    if len(phone_norm) != 10:
        st.warning("電話格式請輸入 10 位數字（例如 0912345678）")

if role == "victim":
    st.caption("＊請先填這一張，受災需求細節會在下一張「受災需求表單」填寫。")
else:
    st.caption("＊請先填這一張，志工媒合會依此資料進行。")

if st.button("送出基本資料 submit"):
    phone_norm = normalize_phone(phone)

    # 1️⃣ 必填檢查
    if not name or not phone:
        st.error("❌ 姓名與電話為必填欄位")
    elif len(phone_norm) != 10:
        st.error("❌ 電話格式應為 10 位數字，請修正後再送出。")
    else:
        # 2️⃣ 查重：同 role + name + phone 已存在就擋掉
        if is_duplicate(role, name, phone_norm):
            st.warning("⚠ 已有相同身分＋姓名＋電話的紀錄，請不要重複註冊。")
        else:
            # 3️⃣ 新增一個 id_number
            id_number = get_next_id_number()

            row = [
                id_number,        # id_number
                role,             # role
                name.strip(),     # name
                phone_norm,       # phone（用標準化後的）
                line_id.strip(),  # line_id
                "",               # mission_name
                "",               # address
                "",               # work_time
                "",               # demand_worker
                0,                # selected_worker
                "",               # accepted_volunteers
                "",               # resources
                "",               # skills
                "",               # photo
                "",               # transport
                "",               # note
            ]

            try:
                ws.append_row(row)

                # 存進 session_state 讓其他頁面可以用
                st.session_state["current_volunteer_id"] = id_number
                st.session_state["current_volunteer_name"] = name.strip()
                st.session_state["current_volunteer_phone"] = phone_norm
                st.session_state["current_volunteer_line"] = line_id.strip()

                st.success("✅ 已成功送出基本資料！")

                if role == "victim":
                    st.info("請接著前往「受災需求表單」頁面填寫今日需求。")
                else:
                    st.info("請接著前往「民眾媒合介面」頁面選擇任務。")

            except Exception as e:
                st.error("❌ 填寫失敗，請稍後再試。")
                st.error(str(e))
