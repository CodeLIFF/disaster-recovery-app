import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="災害需求管理系統",
    page_icon="🌏",
    layout="wide",
)

# --------- 定義每個「頁面」的內容 --------- #

def page_home():
    st.title("🌏 災害需求管理系統（首頁）")
    st.write("請從左側選單選擇功能頁面。")
    st.info("系統包含：基本說明、基本資料表單、受災需求表單。")

def page_basic_info():
    st.title("👤 基本資料表單")

    st.write("請填寫您的基本資料。")

    with st.form("basic_info_form"):
        name = st.text_input("姓名")
        phone = st.text_input("電話")
        id_no = st.text_input("身分證字號（可選填）")
        address = st.text_input("通訊地址 / 安置地點")
        family_num = st.number_input("同住家人口數", min_value=1, step=1)

        submitted = st.form_submit_button("送出")

    if submitted:
        st.success("基本資料已送出，感謝填寫！")
        st.write("### 您填寫的資料：")
        st.write(f"- 姓名：{name}")
        st.write(f"- 電話：{phone}")
        st.write(f"- 身分證字號：{id_no}")
        st.write(f"- 通訊地址 / 安置地點：{address}")
        st.write(f"- 同住家人口數：{family_num}")

def page_needs():
    st.title("🆘 受災需求表單")

    st.write("請填寫目前的受災狀況與具體需求。")

    with st.form("disaster_needs_form"):
        name = st.text_input("姓名")
        phone = st.text_input("電話")
        location = st.text_input("所在位置（縣市、鄉鎮、市區或收容所名稱）")

        st.write("### 目前狀況")
        has_injury = st.radio("家中是否有人受傷？", ["否", "是"], index=0)
        has_trapped = st.radio("是否有人受困無法移動？", ["否", "是"], index=0)

        st.write("### 具體需求（可複選）")
        need_food = st.checkbox("食物")
        need_water = st.checkbox("飲用水")
        need_med = st.checkbox("藥品 / 醫療協助")
        need_clothes = st.checkbox("衣物 / 保暖用品")
        need_shelter = st.checkbox("安置 / 住宿協助")
        other_need = st.text_area("其他需求（請簡要說明）")

        submitted = st.form_submit_button("送出")

    if submitted:
        st.success("受災需求已送出，感謝回報！")
        st.write("### 您回報的資料：")
        st.write(f"- 姓名：{name}")
        st.write(f"- 電話：{phone}")
        st.write(f"- 所在位置：{location}")
        st.write(f"- 是否有人受傷：{has_injury}")
        st.write(f"- 是否有人受困：{has_trapped}")

        needs = []
        if need_food: needs.append("食物")
        if need_water: needs.append("飲用水")
        if need_med: needs.append("藥品 / 醫療協助")
        if need_clothes: needs.append("衣物 / 保暖用品")
        if need_shelter: needs.append("安置 / 住宿協助")

        st.write(f"- 主要需求項目：{', '.join(needs) if needs else '未勾選'}")
        st.write(f"- 其他需求說明：{other_need if other_need else '無'}")


# --------- 左側 sidebar 選單（手動「多頁」）--------- #

st.sidebar.title("頁面選單")

page = st.sidebar.radio(
    "請選擇頁面：",
    (
        "首頁",
        "系統基本說明",
        "基本資料表單",
        "受災需求表單",
    )
)

if page == "首頁":
    page_home()
elif page == "基本資料表單":
    page_basic_info()
elif page == "受災需求表單":
    page_needs()

