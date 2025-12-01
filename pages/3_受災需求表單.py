# (檔頭與前半部與你現有相同，以下只貼出變更重點區段以便閱讀——實際請將整個檔案替換或依此修改)
...
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
...
    try:
        ws.update(f"A{row_number}:P{row_number}", [new_row])
        st.success("✅ 已成功更新您『今天』的受災需求資料！")
...
