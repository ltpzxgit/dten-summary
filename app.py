import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - DTEN", layout="wide")

st.title("ITOSE Tools - DTEN Linkage (Block Parser)")

# =========================
# Regex
# =========================
DATETIME_ID_REGEX = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ([a-f0-9\-]{36})'
REQUEST_ID_REGEX = r'Request ID[:\s]+([a-f0-9\-]{36})'

LDCMID_BLOCK_REGEX = r'"LDCMID"\s*:\s*"([^"]+)"'
STATUS_BLOCK_REGEX = r'"StatusReg"\s*:\s*"([^"]+)"'

# =========================
# Extract
# =========================
def extract_corr_id(text):
    m = re.search(DATETIME_ID_REGEX, text)
    return m.group(1) if m else None

def extract_request_id(text):
    m = re.search(REQUEST_ID_REGEX, text)
    return m.group(1) if m else None

def extract_ldcmid(text):
    m = re.search(LDCMID_BLOCK_REGEX, text)
    return m.group(1) if m else None

def extract_status(text):
    m = re.search(STATUS_BLOCK_REGEX, text)
    return m.group(1) if m else None

def get_carrier(deviceid):
    if str(deviceid).startswith(("A", "Z")):
        return "AIS"
    elif deviceid == "" or pd.isna(deviceid):
        return "-"
    else:
        return "TRUE"

# =========================
# CORE (เหมือน repo logic)
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

            # init session
            if corr_id not in log_map:
                log_map[corr_id] = {
                    "request_id": None
                }

            # ✅ copy logic จาก repo
            req_id = extract_request_id(text)
            if req_id:
                log_map[corr_id]["request_id"] = req_id

            current_request = log_map[corr_id]["request_id"]

            # block extract
            ldcmid = extract_ldcmid(text)
            status = extract_status(text)

            if ldcmid:
                ordered_rows.append({
                    "DeviceID": ldcmid.strip(),
                    "RequestID": current_request if current_request else "-",
                    "DTENLinkage Result": status if status else "-"
                })

    if not ordered_rows:
        return pd.DataFrame(columns=["No.", "DeviceID", "RequestID", "Carrier", "DTENLinkage Result"])

    result_df = pd.DataFrame(ordered_rows)

    # clean
    result_df["DeviceID"] = result_df["DeviceID"].astype(str).str.strip()
    result_df["RequestID"] = result_df["RequestID"].astype(str).str.strip()

    # dedupe (เหมือน repo)
    result_df = result_df.drop_duplicates(subset=["DeviceID", "RequestID"])

    # carrier
    result_df["Carrier"] = result_df["DeviceID"].apply(get_carrier)

    # fill
    result_df["DTENLinkage Result"] = result_df["DTENLinkage Result"].fillna("-")

    # No.
    result_df = result_df.reset_index(drop=True)
    result_df.insert(0, "No.", result_df.index + 1)

    # columns
    result_df = result_df[[
        "No.", "DeviceID", "RequestID", "Carrier", "DTENLinkage Result"
    ]]

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
# UI
# =========================
file1 = st.file_uploader("📥 Upload File", type=["xlsx", "csv"])

if file1:

    df_raw = load_file(file1)

    st.success("✅ Upload สำเร็จ")

    with st.expander("🔍 Debug Preview"):
        st.write(df_raw.head())

    result_df = process_file(df_raw)

    st.subheader("📄 DTENLinkage Result")
    st.dataframe(result_df, use_container_width=True)

    # export
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        result_df.to_excel(writer, sheet_name="DTENLinkage", index=False)

    st.download_button(
        label="📥 Download Excel",
        data=output.getvalue(),
        file_name="dten_block_extract.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
