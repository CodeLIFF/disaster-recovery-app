import streamlit as st
from supabase import create_client, Client
import uuid  # 產生唯一檔名（避免覆蓋）

# 設定 Supabase
SUPABASE_URL = "https://zktsrpccikfnsqkpuxcc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InprdHNycGNjaWtmbnNxa3B1eGNjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQyNDM1NTAsImV4cCI6MjA3OTgxOTU1MH0.x0h5R5KfmzfCZ8WALDAeEPU36WGgE0Ri-N1JGY6VCcM"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("照片上傳示範（Supabase Storage）")

uploaded_file = st.file_uploader("上傳照片", type=["jpg", "png", "jpeg"])

if uploaded_file:
    # 建立唯一檔名
    file_ext = uploaded_file.name.split(".")[-1]
    file_name = f"{uuid.uuid4()}.{file_ext}"

    # 上傳到 bucket
    res = supabase.storage.from_("photos").upload(
        file_name,
        uploaded_file.getvalue(),
        {"content-type": uploaded_file.type}
    )

    if res:
        # Public URL
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/photos/{file_name}"
        st.success("上傳成功！")
        st.image(public_url)
        st.write("圖片網址：", public_url)
