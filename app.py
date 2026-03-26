import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - DTEN", layout="wide")

st.title("ITOSE Tools - DTEN Linkage")

# Regex
DATETIME_ID_REGEX = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ([a-f0-9\-]{36})'
LDCMID_REGEX = r'LDCMID=([A-Za-z0-9\-]+)'
REQUEST_ID_REGEX = r'Request ID:\s*([a-f0-9\-]{36})'
PROSTATUS_REGEX = r'ProStatus=([A-Za-z0-9_]+)'

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

uploaded_file = st.file_uploader("📥 Upload Excel / CSV", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.write("📊 Preview", df.head())

    log_map = {}
    ordered_rows = []

    # 🔥 อ่านตามลำดับจริง
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

            # 🔥 ถ้าครบแล้ว → push ทันที (รักษาลำดับ)
            data = log_map[corr_id]
            if data["deviceids"] and data["request_id"]:
                for d in data["deviceids"]:
                    ordered_rows.append({
                        "deviceid": d,
                        "request_id": data["request_id"],
                        "ProStatus": data["prostatus"]
                    })
                # กันซ้ำ
                log_map[corr_id]["deviceids"] = []

    result_df = pd.DataFrame(ordered_rows)

    # ลบซ้ำ (แต่ยังรักษา order)
    result_df = result_df.drop_duplicates()

    # Carrier
    result_df["Carrier"] = result_df["deviceid"].apply(get_carrier)

    # No.
    result_df = result_df.reset_index(drop=True)
    result_df.insert(0, "No.", result_df.index + 1)

    st.success(f"✅ Extracted {len(result_df)} records")

    st.dataframe(result_df)

    # Download
    output = BytesIO()
    result_df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    st.download_button(
        label="📥 Download Excel",
        data=output,
        file_name="dten-summary.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
