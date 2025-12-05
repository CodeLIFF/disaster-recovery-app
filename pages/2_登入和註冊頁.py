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
ws = gc.open_by_key(SHEET_ID).worksheet("vol")


# ---------- 工具函式 ----------
def normalize_phone(s: str) -> str:
    if s is None or s == "":
        return ""
    s = str(s).replace("'", "").strip()
    s = re.sub(r"\D", "", s)
    if len(s) == 9 and s.startswith("9"):
        s = "0" + s
    return s


def get_next_id_number():
    col = ws.col_values(1)[1:]
    nums = [int(v) for v in col if str(v).strip().isdigit()]
    return (max(nums) + 1) if nums else 1


def is_duplicate(role: str, name: str, phone: str) -> bool:
    data = ws.get_all_records()
    if not data:
        return False
    df = pd.DataFrame(data)
    df["role"] = df["role"].astype(str).str.strip().str.lower()
    df["phone"] = df["phone"].astype(str).apply(normalize_phone)
    return ((df["role"] == role.lower().strip()) &
            (df["phone"] == normalize_phone(phone))).any()


# =================================================================
#  🟦🟦🟦               登入模式 / 註冊模式                🟦🟦🟦
# =================================================================
st.title("註冊 / 登入 basic registration")

mode = st.radio("請選擇操作模式", ["註冊", "登入"])


# =================================================================
#  🟩🟩🟩                     登入系統                     🟩🟩🟩
# =================================================================
if mode == "登入":
    st.header("登入 Login")

    role_display = st.selectbox("身分 role", ["志工 volunteer", "受災戶 victim"])
    role = "volunteer" if "志工" in role_display else "victim"

    login_phone = st.text_input("請輸入註冊時的電話")

    if st.button("登入 Login"):
        phone_norm = normalize_phone(login_phone)

        data = ws.get_all_records()
        df = pd.DataFrame(data)
        df["phone"] = df["phone"].astype(str).apply(normalize_phone)
        df["role"] = df["role"].astype(str).str.strip()

        # 找所有電話相同的紀錄
        all_records = df[df["phone"] == phone_norm]

        if all_records.empty:
            st.error("❌ 查無此電話的註冊紀錄，請先完成註冊。")
            st.stop()

        # 在這些紀錄裡查詢該身分
        user_records = all_records[all_records["role"] == role]

        if user_records.empty:
            st.error(
                f"❌ 此電話尚未以「{role}」身分註冊。\n"
                f"你可以切換到『註冊模式』，用同一支電話增加新身分。"
            )
            st.stop()

        # 登入成功
        user = user_records.iloc[0]
        st.success(f"登入成功！歡迎 {user['name']}")

        # ---------------- 受災戶：顯示自己發布的任務 ----------------
        if role == "victim":
            st.subheader("您發布的任務 Your posted missions")

            my_tasks = df[df["phone"] == phone_norm]

            if my_tasks.empty:
                st.info("目前沒有您發布的任務。")
            else:
                display_df = my_tasks[
                    ["mission_name", "address", "work_time",
                     "demand_worker", "selected_worker",
                     "accepted_volunteers", "date", 
                     "name", "phone", "line_id"]
                ]
                
                display_df = display_df.rename(columns={
                    "mission_name": "任務名稱",
                    "address": "地點",
                    "work_time": "工作時間",
                    "demand_worker": "需求人數",
                    "selected_worker": "目前人數",
                    "accepted_volunteers": "已媒合志工",
                    "date": "發布日期",
                    "name": "受災戶姓名",
                    "phone": "受災戶電話",
                    "line_id": "受災戶 LineID"
                })

                st.dataframe(display_df)

        # ---------------- 志工：顯示被接受的任務 ----------------
        else:
            st.subheader("您參與的任務 Missions you joined")

            my_name = user["name"]
            last3 = phone_norm[-3:]

            pattern = rf"{re.escape(my_name)}\({last3}\)"

            df["accepted_volunteers"] = df["accepted_volunteers"].astype(str)

            joined_tasks = df[df["accepted_volunteers"].str.contains(pattern, regex=True)]

            if joined_tasks.empty:
                st.info("目前您沒有參與的任務。")
            else:
                # 1. 修正點：先將篩選結果指派給變數 display_df
                display_df = joined_tasks[
                    ["mission_name", "address", "work_time",
                     "demand_worker", "selected_worker",
                     "date", 
                     "name", "phone", "line_id"] # 在這裡加入受災戶聯絡資訊
                ]

                # 2. 修正點：現在 display_df 已經存在，可以進行 rename
                display_df = display_df.rename(columns={
                    "mission_name": "任務名稱",
                    "address": "地點",
                    "work_time": "工作時間",
                    "demand_worker": "需求人數",
                    "selected_worker": "目前人數",
                    "date": "發布日期",
                    "name": "受災戶姓名",
                    "phone": "受災戶電話",
                    "line_id": "受災戶 LineID"
                })

                # 3. 最後顯示結果
                st.dataframe(display_df)

# =================================================================
#  🟦🟦🟦             以下為原本的「註冊模式」             🟦🟦🟦
# =================================================================
else:
    role_display = st.selectbox("身分 role", ["志工 volunteer", "受災戶 victim"])
    role = "volunteer" if "志工" in role_display else "victim"

    name = st.text_input("姓名 name")
    phone = st.text_input("電話 phone number")
    line_id = st.text_input("Line ID（選填）")

    if phone:
        if len(normalize_phone(phone)) != 10:
            st.warning("電話格式請輸入 10 位數字（例如 0912345678）")

    if st.button("送出基本資料 submit"):
        phone_norm = normalize_phone(phone)

        if not name or not phone:
            st.error("❌ 姓名與電話為必填欄位")
        elif len(phone_norm) != 10:
            st.error("❌ 電話格式應為 10 位數字")
        elif is_duplicate(role, name, phone_norm):
            st.warning("❌ 此電話已註冊，請改用登入模式")
        else:
            id_number = get_next_id_number()

            row = [
                id_number,
                role,
                name.strip(),
                "'" + phone_norm,
                line_id.strip(),
                "",
                "",
                "",
                "",
                0,
                "",
                "",
                "",
                "",
                "",
                "",
            ]

            try:
                ws.append_row(row)
                st.success("✅ 註冊成功！請使用登入模式登入。")
            except Exception as e:
                st.error("❌ 填寫失敗")
                st.error(str(e))
