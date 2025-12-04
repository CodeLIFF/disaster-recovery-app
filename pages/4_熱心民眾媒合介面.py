import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re  # <- normalize_phone 使用到 re

st.set_page_config(page_title="志工媒合平台（熱心民眾）", layout="wide")

# ----- 緊湊模式 CSS（預設套用） -----
css = """
<style>
/* 卡片間距與 hr */
.stMarkdown hr, hr {
    margin-top: 1.0rem !important;
    margin-bottom: 1.0rem !important;
    height: 1px;
    background: #e6e6e6;
    border: none;
}
.card-spacer {
    height: 0.6rem !important;
    width: 100%;
}

/* 標籤 (tag) 樣式：保證每個標籤之間至少有一個字元寬度 */
.tag-label {
    display: inline-block;
    padding: 4px 8px;
    margin-right: 1ch; /* 至少一個字元寬度的空白 */
    border-radius: 6px;
    font-size: 14px;
    color: #333;
}

/* 緊湊模式的頁面間距微調（調整為原先的一半） */
.block-container {
    padding-top: 0.3rem !important;
    padding-bottom: 0.3rem !important;
}
.stApp .block-container > div {
    margin-top: 0.14rem !important;
    margin-bottom: 0.14rem !important;
}
.stButton>button {
    padding: 6px 10px !important;
    font-size: 0.95rem !important;
}
/* 工作時間 multiselect - 對應 #FFF8EC */
div[data-testid="stMultiSelect"]:nth-of-type(1) [data-baseweb="tag"] {
    background-color: #FFF8EC !important;
    color: #333 !important;
    border: 1px solid #FFF8EC !important;
}

/* 能力需求 multiselect - 對應 #ADEDCC */
div[data-testid="stMultiSelect"]:nth-of-type(2) [data-baseweb="tag"] {
    background-color: #ADEDCC !important;
    color: #333 !important;
    border: 1px solid #ADEDCC !important;
}

/* 提供資源 multiselect - 對應 #FFE3B3 */
div[data-testid="stMultiSelect"]:nth-of-type(3) [data-baseweb="tag"] {
    background-color: #FFE3B3 !important;
    color: #333 !important;
    border: 1px solid #FFE3B3 !important;
}

/* 建議交通 multiselect - 對應 #35D0C7 */
div[data-testid="stMultiSelect"]:nth-of-type(4) [data-baseweb="tag"] {
    background-color: #35D0C7 !important;
    color: white !important;
    border: 1px solid #35D0C7 !important;
}

</style>
"""

st.markdown(css, unsafe_allow_html=True)

# 共用手機標準化函式
def normalize_phone(p):
    """
    統一電話格式：
    - 移除單引號 (Google Sheets 的文字前綴)
    - 去掉空白、破折號等非數字字元
    - 9 碼且 9 開頭則補 0
    - 回傳標準 10 碼電話號碼（若無法取得則回傳原數字序列）
    """
    if p is None or p == "":
        return ""
    
    # 移除單引號
    p = str(p).strip().replace("'", "")
    
    # 只保留數字
    p = re.sub(r"\D", "", p)
    
    # 若長度 9 且 9 開頭，補 0
    if len(p) == 9 and p.startswith("9"):
        return "0" + p
    
    return p

# ==========================================
# 1. 初始化設定與連線
# ==========================================

# 初始化 Session State (用來記住使用者身份與暫存報名狀態)
if "user_phone" not in st.session_state:
    st.session_state["user_phone"] = None  # 登入/報名後的電話
if "my_new_tasks" not in st.session_state:
    st.session_state["my_new_tasks"] = []  # 剛報名但還沒寫入 Sheet 的任務 ID
if "page" not in st.session_state:
    st.session_state["page"] = "task_list"  # 預設頁面
# selected_task_id 會在點選報名按鈕時被設定

# 安全 rerun wrapper（處理不同 Streamlit 版本沒有 experimental_rerun 屬性的情況）
def safe_rerun():
    # 先嘗試呼叫常見的 rerun 實作
    for name in ("experimental_rerun", "rerun"):
        fn = getattr(st, name, None)
        if callable(fn):
            return fn()
    # 若都沒有，使用 session_state toggle 並 stop（可在下次互動時看到更新）
    st.session_state["_safe_rerun_trigger"] = not st.session_state.get("_safe_rerun_trigger", False)
    st.stop()

# Google Sheet 連線 (使用快取資源，避免重複連線)
@st.cache_resource
def get_sheet_connection():
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["google"],
        scopes=SCOPES
    )
    gc = gspread.authorize(creds)
    SHEET_ID = "1PbYajOLCW3p5vsxs958v-eCPgHC1_DnHf9G_mcFx9C0"
    # Use named worksheet "vol" (consistent with other pages)
    return gc.open_by_key(SHEET_ID).worksheet("vol")

try:
    sheet = get_sheet_connection()
except Exception as e:
    st.error(f"無法連線至 Google Sheets，請檢查 secrets 設定: {e}")
    st.stop()

# ==========================================
# 2. 資料讀取與處理函式
# ==========================================

# 讀取資料 (設定 ttl=3 秒，3秒內重新整理不會真的去呼叫 Google API，保護額度)
@st.cache_data(ttl=3)
def load_data():
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # 清洗欄位名稱
        df.columns = df.columns.str.strip()
        
        # 轉型數值欄位
        for col in ["id_number", "selected_worker", "demand_worker"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        
        # 轉型文字欄位
        text_fields = ["phone", "line_id", "mission_name", "address", "work_time",
                       "skills", "resources", "transport", "note", "photo", "role", "name", "other", "accepted_volunteers"]
        for col in text_fields:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str).str.strip()
        if "phone" in df.columns:
            # ✅ 特別處理 phone 欄位：移除單引號並標準化
            df["phone"] = df["phone"].apply(normalize_phone)

        # ----- 新增容錯：確保後續程式會使用到的欄位都存在 -----
        # 若缺少預期的數值欄位，補上預設 0
        required_ints = ["id_number", "selected_worker", "demand_worker"]
        for c in required_ints:
            if c not in df.columns:
                df[c] = 0
            else:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
        # 若缺少預期的文字欄位，補上空字串
        required_texts = ["phone", "line_id", "mission_name", "address", "work_time",
                          "skills", "resources", "transport", "note", "photo", "role", "name", "other", "accepted_volunteers"]
        for c in required_texts:
            if c not in df.columns:
                df[c] = ""
            else:
                df[c] = df[c].fillna("").astype(str).str.strip()

        # 最後再一次標準化 phone 欄位
        df["phone"] = df["phone"].apply(normalize_phone)

        return df
    except Exception as e:
        st.error(f"讀取資料失敗: {e}")
        return pd.DataFrame()

# 輔助函式：翻譯與標籤顯示
translate = {
    "morning": " 早上 (08-11) ",
    "noon": " 中午 (11-13) ",
    "afternoon": " 下午 (13-17) ",
    "night": " 晚上 (17-19) "
}
def t(value):
    value = str(value).strip()
    return f"{translate[value]} ({value})" if value in translate else value

def translate_list(text):
    parts = [p.strip() for p in str(text).split(",")]
    return "、".join([t(p) for p in parts if p])

def render_labels(text, mapping_dict, color="#FFD9C0"):
    # 以 class="tag-label" 並帶入背景色，確保標籤之間有至少一個字元的空間（CSS margin-right:1ch）
    parts = [p.strip() for p in str(text).split(",") if p.strip()]
    labels = []
    for p in parts:
        label = mapping_dict.get(p, p)
        # 使用 class + inline background color（可被 color 參數覆蓋）
        html = f'<span class="tag-label" style="background:{color};">{label}</span>'
        labels.append(html)
    return " ".join(labels)  # 用空白將 span 串起（使閱讀上更自然）

# UI 顯示字典
time_display = {
    "morning": " 早上 (08-11)",
    "noon": " 中午 (11-13)",
    "afternoon": " 下午 (13-17)",
    "night": " 晚上 (17-19)"
}
skills_display = {
    "supplies distribution": " 物資",
    "cleaning": " 清掃",
    "medical": " 醫療",
    "heavy lifting": " 搬運",
    "driver's license": " 駕照",
    "other": " 其他"
}
resources_display = {
    "tool": " 工具",
    "food": " 食物",
    "water": " 飲用水",
    "medical supplies": " 醫療",
    "hygiene supplies": " 清潔用品",
    "accommodation": " 住宿",
    "other": " 其他"
}
transport_display = {
    "train": " 火車",
    "bus": " 巴士",
    "walk": " 步行",
    "car": " 開車",
    "scooter": " 機車",
    "bike": " 單車",
    "other": " 其他"
}

# ---------- accepted_volunteers 相關 helper ----------
def format_vol_entry(name, phone):
    """統一格式：Name(末3碼)。用於比對與顯示。"""
    pn = normalize_phone(phone)
    suffix = pn[-3:] if pn else ""
    return f"{name}({suffix})"

def parse_accepted_volunteers(text):
    """把 accepted_volunteers 文字拆成清單（每行一筆），並去除空白。"""
    if not text:
        return []
    return [l.strip() for l in str(text).splitlines() if l.strip()]

def volunteer_signed_up_for_task(df, task_id, vol_name, vol_phone):
    """檢查某志工（name + phone）是否已在指定任務的 accepted_volunteers 裡。"""
    victim_rows = df[(df["role"] == "victim") & (df["id_number"] == int(task_id))]
    if victim_rows.empty:
        return False
    acc_text = str(victim_rows.iloc[0].get("accepted_volunteers", "") or "")
    entries = parse_accepted_volunteers(acc_text)
    target = format_vol_entry(vol_name, vol_phone)
    return target in entries

def add_volunteer_to_task_on_sheet(df, task_id, vol_name, vol_phone):
    """
    將志工加入指定任務的 accepted_volunteers 並在 sheet 上更新 selected_worker 與 accepted_volunteers。
    會回傳 True/False 表示是否成功；若失敗會 raise Exception 由呼叫端處理。
    """
    # 取得工作表列號（DataFrame index -> Google Sheet row）
    victim_idx = df.index[(df["role"] == "victim") & (df["id_number"] == int(task_id))]
    if len(victim_idx) == 0:
        raise ValueError("找不到指定任務在資料表中的列")
    task_row_idx = victim_idx[0] + 2  # DataFrame index 0 -> sheet row 2

    # 取得當前 selected_worker 與 accepted_volunteers
    current_count_in_sheet = int(df.loc[df["id_number"] == int(task_id), "selected_worker"].iloc[0])
    existing = str(df.loc[df["id_number"] == int(task_id), "accepted_volunteers"].iloc[0] or "")

    new_entry = format_vol_entry(vol_name, vol_phone)
    existing_list = parse_accepted_volunteers(existing)
    if new_entry in existing_list:
        # 已存在，不重複加入
        return False

    # 檢查是否已額滿
    current_demand = int(df.loc[df["id_number"] == int(task_id), "demand_worker"].iloc[0])
    if current_count_in_sheet >= current_demand:
        raise ValueError("任務已額滿")

    updated_val = (existing + "\n" + new_entry).strip()
    # 找出 sheet 的欄位 index（使用 DataFrame 的欄位位置 +1）
    selected_col = df.columns.get_loc("selected_worker") + 1
    acc_col = df.columns.get_loc("accepted_volunteers") + 1

    # 更新 sheet（gspread 的 update_cell 使用 1-index）
    sheet.update_cell(task_row_idx, selected_col, current_count_in_sheet + 1)
    sheet.update_cell(task_row_idx, acc_col, updated_val)
    return True

# ==========================================
# 3. 程式主流程（以 page 控制，點「我要報名」會切換到 signup）
# ==========================================

# --- 步驟 A: 讀取最新資料 ---
df = load_data()

# 分離任務與志工
if not df.empty:
    missions = df[(df["role"] == "victim") & (df["demand_worker"] > 0)].copy()
    volunteers = df[df["role"] == "volunteer"].copy()
else:
    missions = pd.DataFrame()
    volunteers = pd.DataFrame()

# ========== 聯絡資訊確認頁面 ==========
if st.session_state.get("page") == "check_contact":
    task_id = st.session_state.get("check_contact_task_id")
    
    if task_id is None:
        st.error("未選擇任務，請從任務列表操作。")
        if st.button("返回任務列表", key="cc_top_return"):
            st.session_state["page"] = "task_list"
            safe_rerun()
        st.stop()
    
    st.title("確認聯絡資訊")
    st.info("請驗證您已報名此任務")

    # 新增：常駐返回按鈕，避免點錯卡住
    if st.button("🔙 返回任務列表", use_container_width=True, key="cc_back_top"):
        if "contact_verified_volunteer" in st.session_state:
            del st.session_state["contact_verified_volunteer"]
        st.session_state["page"] = "task_list"
        safe_rerun()
    
    if "contact_verified_volunteer" not in st.session_state:
        with st.form("contact_verify_form"):
            verify_phone = st.text_input("請輸入您報名時的手機號碼（09開頭）")
            verify_submit = st.form_submit_button("驗證身份")
        
        if verify_submit:
            if not verify_phone:
                st.warning("❌ 請輸入手機號碼")
            else:
                # 標準化輸入
                verify_phone = verify_phone.strip()
                if not verify_phone.startswith("0") and len(verify_phone) == 9:
                    verify_phone = "0" + verify_phone
                verify_phone = normalize_phone(verify_phone)

                if not (verify_phone.isdigit() and len(verify_phone) == 10 and verify_phone.startswith("09")):
                    st.error("❌ 請輸入有效的台灣手機號碼（09開頭共10碼）")
                else:
                    # 重新讀取最新資料
                    load_data.clear()
                    df_fresh = load_data()
                    if df_fresh.empty:
                        st.error("❌ 無法讀取資料，請稍後再試")
                        st.stop()

                    # 檢查該手機是否存在於指定任務的 accepted_volunteers
                    # 透過比對末三碼（與系統加入格式一致）
                    victim_rows = df_fresh[(df_fresh["role"] == "victim") & (df_fresh["id_number"] == int(task_id))]
                    if victim_rows.empty:
                        st.error("❌ 找不到該任務")
                        st.stop()
                    acc_text = str(victim_rows.iloc[0].get("accepted_volunteers", "") or "")
                    entries = parse_accepted_volunteers(acc_text)
                    suffix = verify_phone[-3:] if verify_phone else ""
                    matched = any(suffix and suffix in e for e in entries)
                    
                    if not matched:
                        st.error("❌ 您尚未報名此任務，無法查看聯絡資訊！")
                        if st.button("返回任務列表", key="cc_verify_fail_return"):
                            st.session_state["page"] = "task_list"
                            safe_rerun()
                        st.stop()
                    else:
                        st.session_state["contact_verified_volunteer"] = verify_phone
                        st.success("✅ 驗證成功！")
                        safe_rerun()
    
    else:
        # 已驗證，顯示受災戶聯絡資訊
        st.success("✅ 驗證通過")
        
        load_data.clear()
        df_fresh = load_data()
        
        victim_rows = df_fresh[(df_fresh["role"] == "victim") & (df_fresh["id_number"] == int(task_id))]
        
        if not victim_rows.empty:
            vr = victim_rows.iloc[0]
            victim_name = str(vr.get("name", "")).strip()
            victim_phone = normalize_phone(str(vr.get("phone", "")).strip())
            victim_line = str(vr.get("line_id", "")).strip()
            victim_note = str(vr.get("note", "")).strip()
            
            st.markdown("### 📞 受災戶聯絡資訊")
            st.write(f"**姓名：** {victim_name}")
            st.write(f"**電話：** {victim_phone}")
            st.write(f"**Line ID：** {victim_line}")
            if victim_note:
                st.write(f"**備註：** {victim_note}")
        else:
            st.warning("⚠ 無法找到受災戶聯絡資訊")
        
        # 新增：已驗證狀態也提供返回按鈕（原本已存在，保留）
        if st.button("🔙 返回任務列表", use_container_width=True, key="cc_back_verified"):
            if "contact_verified_volunteer" in st.session_state:
                del st.session_state["contact_verified_volunteer"]
            st.session_state["page"] = "task_list"
            safe_rerun()
    
    st.stop()

# 分支：signup 頁面（驗證身份 + 報名流程）
if st.session_state.get("page") == "signup":
    # 確保有選到任務 ID
    task_id = st.session_state.get("selected_task_id")
    if task_id is None:
        st.error("未選擇報名的任務，請從任務列表選擇任務後再報名。")
        if st.button("返回任務列表", key="signup_no_task_return"):
            st.session_state["page"] = "task_list"
            safe_rerun()
        st.stop()
    
    st.title("報名任務")
    st.info("請先驗證您的志工身份（需先在系統中註冊）")

    # 階段 1: 驗證身份（檢查是否已註冊）
    if "verified_volunteer" not in st.session_state:
        with st.form("verify_form"):
            verify_phone = st.text_input("請輸入您註冊時的手機號碼（09開頭）")
            verify_submit = st.form_submit_button("驗證身份")
        
        if verify_submit:
            # 基礎格式驗證
            if not verify_phone:
                st.warning("❌ 請輸入手機號碼")
            else:
                # 標準化輸入的手機號碼
                verify_phone = verify_phone.strip()
                if not verify_phone.startswith("0") and len(verify_phone) == 9:
                    verify_phone = "0" + verify_phone
                verify_phone = normalize_phone(verify_phone)

                if not (verify_phone.isdigit() and len(verify_phone) == 10 and verify_phone.startswith("09")):
                    st.error("❌ 請輸入有效的台灣手機號碼（09開頭共10碼）")
                else:
                    # 重新讀取最新資料以避免 race condition
                    load_data.clear()
                    df_fresh = load_data()

                    if df_fresh.empty:
                        st.error("❌ 無法讀取資料，請稍後再試")
                        st.stop()

                    # 標準化所有電話號碼
                    df_fresh["phone"] = df_fresh["phone"].apply(normalize_phone)

                    # 只要 role = "volunteer" 就算已註冊
                    registered_vols = df_fresh[df_fresh["role"] == "volunteer"].copy()

                    # 嘗試直接比對
                    matching_vol = registered_vols[registered_vols["phone"] == verify_phone]

                    # 如果找不到，嘗試移除空格與 dash 比對
                    if matching_vol.empty:
                        verify_phone_clean = verify_phone.replace(" ", "").replace("-", "")
                        matching_vol = registered_vols[
                            registered_vols["phone"].str.replace(" ", "").str.replace("-", "") == verify_phone_clean
                        ]

                    if matching_vol.empty:
                        st.error("❌ 查無此手機號碼的註冊記錄，請先完成志工註冊！")
                        st.info(f" 提示：您輸入的號碼是 {verify_phone}")
                        if len(registered_vols) > 0:
                            masked_phones = [f"{p[:4]}****{p[-2:]}" for p in registered_vols["phone"].tolist()[:5]]
                            st.info(f"資料庫中已註冊電話範例：{', '.join(masked_phones)}")
                        if st.button("返回任務列表", key="signup_verify_fail_return"):
                            st.session_state["page"] = "task_list"
                            safe_rerun()
                        st.stop()
                    else:
                        # 驗證成功，取一筆代表資料
                        if len(matching_vol) > 1:
                            registration_record = matching_vol[matching_vol["id_number"] == 0]
                            if not registration_record.empty:
                                vol_info = registration_record.iloc[0]
                            else:
                                vol_info = matching_vol.iloc[0]
                        else:
                            vol_info = matching_vol.iloc[0]

                        st.session_state["verified_volunteer"] = {
                            "name": str(vol_info.get("name", "")),
                            "phone": verify_phone,
                            "line_id": str(vol_info.get("line_id", ""))
                        }
                        st.success(f"✅ 驗證成功！歡迎 {vol_info.get('name', '志工')}！")
                        safe_rerun()

    # 階段 2: 已驗證身份，進行報名
    else:
        vol_info = st.session_state["verified_volunteer"]
        st.success(f"✅ 已驗證身份：{vol_info['name']} ({vol_info['phone']})")
        st.info("請確認報名資訊")

        # 如果剛剛已經報名成功（顯示成功訊息並提供返回列表按鈕）
        if st.session_state.get("signup_success") and st.session_state.get("signup_task_id") == task_id:
            st.success("🎉 報名成功！感謝您伸出援手 ❤️")
            contact_note = st.session_state.get("signup_contact_note", "")
            if contact_note:
                st.info(contact_note)
            if st.button("🔙 返回任務列表", use_container_width=True, key=f"signup_back_after_{task_id}"):
                # 清理狀態並返回
                for k in ["signup_success", "signup_task_id", "signup_contact_note", "verified_volunteer"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.session_state["page"] = "task_list"
                safe_rerun()
            st.stop()

        # 重新檢查是否已報名此任務
        load_data.clear()
        df_fresh = load_data()

        if df_fresh.empty:
            st.error("無法讀取任務資料，請稍後再試。")
            if st.button("返回任務列表", key="signup_df_empty_return"):
                st.session_state["page"] = "task_list"
                del st.session_state["verified_volunteer"]
                safe_rerun()
            st.stop()

        df_fresh["phone"] = df_fresh["phone"].apply(normalize_phone)

        # 檢查此志工是否已報名此任務（改用 victim.accepted_volunteers）
        already_signed = volunteer_signed_up_for_task(df_fresh, task_id, vol_info["name"], vol_info["phone"])
        
        if already_signed:
            st.error("❌ 您已經報名過此任務，請勿重複報名！")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("返回列表", key=f"signup_already_back_{task_id}"):
                    del st.session_state["verified_volunteer"]
                    st.session_state["page"] = "task_list"
                    safe_rerun()
            with col2:
                if st.button("報名其他任務", key=f"signup_already_other_{task_id}"):
                    del st.session_state["verified_volunteer"]
                    st.session_state["page"] = "task_list"
                    safe_rerun()
            st.stop()

        # 顯示任務資訊
        task_info = df_fresh[(df_fresh["role"] == "victim") & (df_fresh["id_number"] == int(task_id))]
        if not task_info.empty:
            task = task_info.iloc[0]
            st.markdown("### 報名任務資訊")
            st.write(f"**任務名稱：** {task.get('mission_name', '未命名任務')}")
            st.write(f"**地址：** {task.get('address', '')}")
            st.write(f"**工作時間：** {task.get('work_time', '')}")

        # 確認報名按鈕
        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ 確認報名", type="primary", use_container_width=True, key=f"signup_confirm_{task_id}"):

                try:
                    # 嘗試把志工加入任務（包含名額檢查）
                    added = add_volunteer_to_task_on_sheet(df_fresh, task_id, vol_info["name"], vol_info["phone"])
                    if not added:
                        st.error("❌ 您已經報名過此任務，請勿重複報名！")
                        st.stop()

                    # 清除 cache 並更新 session state
                    load_data.clear()
                    st.session_state["user_phone"] = vol_info["phone"]
                    st.session_state["my_new_tasks"].append(int(task_id))

                    # 取得受災戶聯絡資訊（以最新資料為準）
                    load_data.clear()
                    df_after = load_data()
                    victim_rows = df_after[(df_after["role"] == "victim") & (df_after["id_number"] == int(task_id))]
                    victim_name = victim_rows.iloc[0].get("name", "") if not victim_rows.empty else ""
                    victim_phone = normalize_phone(victim_rows.iloc[0].get("phone", "")) if not victim_rows.empty else ""
                    victim_line = victim_rows.iloc[0].get("line_id", "") if not victim_rows.empty else ""
                    victim_note = victim_rows.iloc[0].get("note", "") if not victim_rows.empty else ""

                    # 建立聯絡資訊
                    if victim_name or victim_phone or victim_line or victim_note:
                        contact_note = f"""這是你選擇幫忙的受災戶資料，可以自行連絡他了喔!
受災戶姓名：{victim_name}
電話：{victim_phone}
LineID：{victim_line}
備註：{victim_note}"""
                    else:
                        contact_note = "受災戶聯絡資料：無（目標任務未在 Sheet 找到對應受災戶）。"

                    # 顯示成功訊息（並在同一畫面提供返回按鈕）
                    st.success("🎉 報名成功！感謝您伸出援手 ❤️")
                    st.info(contact_note)

                    # 設定狀態：供後續 render 使用（也保留在 session）
                    st.session_state["signup_success"] = True
                    st.session_state["signup_task_id"] = int(task_id)
                    st.session_state["signup_contact_note"] = contact_note

                    # 立即在同一頁面提供返回按鈕，使用者按下後才會跳回任務列表
                    if st.button("🔙 返回任務列表", key=f"back_after_signup_{task_id}", use_container_width=True):
                        # 清理相關狀態並返回列表
                        for k in ["signup_success", "signup_task_id", "signup_contact_note", "verified_volunteer"]:
                            if k in st.session_state:
                                del st.session_state[k]
                        st.session_state["page"] = "task_list"
                        safe_rerun()

                    # 停在成功視圖，等待使用者按返回
                    st.stop()

                except Exception as e:
                    st.error(f"報名失敗: {e}")
                    st.stop()

        with col2:
            if st.button(" 取消報名", use_container_width=True, key=f"signup_cancel_{task_id}"):
                if "verified_volunteer" in st.session_state:
                    del st.session_state["verified_volunteer"]
                st.session_state["page"] = "task_list"
                safe_rerun()

    st.stop()

# --- 步驟 C: 任務列表頁面 (Task List Page) ---
# 如果不是 signup，顯示任務列表
st.title("災後人力媒合平台（熱心民眾端）")
st.caption("以下為受災戶上傳的最新需求")

# 1. 搜尋過濾
st.subheader(" 篩選條件")

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

# 地址關鍵字搜尋
keyword = st.text_input(" 地址關鍵字搜尋", placeholder="輸入地址關鍵字")

# 搜尋按鈕
search_button = st.button("🔍 開始搜尋", type="primary", use_container_width=False, key="search_btn")

# 反向映射字典（從顯示文字找回原始 key）
time_reverse = {v: k for k, v in time_display.items()}
skills_reverse = {v: k for k, v in skills_display.items()}
resources_reverse = {v: k for k, v in resources_display.items()}
transport_reverse = {v: k for k, v in transport_display.items()}

# 初始化過濾結果
filtered_missions = missions.copy()

# 只有按下搜尋按鈕或有任何選項時才進行過濾
if search_button or selected_times or selected_skills or selected_resources or selected_transports or keyword:
    # 過濾工作時間（OR 邏輯：符合任一選項即可）
    if selected_times:
        time_keys = [time_reverse[t] for t in selected_times]
        time_filter = filtered_missions["work_time"].apply(
            lambda x: any(key in str(x) for key in time_keys)
        )
        filtered_missions = filtered_missions[time_filter]

    # 過濾技能（OR 邏輯：符合任一選項即可）
    if selected_skills:
        skill_keys = [skills_reverse[s] for s in selected_skills]
        skill_filter = filtered_missions["skills"].apply(
            lambda x: any(key in str(x) for key in skill_keys)
        )
        filtered_missions = filtered_missions[skill_filter]

    # 過濾資源（OR 邏輯：符合任一選項即可）
    if selected_resources:
        resource_keys = [resources_reverse[r] for r in selected_resources]
        resource_filter = filtered_missions["resources"].apply(
            lambda x: any(key in str(x) for key in resource_keys)
        )
        filtered_missions = filtered_missions[resource_filter]

    # 過濾交通方式（OR 邏輯：符合任一選項即可）
    if selected_transports:
        transport_keys = [transport_reverse[t] for t in selected_transports]
        transport_filter = filtered_missions["transport"].apply(
            lambda x: any(key in str(x) for key in transport_keys)
        )
        filtered_missions = filtered_missions[transport_filter]

    # 過濾地址關鍵字
    if keyword:
        k = keyword.strip()
        filtered_missions = filtered_missions[
            filtered_missions["address"].str.contains(k, case=False, na=False)
        ]

st.write(f"共 {len(filtered_missions)} 筆需求")
st.markdown("---")

# 2. 預先計算所有任務的「目前人數」 (避免在迴圈內算)
# mission_counts 會使用 volunteers 的 id_number 欄位（load_data 已確保該欄位存在）
mission_counts = volunteers["id_number"].value_counts().to_dict() if not volunteers.empty else {}

# 3. 判斷「當前使用者」的狀態
current_user_phone = st.session_state.get("user_phone")

# 找出使用者在 Sheet 裡報名過的任務 ID（透過 accepted_volunteers）
joined_in_sheet = []
if current_user_phone and not missions.empty:
    # 找出 victim rows where accepted_volunteers contains user's suffix
    suffix = normalize_phone(current_user_phone)[-3:] if current_user_phone else ""
    if suffix:
        for iid, vr in missions.set_index("id_number").iterrows():
            acc = str(vr.get("accepted_volunteers", "") or "")
            if acc and any(suffix in e for e in parse_accepted_volunteers(acc)):
                joined_in_sheet.append(iid)

# 合併「Sheet 裡的舊紀錄」和「剛按下報名的新紀錄」
all_my_joined_tasks = set(joined_in_sheet + st.session_state["my_new_tasks"])
has_joined_any = len(all_my_joined_tasks) > 0 # 是否已經報名過任一項

# 4. 顯示卡片迴圈
for idx, row in filtered_missions.iterrows():
    tid = int(row["id_number"])
    
    # 取得該任務目前人數 (加上使用者剛報名但還沒同步到 sheet 的部分)
    current_count = int(row["selected_worker"])
    if tid in st.session_state["my_new_tasks"] and tid not in joined_in_sheet:
        current_count += 1
        
    left, right = st.columns([2, 1])
    
    with left:
        mission_title = str(row.get("mission_name", "")).strip()
        addr = str(row.get("address", "")).strip()
        if mission_title:
            st.markdown(f"### {mission_title}")
        else:
            if addr:
                st.markdown(f"### 任務地址：{addr}")
            else:
                st.markdown(f"### 任務 #{tid}")
        
        if addr:
            st.markdown(f"地址： {addr}")
        
        time_html = f'<span style="font-weight:600;margin-right:20px"> 工作時間：</span>{render_labels(row["work_time"], time_display, "#FFF8EC")}'
        st.markdown(time_html, unsafe_allow_html=True)

        st.markdown(f" 人數： {current_count} / {row['demand_worker']}")
        
        resources_html = f'<span style="font-weight:600;margin-right:25px"> 提供資源：</span>{render_labels(row["resources"], resources_display, "#FFE3B3")}'
        st.markdown(resources_html, unsafe_allow_html=True)

        skills_html = f'<span style="font-weight:600;margin-right:25px"> 能力需求：</span>{render_labels(row["skills"], skills_display, "#ADEDCC")}'
        st.markdown(skills_html, unsafe_allow_html=True)

        transport_html = f'<span style="font-weight:600;margin-right:25px"> 建議交通方式：</span>{render_labels(row["transport"], transport_display, "#35D0C7")}'
        st.markdown(transport_html, unsafe_allow_html=True)
        
        st.markdown(f" 備註： {row['note']}")

        # 把「已報名志工」移到備註下方顯示（如有）
        acc_text = str(row.get("accepted_volunteers", "")).strip()
        if acc_text:
            st.markdown("**已報名志工：**")
            st.markdown(acc_text.replace("\n", "、"))
            # ✅ 新增：確認聯絡按鈕
    
        if st.button("📞 確認受災戶聯絡資訊", key=f"contact_{tid}"):
            st.session_state["page"] = "check_contact"
            st.session_state["check_contact_task_id"] = tid
            safe_rerun()

        # --- 按鈕邏輯 ---
        is_full = current_count >= row["demand_worker"]
        is_joined_this = tid in all_my_joined_tasks
        
        if is_joined_this:
            st.success("✅ 您已報名此任務")
        elif has_joined_any:
            st.warning("⚠ 您已報名其他任務 (每人限一項)")
        elif is_full:
            st.error("❌ 已額滿")
        else:
            # 按鈕會把 page 切到 signup，並記錄 selected_task_id（確保 key 唯一）
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
            
    st.markdown("<div class='card-spacer'></div>", unsafe_allow_html=True)
