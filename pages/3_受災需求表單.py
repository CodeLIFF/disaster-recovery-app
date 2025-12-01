# ---------- 以下為「送出，寫回同一列」區塊（請用此區塊完整覆蓋舊有同段程式） ----------
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
        # 使用者有上傳新的照片 → 上傳到 Supabase，取得網址
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

    # 取出原來該列資料為 dict（編輯前的內容）
    row = row_series.to_dict()

    # ===== 新增：在寫回 Sheet 前，確保 phone 保留前導零（以字串方式寫入） =====
    phone_norm = normalize_phone(phone)
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
        # A:P 共 16 欄，對應 ordered_cols 的欄位數
        ws.update(f"A{row_number}:P{row_number}", [new_row])
        st.success("✅ 已成功更新您『今天』的受災需求資料！")
        st.info("若明天需求有變化，可以再次進入本表單，只需調整有改變的項目即可。")
    except Exception as e:
        st.error("❌ 更新資料失敗，請稍後再試。")
        st.error(str(e))
# ---------- 區塊結束 ----------
