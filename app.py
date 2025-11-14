import streamlit as st

st.set_page_config(
    page_title="災害需求管理系統",
    page_icon="🌏",
    layout="wide"
)

st.sidebar.title("頁面選單")
st.sidebar.page_link("app.py", label="🏠 首頁")
st.sidebar.page_link("pages/1_基本說明.py", label="📘 基本說明")
st.sidebar.page_link("pages/2_基本資料表單.py", label="👤 基本資料表單")
st.sidebar.page_link("pages/3_受災需求表單.py", label="🆘 受災需求表單")

st.title("🌏 災害需求管理系統（首頁）")
st.write("請從左側選單選擇功能頁面。")
st.info("系統包含：基本說明、基本資料表單、受災需求表單。")
