import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="DeviceID Compare Tool", layout="wide")

st.title("🔍 DeviceID Compare Tool (Advanced)")

# =========================
# Upload
# =========================
file1 = st.file_uploader("📥 Upload Log / File 1 (System)", type=["txt", "csv", "xlsx"])
file2 = st.file_uploader("📥 Upload File 2 (TCAP Cloud)", type=["xlsx", "csv"])


# =========================
# Regex Extract DeviceID
# =========================
DEVICE_REGEX = r'"deviceId"\s*:\s*"([^"]+)"'


def extract_device_from_text(file):
    text = file.read().decode("utf-8", errors="ignore")
    matches = re.findall(DEVICE_REGEX, text)

    df = pd.DataFrame(matches, columns=["DeviceID"])
    return df


def load_file(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)


def clean(series):
    return series.astype(str).str.strip()


# =========================
# Main
# =========================
if file1 and file2:

    # =========================
    # STEP 1: Extract DeviceID จาก File1
    # =========================
    if file1.name.endswith(".txt"):
        df1 = extract_device_from_text(file1)

    else:
        df1 = load_file(file1)
        df1.columns = df1.columns.str.strip()

        # ให้ user เลือก column ถ้าไม่ใช่ log
        device_col1 = st.selectbox("เลือก DeviceID column (File1)", df1.columns)
        df1 = df1[[device_col1]].rename(columns={device_col1: "DeviceID"})

    # remove duplicate
    df1["DeviceID"] = clean(df1["DeviceID"])
    df1 = df1.drop_duplicates().reset_index(drop=True)

    # =========================
    # STEP 2: Load File2
    # =========================
    df2 = load_file(file2)
    df2.columns = df2.columns.str.strip()

    device_col2 = st.selectbox("เลือก DeviceID column (File2)", df2.columns)
    df2["DeviceID"] = clean(df2[device_col2])

    df2 = df2[["DeviceID"]].drop_duplicates()

    st.success("✅ Extract + Load สำเร็จ")

    # =========================
    # STEP 3: Compare
    # =========================
    if st.button("🚀 Start Compare"):

        # Sheet1 (เหมือนต้นแบบ + เพิ่ม column)
        df_result = df1.copy()

        df_result["Sent to TCAP Cloud"] = df_result["DeviceID"].isin(df2["DeviceID"]).map({
            True: "Yes",
            False: "No"
        })

        # Sheet2 mismatch
        df_mismatch = df2[~df2["DeviceID"].isin(df1["DeviceID"])].copy()

        # =========================
        # Metrics
        # =========================
        col1, col2, col3 = st.columns(3)

        col1.metric("Total DeviceID (File1)", len(df_result))
        col2.metric("Matched", (df_result["Sent to TCAP Cloud"] == "Yes").sum())
        col3.metric("Not Match (File2)", len(df_mismatch))

        st.divider()

        # =========================
        # Display
        # =========================
        st.subheader("📄 Sheet1 (Original Format + Status)")
        st.dataframe(df_result, use_container_width=True)

        st.subheader("❌ Sheet2 (Not in System)")
        st.dataframe(df_mismatch, use_container_width=True)

        # =========================
        # Export
        # =========================
        output = BytesIO()

        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df_result.to_excel(writer, sheet_name="Result", index=False)
            df_mismatch.to_excel(writer, sheet_name="Mismatch", index=False)

        st.download_button(
            "📥 Download Excel",
            data=output.getvalue(),
            file_name="device_compare.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
