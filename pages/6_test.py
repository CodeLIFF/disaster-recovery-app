import streamlit as st
import io
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError

# ---------- Service Account ----------
creds = Credentials.from_service_account_info(
    st.secrets["google"],
    scopes=[
        "https://www.googleapis.com/auth/drive",
    ],
)

st.write("Service Account:", creds.service_account_email)

# ---------- Google Drive ----------
drive_service = build("drive", "v3", credentials=creds)
DRIVE_PHOTO_FOLDER_ID = "15BiA4lXDXvEPG7fX_GKIhjzhlLdaLiT8"

# ---------- 檢查 Drive 權限 ----------
try:
    test_files = drive_service.files().list(
        q=f"'{DRIVE_PHOTO_FOLDER_ID}' in parents",
        pageSize=1,
        fields="files(id, name)"
    ).execute()
    st.success("✅ Google Drive 權限正常")
except HttpError as e:
    st.error(f"❌ Google Drive 權限有問題: {e}")

# ---------- 上傳檔案 ----------
uploaded_file = st.file_uploader("選擇要上傳的檔案", type=["png", "jpg", "jpeg", "pdf"])

def upload_photo_to_drive(uploaded_file):
    if uploaded_file is None:
        return None
    try:
        uploaded_file.seek(0)
        file_bytes = uploaded_file.read()
        file_stream = io.BytesIO(file_bytes)

        media = MediaIoBaseUpload(
            file_stream,
            mimetype=uploaded_file.type,
            resumable=False,
        )

        file_metadata = {
            "name": uploaded_file.name,
            "parents": [DRIVE_PHOTO_FOLDER_ID],
        }

        drive_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()

        file_id = drive_file["id"]
        return f"https://drive.google.com/uc?id={file_id}"

    except Exception as e:
        st.error(f"上傳檔案到 Google Drive 失敗: {e}")
        return None

if st.button("上傳到 Google Drive"):
    if uploaded_file is None:
        st.warning("請先選擇檔案")
    else:
        link = upload_photo_to_drive(uploaded_file)
        if link:
            st.success("✅ 檔案上傳成功！")
            st.write(f"🔗 Google Drive 連結: {link}")
