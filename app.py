import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - DTEN", layout="wide")

st.title("ITOSE Tools - DTEN Linkage (Compare Mode)")

# =========================
# Regex
# =========================
DATETIME_ID_REGEX = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ([a-f0-9\-]{36})'
LDCMID_REGEX = r'LDCMID=([A-Za-z0-9\-]+)'
REQUEST_ID_REGEX = r'Request ID:\s*([a-f0-9\-]{36})'
PROSTATUS_REGEX = r'ProStatus=([A-Za-z0-9_]+)'


# =========================
# Extract Functions
# =========================
def extract_corr_id(text):
    m = re.search(DATETIME_ID_REGEX, text)
    return m.group(1) if m else None

def extract_ldcmids(text):
    return re.findall(LDCMID_REGEX, text)

def extract_request_id(text):
    m = re.search(REQUEST_ID_REGEX, text)
    return m.group(1) if m else None

def extract_prostatus(text):
    m = re.search(PROSTATUS_REGEX, text)
    return m.group(1) if m else None

def get_carrier(deviceid):
    if deviceid.startswith(("A", "Z")):
        return "AIS"
    elif deviceid == "" or pd.isna(deviceid):
        return "-"
    else:
        return "TRUE"


# =========================
# CORE PARSER (🔥 ใช้ร่วมกันทั้ง 2 ไฟล์)
# =========================
def process_file(df):
    log_map = {}
    ordered_rows = []

    for col in df.columns:
        for val in df[col]:
            if pd.isna(val):
                continue

            text = str(val)
            corr_id = extract_corr_id(text)

            if not corr_id:
                continue

            if corr_id not in log_map:
                log_map[corr_id] = {
                    "deviceids": [],
                    "request_id": None,
                    "prostatus": None
                }

            # device
            ldcmids = extract_ldcmids(text)
            if ldcmids:
                log_map[corr_id]["deviceids"].extend(ldcmids)

            # request id
            req_id = extract_request_id(text)
            if req_id:
                log_map[corr_id]["request_id"] = req_id

            # prostatus
            ps = extract_prostatus(text)
            if ps:
                log_map[corr_id]["prostatus"] = ps

            # push เมื่อครบ
            data = log_map[corr_id]
            if data["deviceids"] and data["request_id"]:
                for d in data["deviceids"]:
                    ordered_rows.append({
                        "DeviceID": d,
                        "RequestID": data["request_id"],
                        "ProStatus": data["prostatus"]
                    })

                log_map[corr_id]["deviceids"] = []

    result_df = pd.DataFrame(ordered_rows)

    # clean + dedupe
    result_df = result_df.drop_duplicates()

    # carrier
    result_df["Carrier"] = result_df["DeviceID"].apply(get_carrier)

    # No.
    result_df = result_df.reset_index(drop=True)
    result_df.insert(0, "No.", result_df.index + 1)

    return result_df


# =========================
# Upload
# =========================
file1 = st.file_uploader("📥 Upload File 1 (System Log)", type=["xlsx", "csv"])
file2 = st.file_uploader("📥 Upload File 2 (TCAP Log)", type=["xlsx", "csv"])


# =========================
# Load Function
# =========================
def load_file(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)


# =========================
# Main
# =========================
if file1 and file2:

    df_raw1 = load_file(file1)
    df_raw2 = load_file(file2)

    st.success("✅ Upload สำเร็จ")

    # =========================
    # Process BOTH FILES
    # =========================
    result_df1 = process_file(df_raw1)
    result_df2 = process_file(df_raw2)

    st.subheader("📄 File1 Result")
    st.dataframe(result_df1, use_container_width=True)

    st.subheader("📄 File2 Result")
    st.dataframe(result_df2, use_container_width=True)

    # =========================
    # Compare
    # =========================
    if st.button("🚀 Compare DeviceID"):

        df1 = result_df1.copy()
        df2 = result_df2.copy()

        # Yes / No
        df1["Sent to TCAP Cloud"] = df1["DeviceID"].isin(df2["DeviceID"]).map({
            True: "Yes",
            False: "No"
        })

        # mismatch
        df_mismatch = df2[~df2["DeviceID"].isin(df1["DeviceID"])].copy()

        # =========================
        # Show
        # =========================
        st.subheader("✅ Sheet1 (Original + Status)")
        st.dataframe(df1, use_container_width=True)

        st.subheader("❌ Sheet2 (Not in System)")
        st.dataframe(df_mismatch, use_container_width=True)

        # =========================
        # Export
        # =========================
        output = BytesIO()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df1.to_excel(writer, sheet_name="Result", index=False)
            df_mismatch.to_excel(writer, sheet_name="Mismatch", index=False)

        st.download_button(
            "📥 Download Excel",
            data=output.getvalue(),
            file_name="dten_compare.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
