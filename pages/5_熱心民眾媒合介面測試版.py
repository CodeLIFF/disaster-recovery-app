import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="志工媒合平台（熱心民眾）", layout="wide")

# 精簡 CSS（保留必要樣式）
css = """
<style>
.card-spacer { height: 0.6rem !important; width: 100%; }
.tag-label { display:inline-block; padding:4px 8px; margin-right:1ch; border-radius:6px; font-size:14px; color:#333; }
.block-container { padding-top:0.3rem !important; padding-bottom:0.3rem !important; }
.stApp .block-container > div { margin-top:0.14rem !important; margin-bottom:0.14rem !important; }
.stButton>button { padding:6px 10px !important; font-size:0.95rem !important; }
/* multiselect color targets */
div[data-testid="stMultiSelect"]:nth-of-type(1) [data-baseweb="tag"] { background-color:#FFF8EC !important; color:#333 !important; border:1px solid #FFF8EC !important; }
div[data-testid="stMultiSelect"]:nth-of-type(2) [data-baseweb="tag"] { background-color:#ADEDCC !important; color:#333 !important; border:1px solid #ADEDCC !important; }
div[data-testid="stMultiSelect"]:nth-of-type(3) [data-baseweb="tag"] { background-color:#FFE3B3 !important; color:#333 !important; border:1px solid #FFE3B3 !important; }
div[data-testid="stMultiSelect"]:nth-of-type(4) [data-baseweb="tag"] { background-color:#35D0C7 !important; color:white !important; border:1px solid #35D0C7 !important; }
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ----------------------
# Session state defaults
# ----------------------
if "user_phone" not in st.session_state:
    st.session_state["user_phone"] = None
if "my_new_tasks" not in st.session_state:
    st.session_state["my_new_tasks"] = []
if "page" not in st.session_state:
    st.session_state["page"] = "task_list"

# safe rerun wrapper to avoid AttributeError across Streamlit versions
def safe_rerun():
    for name in ("experimental_rerun", "rerun"):
        fn = getattr(st, name, None)
        if callable(fn):
            return fn()
    # fallback: toggle flag so UI can refresh on next interaction
    st.session_state["_safe_rerun_trigger"] = not st.session_state.get("_safe_rerun_trigger", False)
    st.stop()

# ----------------------
# Google Sheet 連線
# ----------------------
@st.cache_resource
def get_sheet_connection():
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["google"], scopes=SCOPES)
    gc = gspread.authorize(creds)
    SHEET_ID = "1PbYajOLCW3p5vsxs958v-eCPgHC1_DnHf9G_mcFx9C0"
    return gc.open_by_key(SHEET_ID).sheet1

try:
    sheet = get_sheet_connection()
except Exception as e:
    st.error(f"無法連線至 Google Sheets，請檢查 secrets 設定: {e}")
    st.stop()

# ----------------------
# 資料讀取
# ----------------------
@st.cache_data(ttl=3)
def load_data():
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        df.columns = df.columns.str.strip()
        for col in ["id_number", "selected_worker", "demand_worker"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        text_fields = ["phone", "line_id", "mission_name", "address", "work_time",
                       "skills", "resources", "transport", "note", "photo", "role", "name", "other"]
        for col in text_fields:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"讀取資料失敗: {e}")
        return pd.DataFrame()

# ----------------------
# 工具函式
# ----------------------
def normalize_phone(p):
    p = str(p).strip().replace("'", "")
    if len(p) == 9 and p.startswith("9"):
        return "0" + p
    return p

def render_labels(text, mapping_dict, color="#FFD9C0"):
    parts = [p.strip() for p in str(text).split(",") if p.strip()]
    labels = [f'<span class="tag-label" style="background:{color};">{mapping_dict.get(p,p)}</span>' for p in parts]
    return " ".join(labels)

# ----------------------
# 顯示字典
# ----------------------
time_display = {
    "morning": "早上 (08-11)",
    "noon": "中午 (11-13)",
    "afternoon": "下午 (13-17)",
    "night": "晚上 (17-19)"
}
skills_display = {
    "supplies distribution": "物資", "cleaning": "清掃", "medical": "醫療",
    "heavy lifting": "搬運", "driver's license": "駕照", "other": "其他"
}
resources_display = {
    "tool": "工具", "food": "食物", "water": "飲用水", "medical supplies": "醫療",
    "hygiene supplies": "清潔用品", "accommodation": "住宿", "other": "其他"
}
transport_display = {
    "train": "火車", "bus": "巴士", "walk": "步行", "car": "開車",
    "scooter": "機車", "bike": "單車", "other": "其他"
}

# ----------------------
# 主流程
# ----------------------
df = load_data()
if not df.empty:
    missions = df[(df["role"] == "victim") & (df["demand_worker"] > 0)].copy()
    volunteers = df[df["role"] == "volunteer"].copy()
else:
    missions = pd.DataFrame()
    volunteers = pd.DataFrame()

# Signup page: 驗證 + 報名
if st.session_state.get("page") == "signup":
    task_id = st.session_state.get("selected_task_id")
    if task_id is None:
        st.error("未選擇報名的任務，請從任務列表選擇任務後再報名。")
        if st.button("返回任務列表"):
            st.session_state["page"] = "task_list"
            safe_rerun()
        st.stop()

    st.title("報名任務")
    st.info("請先驗證您的志工身份（需先在系統中註冊）")

    # 驗證表單
    if "verified_volunteer" not in st.session_state:
        with st.form("verify_form"):
            verify_phone = st.text_input("請輸入您註冊時的手機號碼（09開頭）")
            verify_submit = st.form_submit_button("驗證身份")

        if verify_submit:
            if not verify_phone:
                st.warning("請輸入手機號碼")
            else:
                verify_phone = verify_phone.strip()
                if not verify_phone.startswith("0") and len(verify_phone) == 9:
                    verify_phone = "0" + verify_phone
                if not (verify_phone.isdigit() and len(verify_phone) == 10 and verify_phone.startswith("09")):
                    st.error("請輸入有效的台灣手機號碼（09開頭共10碼）")
                else:
                    load_data.clear()
                    df_fresh = load_data()
                    if df_fresh.empty:
                        st.error("無法讀取資料，請稍後再試")
                        st.stop()
                    df_fresh["phone"] = df_fresh["phone"].apply(normalize_phone)
                    registered_vols = df_fresh[df_fresh["role"] == "volunteer"].copy()
                    matching_vol = registered_vols[registered_vols["phone"] == verify_phone]
                    if matching_vol.empty:
                        verify_phone_clean = verify_phone.replace(" ", "").replace("-", "")
                        matching_vol = registered_vols[
                            registered_vols["phone"].str.replace(" ", "").str.replace("-", "") == verify_phone_clean
                        ]
                    if matching_vol.empty:
                        st.error("查無此手機號碼的註冊記錄，請先完成志工註冊！")
                        if len(registered_vols) > 0:
                            masked_phones = [f"{p[:4]}****{p[-2:]}" for p in registered_vols["phone"].tolist()[:5]]
                            st.info(f"資料庫中已註冊電話範例：{', '.join(masked_phones)}")
                        if st.button("返回任務列表"):
                            st.session_state["page"] = "task_list"
                            safe_rerun()
                        st.stop()
                    # 取代表筆
                    vol_info = matching_vol[matching_vol["id_number"] == 0].iloc[0] if len(matching_vol) > 1 and not matching_vol[matching_vol["id_number"] == 0].empty else matching_vol.iloc[0]
                    st.session_state["verified_volunteer"] = {
                        "name": str(vol_info.get("name", "")),
                        "phone": verify_phone,
                        "line_id": str(vol_info.get("line_id", ""))
                    }
                    st.success(f"驗證成功！歡迎 {vol_info.get('name', '志工')}！")
                    safe_rerun()

    # 已驗證 -> 報名
    else:
        vol_info = st.session_state["verified_volunteer"]
        st.success(f"已驗證身份：{vol_info['name']} ({vol_info['phone']})")
        st.info("請確認報名資訊")

        load_data.clear()
        df_fresh = load_data()
        if df_fresh.empty:
            st.error("無法讀取任務資料，請稍後再試。")
            if st.button("返回任務列表"):
                st.session_state["page"] = "task_list"
                del st.session_state["verified_volunteer"]
                safe_rerun()
            st.stop()

        df_fresh["phone"] = df_fresh["phone"].apply(normalize_phone)
        signup_records = df_fresh[(df_fresh["role"] == "volunteer") & (df_fresh["id_number"] > 0)]
        is_duplicate = not signup_records[(signup_records["phone"] == vol_info["phone"]) & (signup_records["id_number"] == int(task_id))].empty

        if is_duplicate:
            st.error("您已經報名過此任務，請勿重複報名！")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("返回列表"):
                    del st.session_state["verified_volunteer"]
                    st.session_state["page"] = "task_list"
                    safe_rerun()
            with col2:
                if st.button("報名其他任務"):
                    del st.session_state["verified_volunteer"]
                    st.session_state["page"] = "task_list"
                    safe_rerun()
            st.stop()

        task_info = df_fresh[(df_fresh["role"] == "victim") & (df_fresh["id_number"] == int(task_id))]
        if not task_info.empty:
            task = task_info.iloc[0]
            st.markdown("### 報名任務資訊")
            st.write(f"**任務名稱：** {task.get('mission_name', '未命名任務')}")
            st.write(f"**地址：** {task.get('address', '')}")
            st.write(f"**工作時間：** {task.get('work_time', '')}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 確認報名", type="primary", use_container_width=True):
                try:
                    phone_to_write = "'" + vol_info["phone"]
                    victim_name = victim_phone = victim_line = victim_note = ""
                    if not df_fresh.empty:
                        victim_rows = df_fresh[(df_fresh["role"] == "victim") & (df_fresh["id_number"] == int(task_id))]
                        if not victim_rows.empty:
                            vr = victim_rows.iloc[0]
                            victim_name = str(vr.get("name", "")).strip()
                            victim_phone = normalize_phone(str(vr.get("phone", "")).strip())
                            victim_line = str(vr.get("line_id", "")).strip()
                            victim_note = str(vr.get("note", "")).strip()
                    if victim_name or victim_phone or victim_line or victim_note:
                        contact_note = f"受災戶姓名：{victim_name}\n電話：{victim_phone}\nLineID：{victim_line}\n備註：{victim_note}"
                    else:
                        contact_note = "受災戶聯絡資料：無（目標任務未在 Sheet 找到對應受災戶）。"
                    row_data = [int(task_id), "volunteer", vol_info["name"], phone_to_write, vol_info["line_id"], "", "", "", "", "", "", contact_note]
                    sheet.append_row(row_data)
                    st.session_state["user_phone"] = vol_info["phone"]
                    st.session_state["my_new_tasks"].append(int(task_id))
                    load_data.clear()
                    st.success("報名成功！")
                    st.markdown(f"```\n{contact_note}\n```")
                    del st.session_state["verified_volunteer"]
                    if st.button("返回任務列表", use_container_width=True):
                        st.session_state["page"] = "task_list"
                        safe_rerun()
                except Exception as e:
                    st.error(f"報名失敗: {e}")
                    st.stop()

        with col2:
            if st.button("取消報名", use_container_width=True):
                if "verified_volunteer" in st.session_state:
                    del st.session_state["verified_volunteer"]
                st.session_state["page"] = "task_list"
                safe_rerun()
    st.stop()

# 任務列表頁面
st.title("災後人力媒合平台（熱心民眾端）")
st.caption("以下為受災戶上傳的最新需求")

# 篩選 UI
col1, col2, col3, col4 = st.columns(4)
with col1:
    time_options = list(time_display.values())
    selected_times = st.multiselect("工作時間", time_options, placeholder="選擇時段")
with col2:
    skill_options = list(skills_display.values())
    selected_skills = st.multiselect("能力需求", skill_options, placeholder="選擇技能")
with col3:
    resource_options = list(resources_display.values())
    selected_resources = st.multiselect("提供資源", resource_options, placeholder="選擇資源")
with col4:
    transport_options = list(transport_display.values())
    selected_transports = st.multiselect("建議交通", transport_options, placeholder="選擇交通方式")

keyword = st.text_input("地址關鍵字搜尋", placeholder="輸入地址關鍵字")
search_button = st.button("🔍 開始搜尋", type="primary", key="search_btn")

# 反向映射
time_reverse = {v: k for k, v in time_display.items()}
skills_reverse = {v: k for k, v in skills_display.items()}
resources_reverse = {v: k for k, v in resources_display.items()}
transport_reverse = {v: k for k, v in transport_display.items()}

filtered_missions = missions.copy()
if search_button or selected_times or selected_skills or selected_resources or selected_transports or keyword:
    if selected_times:
        time_keys = [time_reverse[t] for t in selected_times]
        filtered_missions = filtered_missions[filtered_missions["work_time"].apply(lambda x: any(key in str(x) for key in time_keys))]
    if selected_skills:
        skill_keys = [skills_reverse[s] for s in selected_skills]
        filtered_missions = filtered_missions[filtered_missions["skills"].apply(lambda x: any(key in str(x) for key in skill_keys))]
    if selected_resources:
        resource_keys = [resources_reverse[r] for r in selected_resources]
        filtered_missions = filtered_missions[filtered_missions["resources"].apply(lambda x: any(key in str(x) for key in resource_keys))]
    if selected_transports:
        transport_keys = [transport_reverse[t] for t in selected_transports]
        filtered_missions = filtered_missions[filtered_missions["transport"].apply(lambda x: any(key in str(x) for key in transport_keys))]
    if keyword:
        k = keyword.strip()
        filtered_missions = filtered_missions[filtered_missions["address"].str.contains(k, case=False, na=False)]

st.write(f"共 {len(filtered_missions)} 筆需求")
st.markdown("---")

mission_counts = volunteers["id_number"].value_counts().to_dict()
current_user_phone = st.session_state.get("user_phone")
joined_in_sheet = volunteers[volunteers["phone"] == current_user_phone]["id_number"].tolist() if current_user_phone else []
all_my_joined_tasks = set(joined_in_sheet + st.session_state["my_new_tasks"])
has_joined_any = len(all_my_joined_tasks) > 0

for idx, row in filtered_missions.iterrows():
    tid = int(row["id_number"])
    current_count = mission_counts.get(tid, 0)
    if tid in st.session_state["my_new_tasks"] and tid not in joined_in_sheet:
        current_count += 1

    left, right = st.columns([2, 1])
    with left:
        mission_title = str(row.get("mission_name", "")).strip()
        addr = str(row.get("address", "")).strip()
        if mission_title:
            st.markdown(f"### {mission_title}")
        elif addr:
            st.markdown(f"### 任務地址：{addr}")
        else:
            st.markdown(f"### 任務 #{tid}")
        if addr:
            st.markdown(f"地址： {addr}")

        st.markdown(f'<span style="font-weight:600;margin-right:20px"> 工作時間：</span>{render_labels(row["work_time"], time_display, "#FFF8EC")}', unsafe_allow_html=True)
        st.markdown(f" 人數： {current_count} / {row['demand_worker']}")
        st.markdown(f'<span style="font-weight:600;margin-right:25px"> 提供資源：</span>{render_labels(row["resources"], resources_display, "#FFE3B3")}', unsafe_allow_html=True)
        st.markdown(f'<span style="font-weight:600;margin-right:25px"> 能力需求：</span>{render_labels(row["skills"], skills_display, "#ADEDCC")}', unsafe_allow_html=True)
        st.markdown(f'<span style="font-weight:600;margin-right:25px"> 建議交通方式：</span>{render_labels(row["transport"], transport_display, "#35D0C7")}', unsafe_allow_html=True)
        st.markdown(f" 備註： {row['note']}")

        task_vols = volunteers[volunteers["id_number"] == tid]
        if not task_vols.empty:
            vols_display = []
            for _, v in task_vols.iterrows():
                v_phone = str(v.get('phone', ''))
                show_phone = v_phone[-3:] if len(v_phone) >= 3 else ""
                vols_display.append(f"{v.get('name','匿名')} ({show_phone})")
            st.markdown("**已報名志工：** " + "、".join(vols_display))

        is_full = current_count >= row["demand_worker"]
        is_joined_this = tid in all_my_joined_tasks

        if is_joined_this:
            st.success("✅ 您已報名此任務")
        elif has_joined_any:
            st.warning("⚠ 您已報名其他任務 (每人限一項)")
        elif is_full:
            st.error("❌ 已額滿")
        else:
            if st.button("我要報名", key=f"btn_{tid}"):
                st.session_state["page"] = "signup"
                st.session_state["selected_task_id"] = int(tid)
                safe_rerun()

    with right:
        photo = str(row.get("photo", "")).strip()
        if photo.startswith("http"):
            st.image(photo, use_column_width=True)
        else:
            st.info("尚無照片")

    st.markdown("<div class='card-spacer'></div>", unsafe_allow_html=True)import streamlit as st
import pandas as pd
import os

st.title("志工媒合平台")

CSV_PATH = "tasks.csv"

# 讀取 CSV
def load_data():
    if not os.path.exists(CSV_PATH):
        return pd.DataFrame(columns=[
            "id", "address", "work_time",
            "need_people", "selected_people",
            "skills", "resources",
            "photo_url", "transport",
            "note", "contact", "created_at"
        ])
    return pd.read_csv(CSV_PATH)

# 儲存 CSV
def save_data(df):
    df.to_csv(CSV_PATH, index=False)

# =============================
# 讀取資料
# =============================
df = load_data()

# 上傳資料
uploaded_file = st.file_uploader("上傳受災戶需求 CSV 檔案", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    save_data(df)
    st.success("CSV 上傳成功並已儲存！")

# 空資料處理
if df.empty:
    st.info("目前沒有任務可顯示，請上傳 CSV。")
    st.stop()

# =============================
# 搜尋 + 排序
# =============================
keyword = st.text_input("搜尋任務（技能、地址、備註…）")
sort_option = st.selectbox("排序方式", ["最新優先", "缺人最多"])

# 搜尋
if keyword:
    df = df[df.apply(lambda row: keyword.lower() in str(row).lower(), axis=1)]

# 排序
if sort_option == "最新優先":
    df = df.sort_values("id", ascending=False)
else:
    df["缺口"] = df["need_people"] - df["selected_people"]
    df = df.sort_values("缺口", ascending=False)

# 初始化 session_state
if "accepted_task" not in st.session_state:
    st.session_state.accepted_task = None

# =============================
# 任務列表
# =============================
st.subheader("任務列表")

for idx, row in df.iterrows():

    with st.container():
        st.subheader("用戶需求")

        st.write(f"📍 地點：{row['address']}")
        st.write(f"🕒 時間：{row['work_time']}")
        st.write(f"👥 需求人數：{row['need_people']}")
        st.write(f"🎯 已選志工：{row['selected_people']}")
        st.write(f"🔧 技能：{row['skills']}")
        st.write(f"🔨 物資：{row['resources']}")
        st.write(f"🚌 交通方式：{row['transport']}")
        st.write(f"📝 備註：{row['note']}")

        if isinstance(row["photo_url"], str) and row["photo_url"].strip() != "":
            st.image(row["photo_url"], use_container_width=True)

        # 按下按鈕 → 接取任務
        if st.button("確定接取", key=f"accept_{idx}"):
            st.session_state.accepted_task = row["id"]
            

        st.write("---")


# =============================
# 顯示接取結果 + 更新資料
# =============================

if st.session_state.accepted_task is not None:

    task_id = st.session_state.accepted_task

    task = df[df["id"] == task_id].iloc[0]

    st.success("🎉 你已成功接取此任務！")
    st.info(f"📞 受災戶聯絡資訊：{task['contact']}")

    # 更新該任務 selected_people +1
    df.loc[df["id"] == task_id, "selected_people"] += 1

    # 儲存變更到 CSV
    save_data(df)

    # 顯示更新後的人數
    updated = df[df["id"] == task_id].iloc[0]
    st.write(f"🎯 更新後已選志工：{updated['selected_people']} 人")

    # 清除狀態（避免重新載入時重複顯示）
    st.session_state.accepted_task = None
