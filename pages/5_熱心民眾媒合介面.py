import streamlit as st
import pandas as pd
import os

st.title("志工媒合平台")

CSV_PATH = "tasks.csv"

# 讀取 CSV
def load_data():
    if not os.path.exists(CSV_PATH):
        return pd.DataFrame(columns=[
            "id", "address", "work_time",
            "need_people", "selected_people",
            "skills", "resources",
            "photo_url", "transport",
            "note", "contact", "created_at"
        ])
    return pd.read_csv(CSV_PATH)

# 儲存 CSV
def save_data(df):
    df.to_csv(CSV_PATH, index=False)

# =============================
# 讀取資料
# =============================
df = load_data()

# 上傳資料
uploaded_file = st.file_uploader("上傳受災戶需求 CSV 檔案", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    save_data(df)
    st.success("CSV 上傳成功並已儲存！")

# 空資料處理
if df.empty:
    st.info("目前沒有任務可顯示，請上傳 CSV。")
    st.stop()

# =============================
# 搜尋 + 排序
# =============================
keyword = st.text_input("搜尋任務（技能、地址、備註…）")
sort_option = st.selectbox("排序方式", ["最新優先", "缺人最多"])

# 搜尋
if keyword:
    df = df[df.apply(lambda row: keyword.lower() in str(row).lower(), axis=1)]

# 排序
if sort_option == "最新優先":
    df = df.sort_values("id", ascending=False)
else:
    df["缺口"] = df["need_people"] - df["selected_people"]
    df = df.sort_values("缺口", ascending=False)

# 初始化 session_state
if "accepted_task" not in st.session_state:
    st.session_state.accepted_task = None

# =============================
# 任務列表
# =============================
st.subheader("任務列表")

for idx, row in df.iterrows():

    with st.container():
        st.subheader("用戶需求")

        st.write(f"📍 地點：{row['address']}")
        st.write(f"🕒 時間：{row['work_time']}")
        st.write(f"👥 需求人數：{row['need_people']}")
        st.write(f"🎯 已選志工：{row['selected_people']}")
        st.write(f"🔧 技能：{row['skills']}")
        st.write(f"🔨 物資：{row['resources']}")
        st.write(f"🚌 交通方式：{row['transport']}")
        st.write(f"📝 備註：{row['note']}")

        if isinstance(row["photo_url"], str) and row["photo_url"].strip() != "":
            st.image(row["photo_url"], use_container_width=True)

        # 按下按鈕 → 接取任務
        if st.button("確定接取", key=f"accept_{idx}"):
            st.session_state.accepted_task = row["id"]
            

        st.write("---")


# =============================
# 顯示接取結果 + 更新資料
# =============================

if st.session_state.accepted_task is not None:

    task_id = st.session_state.accepted_task

    task = df[df["id"] == task_id].iloc[0]

    st.success("🎉 你已成功接取此任務！")
    st.info(f"📞 受災戶聯絡資訊：{task['contact']}")

    # 更新該任務 selected_people +1
    df.loc[df["id"] == task_id, "selected_people"] += 1

    # 儲存變更到 CSV
    save_data(df)

    # 顯示更新後的人數
    updated = df[df["id"] == task_id].iloc[0]
    st.write(f"🎯 更新後已選志工：{updated['selected_people']} 人")

    # 清除狀態（避免重新載入時重複顯示）
    st.session_state.accepted_task = None
