import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - DTEN", layout="wide")

st.title("ITOSE Tools - DTEN Linkage (Dual Extract)")

# =========================
# Regex
# =========================
DATETIME_ID_REGEX = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ([a-f0-9\-]{36})'
LDCMID_REGEX = r'(?:LDCMID|deviceId)[=:"\s]+([A-Za-z0-9\-]+)'
REQUEST_ID_REGEX = r'Request ID[:\s]+([a-f0-9\-]{36})'
PROSTATUS_REGEX = r'ProStatus[=:\s]+([A-Za-z0-9_]+)'

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
    if str(deviceid).startswith(("A", "Z")):
        return "AIS"
    elif deviceid == "" or pd.isna(deviceid):
        return "-"
    else:
        return "TRUE"

# =========================
# CORE PARSER
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

            # push
            data = log_map[corr_id]
            if data["deviceids"] and data["request_id"]:
                for d in data["deviceids"]:
                    ordered_rows.append({
                        "DeviceID": str(d).strip(),
                        "RequestID": str(data["request_id"]).strip(),
                        "ProStatus": data["prostatus"]
                    })

                log_map[corr_id]["deviceids"] = []

    # กัน empty
    if not ordered_rows:
        return pd.DataFrame(columns=["No.", "DeviceID", "RequestID", "ProStatus", "Carrier"])

    result_df = pd.DataFrame(ordered_rows)

    # 🔥 clean ก่อน dedupe
    result_df["DeviceID"] = result_df["DeviceID"].astype(str).str.strip()
    result_df["RequestID"] = result_df["RequestID"].astype(str).str.strip()

    # 🔥 กันเบิ้ลจริง (ใช้ key หลัก)
    result_df = result_df.drop_duplicates(subset=["DeviceID", "RequestID"])

    # carrier
    result_df["Carrier"] = result_df["DeviceID"].apply(get_carrier)

    # No.
    result_df = result_df.reset_index(drop=True)
    result_df.insert(0, "No.", result_df.index + 1)

    return result_df


# =========================
# Load File
# =========================
def load_file(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)


# =========================
# Upload
# =========================
file1 = st.file_uploader("📥 Upload File 1", type=["xlsx", "csv"])
file2 = st.file_uploader("📥 Upload File 2", type=["xlsx", "csv"])


# =========================
# Main
# =========================
if file1 and file2:

    df_raw1 = load_file(file1)
    df_raw2 = load_file(file2)

    st.success("✅ Upload สำเร็จ")

    with st.expander("🔍 Debug Preview"):
        st.write("File1 sample", df_raw1.head())
        st.write("File2 sample", df_raw2.head())

    # Process
    result_df1 = process_file(df_raw1)
    result_df2 = process_file(df_raw2)

    # =========================
    # Show
    # =========================
    st.subheader("📄 Sheet1 (DTENLinkage)")
    st.dataframe(result_df1, use_container_width=True)

    st.subheader("📄 Sheet2 (DTENTCAPLinkage)")
    st.dataframe(result_df2[["No.", "DeviceID", "RequestID"]], use_container_width=True)

    # =========================
    # Export
    # =========================
    output = BytesIO()

    # 👉 ตัด column Sheet2
    result_df2_export = result_df2[["No.", "DeviceID", "RequestID"]].copy()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        result_df1.to_excel(writer, sheet_name="DTENLinkage", index=False)
        result_df2_export.to_excel(writer, sheet_name="DTENTCAPLinkage", index=False)

    st.download_button(
        label="📥 Download Excel (2 Sheets)",
        data=output.getvalue(),
        file_name="dten_dual_extract.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
