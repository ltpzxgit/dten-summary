import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - DTEN", layout="wide")

st.title("ITOSE Tools - DTEN Linkage")

# =========================
# REGEX
# =========================
DATETIME_ID_REGEX = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ([a-f0-9\-]{36})'
REQUEST_ID_REGEX = r'Request ID:\s*([a-f0-9\-]{36})'

# DTEN block
PAIR_REGEX = r'"LDCMID":"([A-Za-z0-9\-]+)".*?"StatusReg":"([^"]+)".*?"ResDate":"([^"]+)"'

# TCAP block
TCAP_REGEX = r'"deviceId":"([^"]+)".*?"IMEI":"([^"]+)".*?"ICCID":"([^"]+)".*?"IMSI":"([^"]+)".*?"prodStatus":"([^"]+)".*?"prodDate":"([^"]+)".*?"sendDate":"([^"]+)".*?"typeStatus":"([^"]+)"'


# =========================
# FUNCTIONS
# =========================
def extract_corr_id(text):
    m = re.search(DATETIME_ID_REGEX, text)
    return m.group(1) if m else None

def extract_request_id(text):
    m = re.search(REQUEST_ID_REGEX, text)
    return m.group(1) if m else None

def extract_pairs(text):
    return re.findall(PAIR_REGEX, text)

def extract_tcap(text):
    return re.findall(TCAP_REGEX, text)

def get_carrier(deviceid):
    if deviceid.startswith(("A", "Z")):
        return "AIS"
    elif deviceid == "" or pd.isna(deviceid):
        return "-"
    else:
        return "TRUE"


# =========================
# UPLOAD
# =========================
uploaded_file = st.file_uploader("📥 Upload Excel / CSV", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.write("📊 Preview", df.head())

    # =========================
    # DTEN LOGIC
    # =========================
    log_map = {}
    ordered_rows = []

    # =========================
    # TCAP LOGIC
    # =========================
    tcap_rows = []

    for col in df.columns:
        for val in df[col]:
            if pd.isna(val):
                continue

            text = str(val)

            # ---------- TCAP ----------
            tcap_data = extract_tcap(text)
            for d, imei, iccid, imsi, prod, prod_date, send_date, type_status in tcap_data:
                tcap_rows.append({
                    "DeviceID": d,
                    "IMEI": imei,
                    "ICCID": iccid,
                    "IMSI": imsi,
                    "ProdStatus": prod,
                    "ProdDate": prod_date,
                    "SendDate": send_date,
                    "TypeStatus": type_status
                })

            # ---------- DTEN ----------
            corr_id = extract_corr_id(text)
            if not corr_id:
                continue

            if corr_id not in log_map:
                log_map[corr_id] = {
                    "request_id": None,
                    "pairs": []
                }

            # request id
            req_id = extract_request_id(text)
            if req_id:
                log_map[corr_id]["request_id"] = req_id

            # device + result + datetime
            pairs = extract_pairs(text)
            if pairs:
                log_map[corr_id]["pairs"].extend(pairs)

            # push
            data = log_map[corr_id]
            if data["pairs"] and data["request_id"]:
                for d, status, resdate in data["pairs"]:
                    ordered_rows.append({
                        "DeviceID": d,
                        "Request ID": data["request_id"],
                        "Result": status if status else "-",
                        "Date Time": resdate if resdate else "-"
                    })

                log_map[corr_id]["pairs"] = []

    # =========================
    # DATAFRAME
    # =========================
    result_df = pd.DataFrame(ordered_rows).drop_duplicates()
    result_df["Carrier"] = result_df["DeviceID"].apply(get_carrier)
    result_df = result_df.reset_index(drop=True)
    result_df.insert(0, "No.", result_df.index + 1)

    tcap_df = pd.DataFrame(tcap_rows).drop_duplicates()
    tcap_df = tcap_df.reset_index(drop=True)
    tcap_df.insert(0, "No.", tcap_df.index + 1)

    # =========================
    # DISPLAY
    # =========================
    st.subheader("📄 DTENLinkage")
    st.dataframe(result_df)

    st.subheader("📄 DTENTCAPLinkage")
    st.dataframe(tcap_df)

    st.success(f"✅ DTEN: {len(result_df)} records | TCAP: {len(tcap_df)} records")

    # =========================
    # EXPORT
    # =========================
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        result_df.to_excel(writer, index=False, sheet_name='DTENLinkage')
        tcap_df.to_excel(writer, index=False, sheet_name='DTENTCAPLinkage')

    output.seek(0)

    st.download_button(
        label="📥 Download Excel",
        data=output,
        file_name="dten-full-report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
