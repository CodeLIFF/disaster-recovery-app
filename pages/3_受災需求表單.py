python name=pages/3_受災需求表單.py url=https://github.com/CodeLIFF/disaster-recovery-app/blob/main/pages/3_%E5%8F%97%E7%81%BD%E9%9C%80%E6%B1%82%E8%A1%A8%E5%96%AE.py
# ---------- 以下為「送出，寫回同一列」區塊（請用此區塊完整覆蓋舊有同段程式） ----------
if st.button("✅ 送出今日受災需求 submit"):
    # 以 st.session_state 為來源，避免 NameError（變數在其他區塊未宣告）
    name = st.session_state.get("name", "").strip()
    phone = st.session_state.get("phone", "").strip()
    selected_time_codes = st.session_state.get("selected_time_codes", [])
    uploaded_photo = st.session_state.get("uploaded_photo", None)
    prev_photo = st.session_state.get("prev_photo", None)
    mission_name = st.session_state.get("mission_name", "")
    demand_worker = st.session_state.get("demand_worker", 0)
    note = st.session_state.get("note", "")
    # 驗證步驟
    if not st.session_state.get("victim_verified", False):
        st.error("❌ 請先完成『身分驗證』。")
        st.stop()
    if not st.session_state.get("address_verified", False):
        st.error("❌ 請先完成『地址驗證』。")
        st.stop()

    # 檢查 helper 函式是否存在，若不存在給出清楚的錯誤訊息而不是 NameError
    if "find_victim_row" not in globals() or not callable(find_victim_row):
        st.error("❌ 系統錯誤：找不到函式 find_victim_row。請確認程式有正確載入該函式。")
        st.stop()

    row_number, row_series = find_victim_row(name, phone)
    if row_number is None:
        st.error("❌ 找不到您的基本資料。請重新確認。")
        st.stop()

    if not selected_time_codes:
        st.error("❌ 請至少選擇一個需要協助的時間時段。Choose at least one available time.")
        st.stop()

    # 取得 resources，若 helper 不存在則嘗試從 session_state 拿（較安全）
    if "build_resources_string" in globals() and callable(build_resources_string):
        resources_list = build_resources_string()
    else:
        resources_list = st.session_state.get("resources_list", []) or []
    if not resources_list:
        st.error("❌ 請至少勾選一項『可提供的資源』。Choose at least one available resource.")
        st.stop()

    if "build_skills_string" in globals() and callable(build_skills_string):
        skills_list = build_skills_string()
    else:
        skills_list = st.session_state.get("skills_list", []) or []
    if not skills_list:
        st.error("❌ 請至少勾選一項『希望志工具備的能力』。Choose at least one desired skill.")
        st.stop()

    # --- 處理照片：若有新上傳就用新照片，否則沿用舊的 ---
    if uploaded_photo is None and not prev_photo:
        st.error("❌ 請至少上傳一張地點照片。")
        st.stop()
    elif uploaded_photo is not None:
        # 要上傳新的照片：確認上傳 helper 是否存在
        if "upload_photo_to_supabase" in globals() and callable(upload_photo_to_supabase):
            photo_to_save = upload_photo_to_supabase(uploaded_photo)
            if not photo_to_save:
                st.error("❌ 照片上傳失敗，請稍後再試。")
                st.stop()
        else:
            st.error("❌ 系統錯誤：找不到上傳照片的函式 upload_photo_to_supabase。請聯絡開發人員。")
            st.stop()
    else:
        # 沒有上傳新照片，但原本就有舊照片 → 繼續沿用
        photo_to_save = prev_photo

    # transport 來源同 resources/skills
    if "build_transport_string" in globals() and callable(build_transport_string):
        transport_list = build_transport_string()
    else:
        transport_list = st.session_state.get("transport_list", []) or []
    if not transport_list:
        st.error("❌ 請至少勾選一項『建議交通方式』。Choose at least one suggested transportion.")
        st.stop()

    # 取出原來該列資料為 dict（編輯前的內容）
    # row_series 可能來自 find_victim_row，確保不是 None
    try:
        row = row_series.to_dict() if row_series is not None else {}
    except Exception:
        row = {}

    # ===== 新增：在寫回 Sheet 前，確保 phone 保留前導零（以字串方式寫入） =====
    if "normalize_phone" in globals() and callable(normalize_phone):
        phone_norm = normalize_phone(phone)
    else:
        # 若沒有 normalize_phone，至少保留使用者輸入（不做格式化）
        phone_norm = phone

    if phone_norm:
        # prefix single quote so Google Sheets treats it as text and preserves leading zero
        row["phone"] = "'" + phone_norm
    # 若 phone_norm 為空，則保留原 row 中的 phone 值（不改動）

    address = st.session_state.get("address_value", "").strip()
    mission_to_save = mission_name.strip() if mission_name.strip() else address

    work_time_str = ", ".join(selected_time_codes)
    resources_str = ", ".join(resources_list)
    skills_str = ", ".join(skills_list)
    transport_str = ", ".join(transport_list)

    def update_field(key, new_value):
        # 只在 new_value 有實際內容時才覆寫 row，避免把空值覆蓋掉原有資料
        if new_value not in [None, "", 0]:
            row[key] = new_value

    update_field("mission_name", mission_to_save)
    update_field("address", address)
    update_field("work_time", work_time_str)
    # demand_worker 轉型前先檢查
    try:
        dw = int(demand_worker) if demand_worker not in [None, ""] else None
    except Exception:
        dw = None
    if dw is not None:
        update_field("demand_worker", dw)
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

    # 確認 ws（worksheet）是否存在，避免 NameError
    ws_obj = None
    if "ws" in globals():
        ws_obj = globals().get("ws")
    if not ws_obj:
        # 嘗試從 session_state 拿
        ws_obj = st.session_state.get("ws")
    if not ws_obj:
        st.error("❌ 系統錯誤：找不到 worksheet (ws)。請確認 Google Sheets 的連線物件已正確建立並存放於 ws 或 st.session_state['ws']。")
        st.stop()

    try:
        # A:P 共 16 欄，對應 ordered_cols 的欄位數
        ws_obj.update(f"A{row_number}:P{row_number}", [new_row])
        st.success("✅ 已成功更新您『今天』的受災需求資料！")
        st.info("若明天需求有變化，可以再次進入本表單，只需調整有改變的項目即可。")
    except Exception as e:
        st.error("❌ 更新資料失敗，請稍後再試。")
        st.error(str(e))
# ---------- 區塊結束 ----------
