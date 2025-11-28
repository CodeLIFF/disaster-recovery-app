import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from supabase import create_client, Client


# ---------- Google Service Account：一組搞定 ----------
creds = Credentials.from_service_account_info(
    st.secrets["google"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ],
)

# Google Sheet
gc = gspread.authorize(creds)
SHEET_ID = "1PbYajOLCW3p5vsxs958v-eCPgHC1_DnHf9G_mcFx9C0"
ws = gc.open_by_key(SHEET_ID).worksheet("vol")


supabase_url = "https://zktsrpccikfnsqkpuxcc.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InprdHNycGNjaWtmbnNxa3B1eGNjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQyNDM1NTAsImV4cCI6MjA3OTgxOTU1MH0.x0h5R5KfmzfCZ8WALDAeEPU36WGgE0Ri-N1JGY6VCcM"
supabase_bucket = "photos"
supabase: Client = create_client(supabase_url, supabase_key)




def upload_photo_to_supabase(uploaded_file):
    if uploaded_file is None:
        return None
        
    row_number, row_series = find_victim_row(name, phone)
    user_id = row_series.get("id_number")  

    file_ext = uploaded_file.name.split('.')[-1]
    filename = f"{user_id}.{file_ext}"
    file_bytes = uploaded_file.getvalue()

    try:
        # 上傳到 Supabase bucket
        supabase.storage.from_(supabase_bucket).upload(
            path=filename,
            file=file_bytes,
            file_options={
                "content-type": uploaded_file.type
                   
            }
        )
    except Exception as e:
        st.error("Supabase 上傳失敗")
        st.error(str(e))
        return None

    # 取得公開 URL（前提：你的 bucket 要設成 public）
    url = supabase.storage.from_(supabase_bucket).get_public_url(filename)
    return url




SHEET_ID = "1PbYajOLCW3p5vsxs958v-eCPgHC1_DnHf9G_mcFx9C0"
ws = gc.open_by_key(SHEET_ID).worksheet("vol")  # 工作表名稱：vol

# 可變動的災區關鍵字（之後你們只要改這一行即可）
ALLOWED_REGION = "花蓮縣"

# ---------- session_state：記錄驗證狀態 ----------
if "victim_verified" not in st.session_state:
    st.session_state["victim_verified"] = False
    st.session_state["victim_row_number"] = None

if "address_verified" not in st.session_state:
    st.session_state["address_verified"] = False
    st.session_state["address_value"] = ""

if "victim_prev_data" not in st.session_state:
    st.session_state["victim_prev_data"] = {}

# ---------- 小工具：讀取資料 ----------
def load_df():
    data = ws.get_all_records()
    return pd.DataFrame(data) if data else pd.DataFrame()

# 一般文字清洗：處理全形空白、前後空格
def normalize_text(text):
    if pd.isna(text):
        return ""
    return str(text).replace("　", " ").strip()

# 電話清洗：只保留數字，並拿掉開頭的 0
def normalize_phone(text):
    if pd.isna(text):
        return ""
    digits = re.sub(r"\D", "", str(text))
    return digits.lstrip("0")

# 專門找「受災戶」那一列
def find_victim_row(name, phone):
    df = load_df()
    if df.empty:
        return None, None

    df["role"] = df["role"].apply(normalize_text)
    df["name"] = df["name"].apply(normalize_text)
    df["phone_norm"] = df["phone"].apply(normalize_phone)

    name_norm = normalize_text(name)
    phone_norm = normalize_phone(phone)

    mask = (
        (df["role"] == "victim")
        & (df["name"] == name_norm)
        & (df["phone_norm"] == phone_norm)
    )

    if not mask.any():
        return None, None

    idx = df.index[mask][0]
    row_number = idx + 2  # DataFrame index 0 -> Google Sheet 第 2 列
    return row_number, df.loc[idx]

# ---------- 驗證 address 是否在指定縣市，且不含英文字母 ----------
def validate_address(address: str, allowed_region: str):
    address = address.strip()
    if not address:
        return "❌ 地址（address）為必填"

    if allowed_region not in address:
        return f"❌ 目前僅限災區（{allowed_region}），系統判定此地址不在災區內。"

    if re.search(r"[A-Za-z]", address):
        return "❌ 地址請以中文與數字為主，請不要包含英文字母"

    return None

# ---------- 受災需求表單 ----------
st.title("受災戶需求表單")
st.write("請依步驟完成：先驗證身分 → 再驗證地址 → 通過後填寫／更新詳細需求。")

# ================== 第一步：驗證基本資料 ================== #
st.subheader("① 🧍‍♀️ 身分驗證 identity verification")

name = st.text_input("👤 姓名 name（需與「基本資料表單」一致）", key="victim_name")
phone = st.text_input("📞 電話 phone number（需與「基本資料表單」一致）", key="victim_phone")

if st.button("🔍 驗證基本資料 verify"):
    if not name or not phone:
        st.error("❌ 姓名與電話為必填，且需與「基本資料表單」一致")
        st.session_state["victim_verified"] = False
        st.session_state["victim_row_number"] = None
        st.session_state["victim_prev_data"] = {}
    else:
        row_number, row_series = find_victim_row(name, phone)
        if row_number is None:
            st.error("❌ 找不到您的基本資料。")
            st.info("請先在「基本資料表單」選擇『受災戶 victim』並填寫，或確認姓名、電話是否輸入正確。")
            st.session_state["victim_verified"] = False
            st.session_state["victim_row_number"] = None
            st.session_state["victim_prev_data"] = {}
        else:
            st.success(f"✅ 已成功確認您的基本資料！")
            st.session_state["victim_verified"] = True
            st.session_state["victim_row_number"] = row_number
            st.session_state["victim_prev_data"] = row_series.to_dict()

            # 如果 sheet 裡原本已有地址，就幫忙帶入當作預設值
            prev_addr = normalize_text(row_series.get("address", ""))
            if prev_addr and not st.session_state.get("address_value"):
                st.session_state["address_value"] = prev_addr

# 尚未通過驗證就先停在這一步
if not st.session_state["victim_verified"]:
    st.stop()

st.markdown("---")

# ================== 第二步：地址驗證 ================== #
st.subheader("② 📍 地址驗證 address verification")

address_input = st.text_input(
    "🏠 通訊 / 受災地址（address，必填）",
    value=st.session_state.get("address_value", ""),
    placeholder=f"請填寫完整地址，例如：{ALLOWED_REGION}○○鄉○○村○○路○號",
    help=f"目前僅限災區：{ALLOWED_REGION}，地址需包含此縣市名稱。",
)

if st.button("📍 驗證地址 verify"):
    err = validate_address(address_input, ALLOWED_REGION)
    if err:
        st.error(err)
        st.session_state["address_verified"] = False
    else:
        st.success("✅ 地址驗證通過！")
        st.session_state["address_verified"] = True
        st.session_state["address_value"] = address_input.strip()

if not st.session_state["address_verified"]:
    st.stop()

st.markdown("---")

# ================== 取得上一筆資料，準備當作預設值 ================== #
prev = st.session_state.get("victim_prev_data", {}) or {}

# ----- work_time 預設 -----
prev_work = str(prev.get("work_time", "") or "")
prev_work_codes = [w.strip() for w in prev_work.split(",") if w.strip()]

# ----- demand_worker 預設 -----
try:
    prev_demand = int(prev.get("demand_worker", 1))
    if prev_demand < 1 or prev_demand > 20:
        prev_demand = 1
except Exception:
    prev_demand = 1

# ----- resources 預設 -----
prev_resources = str(prev.get("resources", "") or "")
res_tokens = [t.strip() for t in prev_resources.split(",") if t.strip()]
res_tokens_set = set(res_tokens)
res_other_text_default = ""
for t in res_tokens:
    if t.lower().startswith("other:"):
        res_other_text_default = t.split(":", 1)[1].strip()

# ----- skills 預設 -----
prev_skills = str(prev.get("skills", "") or "")
sk_tokens = [t.strip() for t in prev_skills.split(",") if t.strip()]
sk_tokens_set = set(sk_tokens)
sk_other_text_default = ""
for t in sk_tokens:
    if t.lower().startswith("other:"):
        sk_other_text_default = t.split(":", 1)[1].strip()

# ----- transport 預設 -----
prev_transport = str(prev.get("transport", "") or "")
tr_tokens = [t.strip() for t in prev_transport.split(",") if t.strip()]
tr_tokens_set = set(tr_tokens)
tr_other_text_default = ""
for t in tr_tokens:
    if t.lower().startswith("other:"):
        tr_other_text_default = t.split(":", 1)[1].strip()

# ----- mission_name / photo / note 預設 -----
prev_mission = normalize_text(prev.get("mission_name", ""))

prev_photo = prev.get("photo", "")

prev_note = str(prev.get("note", "") or "")

# ================== 第三步：填寫／更新詳細需求 ================== #
st.subheader("③ 📋 填寫／更新今日的受災需求")

# 任務名稱：可留白，預設用昨天的任務名稱（或用地址）
st.markdown("#### 📝 任務名稱 task name（可留白）")

mission_name = st.text_input(
    "任務名稱 task name",        # 這個 label 不會顯示出來，因為我們把它 collapse 掉了
    value=prev_mission,
    placeholder="可填大致地點與主要需求，例如：花蓮縣某某里住家清理",
    help="若留白，系統會自動以地址當作任務名稱。",
    label_visibility="collapsed",  # 🔑 這行讓 label 和那條空白都消失
)

# 工作時間：多選（預設為上一筆設定）
st.markdown("#### ⏰ 需要協助的時間 available time（必填，可複選）")
time_options = {
    "🌅 早上 (08:00–11:00)": "morning",
    "🌞 中午 (11:00–13:00)": "noon",
    "🌇 下午 (13:00–17:00)": "afternoon",
    "🌃 晚上 (17:00–19:00)": "night",
}
default_time_labels = [
    label for label, code in time_options.items() if code in prev_work_codes
]
selected_time_labels = st.multiselect(
    "請選擇需要協助的時段：",
    list(time_options.keys()),
    default=default_time_labels,
)
selected_time_codes = [time_options[label] for label in selected_time_labels]

# 人力需求：標題 + 數字輸入
st.markdown("#### 👥 總人數需求 required number of people（必填，上限 20人）")

demand_worker = st.number_input(
    "總人數需求 required number of people",
    min_value=1,
    max_value=20,
    step=1,
    value=prev_demand,
    label_visibility="collapsed",  # 🔑 不顯示內建 label，只留下上面的 #### 標題
)

# ====== 地點照片：顯示舊照片 + 上傳新照片 ======
st.markdown("#### 📸 地點當前照片 photo（必填）")

if prev_photo:
    st.caption("目前記錄中的照片：")
    st.image(prev_photo, width=300)
    st.caption("若現況與照片差異不大，可以不用重新上傳；若有明顯變化，請重新上傳新的照片。")

uploaded_photo = st.file_uploader(
    "請上傳目前現場照片（支援 .jpg / .jpeg / .png）",
    type=["jpg", "jpeg", "png"],
)

st.markdown("---")

# 提供資源 resources：多選 + 其他（預設上一筆）
st.markdown("#### 📦 可提供的資源 available resources（必填，可複選）")
res_tool = st.checkbox("🛠 工具 tools", value=("tool" in res_tokens_set))
res_food = st.checkbox("🍱 食物 food", value=("food" in res_tokens_set))
res_water = st.checkbox("🚰 水 water", value=("water" in res_tokens_set))
res_med = st.checkbox("💊 醫療用品 medical supplies", value=("medical supplies" in res_tokens_set))
res_hygiene = st.checkbox("🧻 衛生用品 hygiene supplies", value=("hygiene supplies" in res_tokens_set))
res_accommodation = st.checkbox("🏠 住宿 accommodation", value=("accommodation" in res_tokens_set))
res_other = st.checkbox("➕ 其他 other resources", value=bool(res_other_text_default))

res_other_text = st.text_input(
    "請說明其他資源",
    key="res_other_text",
    value=res_other_text_default if res_other else "",
)

# 能力需求 skills：多選 + 其他（預設上一筆）
st.markdown("#### 💪 希望志工具備的能力 desired skills（必填，可複選）")
sk_supplies = st.checkbox("📦 物資發放 supplies distribution", value=("supplies distribution" in sk_tokens_set))
sk_cleaning = st.checkbox("🧹 清掃 cleaning", value=("cleaning" in sk_tokens_set))
sk_medical = st.checkbox("🩺 醫療 medical", value=("medical" in sk_tokens_set))
sk_lifting = st.checkbox("🏋️ 搬運 heavy lifting", value=("heavy lifting" in sk_tokens_set))
sk_license = st.checkbox("🚗 駕照 driver's license", value=("driver's license" in sk_tokens_set))
sk_other = st.checkbox("✨ 其他 other skills", value=bool(sk_other_text_default))

sk_other_text = st.text_input(
    "請說明其他能力需求",
    key="sk_other_text",
    value=sk_other_text_default if sk_other else "",
)

# 建議交通方式 transport：多選 + 其他（預設上一筆）
st.markdown("#### 🚗 建議交通方式 suggested transportation（必填，可複選）")
tr_train = st.checkbox("🚆 火車 train", value=("train" in tr_tokens_set))
tr_bus = st.checkbox("🚌 巴士 bus", value=("bus" in tr_tokens_set))
tr_walk = st.checkbox("🚶‍♀️ 步行 on foot", value=("walk" in tr_tokens_set))
tr_car = st.checkbox("🚗 開車 car", value=("car" in tr_tokens_set))
tr_scooter = st.checkbox("🛵 機車 scooter", value=("scooter" in tr_tokens_set))
tr_bike = st.checkbox("🚲 腳踏車 bike", value=("bike" in tr_tokens_set))
tr_other = st.checkbox("➕ 其他 other transportation", value=bool(tr_other_text_default))

tr_other_text = st.text_input(
    "請說明其他交通方式",
    key="tr_other_text",
    value=tr_other_text_default if tr_other else "",
)

# 備註：預設上一筆
note = st.text_area("💬 備註 / 想說的話 notes（可選填）", value=prev_note)

# ---------- 把 checkbox 狀態組回字串 ----------
def build_resources_string():
    items = []
    if res_tool:
        items.append("tool")
    if res_food:
        items.append("food")
    if res_water:
        items.append("water")
    if res_med:
        items.append("medical supplies")
    if res_hygiene:
        items.append("hygiene supplies")
    if res_accommodation:
        items.append("accommodation")
    if res_other and res_other_text.strip():
        items.append(f"other: {res_other_text.strip()}")
    return items

def build_skills_string():
    items = []
    if sk_supplies:
        items.append("supplies distribution")
    if sk_cleaning:
        items.append("cleaning")
    if sk_medical:
        items.append("medical")
    if sk_lifting:
        items.append("heavy lifting")
    if sk_license:
        items.append("driver's license")
    if sk_other and sk_other_text.strip():
        items.append(f"other: {sk_other_text.strip()}")
    return items

def build_transport_string():
    items = []
    if tr_train:
        items.append("train")
    if tr_bus:
        items.append("bus")
    if tr_walk:
        items.append("walk")
    if tr_car:
        items.append("car")
    if tr_scooter:
        items.append("scooter")
    if tr_bike:
        items.append("bike")
    if tr_other and tr_other_text.strip():
        items.append(f"other: {tr_other_text.strip()}")
    return items

# ================== 送出，寫回同一列 ================== #
if st.button("✅ 送出今日受災需求 submit"):
    if not st.session_state.get("victim_verified", False):
        st.error("❌ 請先完成『身分驗證』。")
        st.stop()
    if not st.session_state.get("address_verified", False):
        st.error("❌ 請先完成『地址驗證』。")
        st.stop()

    row_number, row_series = find_victim_row(name, phone)
    if row_number is None:
        st.error("❌ 找不到您的基本資料。請重新確認。")
        st.stop()

    if not selected_time_codes:
        st.error("❌ 請至少選擇一個需要協助的時間時段。Choose at least one available time.")
        st.stop()

    resources_list = build_resources_string()
    if not resources_list:
        st.error("❌ 請至少勾選一項『可提供的資源』。Choose at least one available resource.")
        st.stop()

    skills_list = build_skills_string()
    if not skills_list:
        st.error("❌ 請至少勾選一項『希望志工具備的能力』。Choose at least one desired skill.")
        st.stop()

    # --- 處理照片：若有新上傳就用新照片，否則沿用舊的 ---
    if uploaded_photo is None and not prev_photo:
        st.error("❌ 請至少上傳一張地點照片。")
        st.stop()
    elif uploaded_photo is not None:
        # 使用者有上傳新的照片 → 上傳到 Google Drive，取得網址
        photo_to_save = upload_photo_to_supabase(uploaded_photo)
        if not photo_to_save:
            st.error("❌ 照片上傳失敗，請稍後再試。")
            st.stop()
    else:
        # 沒有上傳新照片，但原本就有舊照片 → 繼續沿用
        photo_to_save = prev_photo


    transport_list = build_transport_string()
    if not transport_list:
        st.error("❌ 請至少勾選一項『建議交通方式』。Choose at least one suggested transportion.")
        st.stop()

    row = row_series.to_dict()

    address = st.session_state.get("address_value", "").strip()
    mission_to_save = mission_name.strip() if mission_name.strip() else address

    work_time_str = ", ".join(selected_time_codes)
    resources_str = ", ".join(resources_list)
    skills_str = ", ".join(skills_list)
    transport_str = ", ".join(transport_list)

    def update_field(key, new_value):
        if new_value not in [None, "", 0]:
            row[key] = new_value

    update_field("mission_name", mission_to_save)
    update_field("address", address)
    update_field("work_time", work_time_str)
    update_field("demand_worker", int(demand_worker))
    # selected_worker 交給媒合系統管理
    update_field("resources", resources_str)
    update_field("skills", skills_str)
    update_field("photo", photo_to_save)
    update_field("transport", transport_str)
    update_field("note", note.strip() if note else "")

    ordered_cols = [
        "id_number",
        "role",
        "name",
        "phone",
        "line_id",
        "mission_name",
        "address",
        "work_time",
        "demand_worker",
        "selected_worker",
        "accepted_volunteers",
        "resources",
        "skills",
        "photo",
        "transport",
        "note",
    ]
    new_row = [row.get(col, "") for col in ordered_cols]

    try:
        ws.update(f"A{row_number}:P{row_number}", [new_row])
        st.success("✅ 已成功更新您『今天』的受災需求資料！")
        st.info("若明天需求有變化，可以再次進入本表單，只需調整有改變的項目即可。")
    except Exception as e:
        st.error("❌ 更新資料失敗，請稍後再試。")
        st.error(str(e))
