import streamlit as st123
import pandas as pd

st.title("受災戶需求表單")

name = st.text_input("請輸入您的姓名（與註冊時相同）")
phone = st.text_input("請輸入您的電話（與註冊時相同）")

# 載入基本資料表
users = pd.read_csv("users.csv")

if st.button("確認身分"):
    # 檢查姓名與電話是否存在
    matched_user = users[(users["姓名"] == name) & (users["電話"] == phone)]
    if len(matched_user) == 0:
        st.error("查無此使用者，請先到基本資料表單註冊。")
    else:
        st.success("身分驗證成功，請填寫您的需求。")

        # 受災戶需求部分
        need = st.multiselect("需求類型", ["鏟土清淤", "物資搬運", "修繕協助", "醫療支援"])
        location = st.text_input("災害地點")
        people = st.number_input("需要人數", 1, 50)
        resources = st.multiselect("可提供資源", ["鏟子", "食物", "住宿", "飲水"])

        if st.button("送出需求"):
            new_request = pd.DataFrame([{
                "姓名": name,
                "電話": phone,
                "需求": ",".join(need),
                "地點": location,
                "人數": people,
                "提供資源": ",".join(resources)
            }])
            new_request.to_csv("requests.csv", mode="a", header=False, index=False)
            st.success("已送出需求，感謝您的回報！")
