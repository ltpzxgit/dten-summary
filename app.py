import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - DTEN", layout="wide")

st.title("ITOSE Tools - DTEN Linkage")

# Regex
REQUEST_ID_REGEX = r'Request ID:\s*([a-f0-9\-]{36})'
PROSTATUS_REGEX = r'ProStatus=([A-Za-z0-9_]+)'
PAIR_REGEX = r'"LDCMID":"([A-Za-z0-9\-]+)".*?"StatusReg":"([^"]+)"'  # 🔥 ตัวหลัก

def extract_request_id(text):
    m = re.search(REQUEST_ID_REGEX, text)
    return m.group(1) if m else None

def extract_prostatus(text):
    m = re.search(PROSTATUS_REGEX, text)
    return m.group(1) if m else None

def extract_pairs(text):
    return re.findall(PAIR_REGEX, text)

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

    ordered_rows = []

    current_request_id = None
    current_prostatus = None

    for col in df.columns:
        for val in df[col]:
            if pd.isna(val):
                continue

            text = str(val)

            # update context
            req_id = extract_request_id(text)
            if req_id:
                current_request_id = req_id

            ps = extract_prostatus(text)
            if ps:
                current_prostatus = ps

            # 🔥 extract block
            pairs = extract_pairs(text)

            for d, status in pairs:
                ordered_rows.append({
                    "deviceid": d,
                    "request_id": current_request_id,
                    "ProStatus": current_prostatus,
                    "Result": status if status else "-"
                })

    result_df = pd.DataFrame(ordered_rows).drop_duplicates()

    result_df["Carrier"] = result_df["deviceid"].apply(get_carrier)

    result_df = result_df.reset_index(drop=True)
    result_df.insert(0, "No.", result_df.index + 1)

    st.success(f"✅ Extracted {len(result_df)} records")

    st.dataframe(result_df)

    output = BytesIO()
    result_df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    st.download_button(
        label="📥 Download Excel",
        data=output,
        file_name="dten-summary.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
