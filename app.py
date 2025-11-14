import streamlit as st

st.set_page_config(
    page_title="災害需求管理系統",
    page_icon="🌏",
    layout="wide",
    initial_sidebar_state="expanded",  # 一打開就展開 sidebar
)

st.title("🌏 災害需求管理系統（首頁）")
st.write("請從左側選單選擇功能頁面。")
st.info("系統包含：基本說明、基本資料表單、受災需求表單。")

