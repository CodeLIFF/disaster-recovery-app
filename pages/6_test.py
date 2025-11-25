import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ---------- Service Account ----------
creds = Credentials.from_service_account_info(
    st.secrets["google"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ],
)

st.write("Service Account:", creds.service_account_email)

# ---------- Google Sheet 測試 ----------
gc = gspread.authorize(creds)
SHEET_ID = "1PbYajOLCW3p5vsxs958v-eCPgHC1_DnHf9G_mcFx9C0"
try:
    ws = gc.open_by_key(SHEET_ID).worksheet("vol")
    st.success("✅ Sheet 權限正常")
except gspread.exceptions.APIError as e:
    st.error(f"❌ Sheet 權限有問題: {e}")

# ---------- Google Drive 測試 ----------
drive_service = build("drive", "v3", credentials=creds)
DRIVE_PHOTO_FOLDER_ID = "15BiA4lXDXvEPG7fX_GKIhjzhlLdaLiT8"

try:
    # 嘗試列出資料夾中的檔案，確認是否有存取權
    results = drive_service.files().list(
        q=f"'{DRIVE_PHOTO_FOLDER_ID}' in parents",
        pageSize=1,
        fields="files(id, name)"
    ).execute()
    st.success("✅ Drive 權限正常")
except HttpError as e:
    st.error(f"❌ Drive 權限有問題: {e}")
