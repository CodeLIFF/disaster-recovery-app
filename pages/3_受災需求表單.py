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

# 可變動的災區關鍵字（之後你們只要改這一行即可）
ALLOWED_REGION = "花蓮縣"


# ---------- 小工具：讀取資料 + 找受災戶那一列 ----------
def load_df():
    data = ws.get_all_records()
    return pd.DataFrame(data) if data else pd.DataFrame()


def find_victim_row(name, phone):
    df = load_df()
    if df.empty:
        return None, None

    mask = (df["role"] == "victim") & (df["name"] == name) & (df["phone"] == phone)
    if not mask.any():
        return None, df

    idx = df.index[mask][0]
    row_number = idx + 2  # DataFrame index 0 -> Google Sheet 第 2 列
    return row_number, df.loc[idx]


# ---------- 驗證 address 是否在指定縣市，且不含英文字母 ----------
def validate_address(address: str, allowed_region: str) -> str | None:
    address = address.strip()
    if not address:
        return "❌ 地址（address）為必填"

    # 必須包含災區關鍵字，例如「花蓮縣」
    if allowed_region not in address:
        return f"❌ 目前僅限災區（{allowed_region}），系統判定此地址不在災區內。"

    # 不希望有英文字母（防止亂填）
    if re.search(r"[A-Za-z]", address):
        return "❌ 地址請以中文與數字為主，請不要包含英文字母"

    return None


# ---------- 受災需求表單 ----------
st.title("受災需求表單（victim）")

st.write("請先輸入與「基本資料表單」相同的姓名與電話，以便系統找到您的紀錄。")
st.caption("＊只有在基本資料表單中選擇「受災戶 victim」的人，才會被找到。")

name = st.text_input("姓名（需與基本資料表單一致）", key="victim_name")
phone = st.text_input("電話（需與基本資料表單一致）", key="victim_phone")

st.markdown("---")

# 任務與地址
mission_name = st.text_input(
    "任務名稱（mission_name，可留白）",
    placeholder="可填大致地點與主要需求，例如：花蓮縣某某里住家清理",
    help="若留白，系統會自動以地址當作任務名稱。",
)

address = st.text_input(
    "通訊 / 受災地址（address，必填）",
    placeholder="請填寫完整地址，例如：花蓮縣○○鄉○○村○○路○號",
)

# 工作時間：多選
st.subheader("需要協助的時間（work_time，必填，可複選）")
time_options = {
    "早上 morning (08:00–11:00)": "morning",
    "中午 noon (11:00–13:00)": "noon",
    "下午 afternoon (13:00–17:00)": "afternoon",
    "晚上 night (17:00–19:00)": "night",
}
selected_time_labels = st.multiselect(
    "請選擇需要協助的時段：",
    list(time_options.keys()),
)
selected_time_codes = [time_options[label] for label in selected_time_labels]

# 人力需求
demand_worker = st.number_input(
    "總人數需求（demand_worker，必填，上限 20）",
    min_value=1,
    max_value=20,
    step=1,
)

st.markdown("---")

# 提供資源 resources：多選 + 其他
st.subheader("可提供的資源（resources，必填，可複選）")
res_tool = st.checkbox("工具 tool")
res_food = st.checkbox("食物 food")
res_water = st.checkbox("水 water")
res_med = st.checkbox("醫療用品 medical supplies")
res_hygiene = st.checkbox("衛生用品 hygiene supplies")
res_accommodation = st.checkbox("住宿 accommodation")
res_other = st.checkbox("其他 other resources")

res_other_text = ""
if res_other:
    res_other_text = st.text_input("請說明其他資源", key="res_other_text")

# 能力需求 skills：多選 + 其他
st.subheader("希望志工具備的能力（skills，必填，可複選）")
sk_supplies = st.checkbox("物資發放 supplies distribution")
sk_cleaning = st.checkbox("清掃 cleaning")
sk_medical = st.checkbox("醫療 medical")
sk_lifting = st.checkbox("搬運 heavy lifting")
sk_license = st.checkbox("駕照 driver's license")
sk_other = st.checkbox("其他 other skills")

sk_other_text = ""
if sk_other:
    sk_other_text = st.text_input("請說明其他能力需求", key="sk_other_text")

# 地點照片
photo = st.text_input(
    "地點當前照片連結（photo，必填）",
    placeholder="建議先將照片上傳至 Google Drive，設定共用後再貼上分享網址",
)

# 建議交通方式 transport：多選 + 其他
st.subheader("建議交通方式（transport，必填，可複選）")
tr_train = st.checkbox("火車 train")
tr_bus = st.checkbox("巴士 bus")
tr_walk = st.checkbox("步行 walk")
tr_car = st.checkbox("開車 car")
tr_scooter = st.checkbox("騎機車 scooter")
tr_bike = st.checkbox("腳踏車 bike")
tr_other = st.checkbox("其他 other transport")

tr_other_text = ""
if tr_other:
    tr_other_text = st.text_input("請說明其他交通方式", key="tr_other_text")

# 備註
note = st.text_area("備註 / 想說的話（note，可選填）")


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


if st.button("送出受災需求"):
    # 1. 檢查姓名/電話
    if not name or not phone:
        st.error("❌ 姓名與電話為必填，且需與「基本資料表單」一致")
        st.stop()

    # 2. 找到對應受災戶紀錄
    row_number, row_series = find_victim_row(name, phone)
    if row_number is None:
        st.error("❌ 找不到您的基本資料（role = victim）。")
        st.info("請先在「基本資料表單」選擇『受災戶 victim』並填寫，或確認姓名、電話是否輸入正確。")
        st.stop()

    # 3. 驗證 address
    address_error = validate_address(address, ALLOWED_REGION)
    if address_error:
        st.error(address_error)
        st.stop()

    # 4. 驗證 work_time
    if not selected_time_codes:
        st.error("❌ 請至少選擇一個需要協助的時間時段（work_time）")
        st.stop()

    # 5. 驗證 resources
    resources_list = build_resources_string()
    if not resources_list:
        st.error("❌ 請至少勾選一項『可提供的資源（resources）』")
        st.stop()

    # 6. 驗證 skills
    skills_list = build_skills_string()
    if not skills_list:
        st.error("❌ 請至少勾選一項『希望志工具備的能力（skills）』")
        st.stop()

    # 7. 驗證 photo
    if not photo.strip():
        st.error("❌ 地點照片連結（photo）為必填，請貼上分享網址。")
        st.stop()

    # 8. 驗證 transport
    transport_list = build_transport_string()
    if not transport_list:
        st.error("❌ 請至少勾選一項『建議交通方式（transport）』")
        st.stop()

    # 9. 準備更新資料
    row = row_series.to_dict()

    # mission_name：若留白，使用 address
    mission_to_save = mission_name.strip() if mission_name.strip() else address.strip()

    # work_time / resources / skills / transport 轉為字串儲存
    work_time_str = ", ".join(selected_time_codes)
    resources_str = ", ".join(resources_list)
    skills_str = ", ".join(skills_list)
    transport_str = ", ".join(transport_list)

    def update_field(key, new_value):
        # 只有在 new_value 真正有意義時才覆蓋
        if new_value not in [None, "", 0]:
            row[key] = new_value

    update_field("mission_name", mission_to_save)
    update_field("address", address.strip())
    update_field("work_time", work_time_str)
    update_field("demand_worker", int(demand_worker))
    # selected_worker 不在這邊改，由媒合系統管理
    update_field("resources", resources_str)
    update_field("skills", skills_str)
    update_field("photo", photo.strip())
    update_field("transport", transport_str)
    update_field("note", note.strip() if note else "")

    # 依照欄位順序重新組合一列
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
        "resources",
        "skills",
        "photo",
        "transport",
        "note",
    ]
    new_row = [row.get(col, "") for col in ordered_cols]

    try:
        ws.update(f"A{row_number}:O{row_number}", [new_row])
        st.success("✅ 已成功更新您的受災需求資料！")
        st.info("後續志工媒合將依據您提供的資訊進行安排。")
    except Exception as e:
        st.error("❌ 更新 Google Sheet 失敗，請稍後再試。")
        st.error(str(e))
