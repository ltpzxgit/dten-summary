import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - DTEN", layout="wide")

st.title("ITOSE Tools - DTEN + TCAP + ProvisioningRequester")

# =========================
# REGEX
# =========================
DATETIME_ID_REGEX = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ([a-f0-9\-]{36})'
REQUEST_ID_REGEX = r'Request ID:\s*([a-f0-9\-]{36})'

PAIR_REGEX = r'"LDCMID":"([A-Za-z0-9\-]+)".*?"StatusReg":"([^"]+)".*?"ResDate":"([^"]+)"'

TCAP_REGEX = r'"deviceId":"([^"]+)".*?"IMEI":"([^"]+)".*?"ICCID":"([^"]+)".*?"IMSI":"([^"]+)".*?"prodStatus":"([^"]+)".*?"prodDate":"([^"]+)".*?"sendDate":"([^"]+)".*?"typeStatus":"([^"]+)"'

# 🔥 FIX: ProvisioningRequester regex ครบ block
AIS_REGEX = r'resourceOrderId":\s*"([^"]+)".*?resourceGroupId":\s*"([^"]+)".*?resourceOrderTimeOut":\s*"([^"]+)".*?resultCode":\s*"([^"]+)".*?resultDesc":\s*"([^"]+)".*?developerMessage":\s*"([^"]*)"'

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

def extract_ais(text):
    return re.findall(AIS_REGEX, text)

def get_carrier(deviceid):
    if deviceid.startswith(("A", "Z")):
        return "AIS"
    elif deviceid == "" or pd.isna(deviceid):
        return "-"
    else:
        return "TRUE"

# =========================
# UPLOAD 3 FILES
# =========================
col1, col2, col3 = st.columns(3)

with col1:
    dten_file = st.file_uploader("📥 DTEN Log", type=["xlsx", "csv"])

with col2:
    tcap_file = st.file_uploader("📥 TCAP Log", type=["xlsx", "csv"])

with col3:
    ais_file = st.file_uploader("📥 ProvisioningRequester Log", type=["xlsx", "csv"])

if dten_file and tcap_file and ais_file:

    df_dten = pd.read_csv(dten_file) if dten_file.name.endswith(".csv") else pd.read_excel(dten_file)
    df_tcap = pd.read_csv(tcap_file) if tcap_file.name.endswith(".csv") else pd.read_excel(tcap_file)
    df_ais = pd.read_csv(ais_file) if ais_file.name.endswith(".csv") else pd.read_excel(ais_file)

    # =========================
    # DTEN
    # =========================
    log_map = {}
    ordered_rows = []

    for col in df_dten.columns:
        for val in df_dten[col]:
            if pd.isna(val):
                continue

            text = str(val)
            corr_id = extract_corr_id(text)

            if not corr_id:
                continue

            if corr_id not in log_map:
                log_map[corr_id] = {
                    "request_id": None,
                    "pairs": []
                }

            req_id = extract_request_id(text)
            if req_id:
                log_map[corr_id]["request_id"] = req_id

            pairs = extract_pairs(text)
            if pairs:
                log_map[corr_id]["pairs"].extend(pairs)

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

    result_df = pd.DataFrame(ordered_rows).drop_duplicates()
    result_df["Carrier"] = result_df["DeviceID"].apply(get_carrier)
    result_df = result_df.reset_index(drop=True)
    result_df.insert(0, "No.", result_df.index + 1)

    # =========================
    # TCAP
    # =========================
    tcap_rows = []

    for col in df_tcap.columns:
        for val in df_tcap[col]:
            if pd.isna(val):
                continue

            for d, imei, iccid, imsi, prod, prod_date, send_date, type_status in extract_tcap(str(val)):
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

    tcap_df = pd.DataFrame(tcap_rows).drop_duplicates()
    tcap_df = tcap_df.reset_index(drop=True)
    tcap_df.insert(0, "No.", tcap_df.index + 1)

    # =========================
    # ProvisioningRequester
    # =========================
    ais_rows = []

    for col in df_ais.columns:
        for val in df_ais[col]:
            if pd.isna(val):
                continue

            text = str(val)
            corr_id = extract_corr_id(text)

            if not corr_id:
                continue

            matches = extract_ais(text)

            for ro_id, d, timeout, code, desc, dev_msg in matches:
                ais_rows.append({
                    "DeviceID": d,
                    "UUID": corr_id,
                    "ResourceOrderId": ro_id,
                    "ResourceOrderTimeOut": timeout,
                    "ResultCode": code,
                    "ResultDesc": desc,
                    "DeveloperMessage": dev_msg if dev_msg else "-"
                })

    ais_df = pd.DataFrame(ais_rows).drop_duplicates()
    ais_df = ais_df.reset_index(drop=True)
    ais_df.insert(0, "No.", ais_df.index + 1)

    # =========================
    # DISPLAY
    # =========================
    st.subheader("📄 DTENLinkage")
    st.dataframe(result_df)

    st.subheader("📄 DTENTCAPLinkage")
    st.dataframe(tcap_df)

    st.subheader("📄 ProvisioningRequester")
    st.dataframe(ais_df)

    st.success(f"✅ DTEN: {len(result_df)} | TCAP: {len(tcap_df)} | Provisioning: {len(ais_df)}")

    # =========================
    # EXPORT
    # =========================
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        result_df.to_excel(writer, index=False, sheet_name='DTENLinkage')
        tcap_df.to_excel(writer, index=False, sheet_name='DTENTCAPLinkage')
        ais_df.to_excel(writer, index=False, sheet_name='ProvisioningRequester')

    output.seek(0)

    st.download_button(
        "📥 Download Excel",
        data=output,
        file_name="full-linkage.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
