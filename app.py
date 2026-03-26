import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - DTEN", layout="wide")

st.title("ITOSE Tools - DTEN + TCAP + Provisioning")

# =========================
# REGEX
# =========================
DATETIME_ID_REGEX = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ([a-f0-9\-]{36})'
REQUEST_ID_REGEX = r'Request ID:\s*([a-f0-9\-]{36})'

# DTEN
PAIR_REGEX = r'"LDCMID":"([A-Za-z0-9\-]+)".*?"StatusReg":"([^"]+)".*?"ResDate":"([^"]+)"'

# TCAP
TCAP_REGEX = r'"deviceId":"([^"]+)".*?"IMEI":"([^"]+)".*?"ICCID":"([^"]+)".*?"IMSI":"([^"]+)".*?"prodStatus":"([^"]+)".*?"prodDate":"([^"]+)".*?"sendDate":"([^"]+)".*?"typeStatus":"([^"]+)"'

# ProvisioningRequester (multi-line)
AIS_REGEX = r'resourceOrderId":\s*"([^"]+)".*?resourceGroupId":\s*"([^"]+)".*?resourceOrderTimeOut":\s*"([^"]+)".*?resultCode":\s*"([^"]+)".*?resultDesc":\s*"([^"]+)".*?developerMessage":\s*"([^"]*)"'

# ProvisioningResponder (single-line)
RESPONDER_REGEX = r'resourceOrderId":"([^"]+)".*?resourceGroupId":"([^"]+)".*?resultCode":"([^"]+)".*?resultDesc":"([^"]+)".*?developerMessage":"([^"]*)"'

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
    return re.findall(AIS_REGEX, text, re.DOTALL)

def extract_responder(text):
    return re.findall(RESPONDER_REGEX, text)

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
col1, col2, col3 = st.columns(3)

with col1:
    dten_file = st.file_uploader("📥 DTEN Log", type=["xlsx", "csv"])

with col2:
    tcap_file = st.file_uploader("📥 TCAP Log", type=["xlsx", "csv"])

with col3:
    prov_file = st.file_uploader("📥 Provisioning Log", type=["xlsx", "csv"])

if dten_file and tcap_file and prov_file:

    df_dten = pd.read_csv(dten_file) if dten_file.name.endswith(".csv") else pd.read_excel(dten_file)
    df_tcap = pd.read_csv(tcap_file) if tcap_file.name.endswith(".csv") else pd.read_excel(tcap_file)
    df_prov = pd.read_csv(prov_file) if prov_file.name.endswith(".csv") else pd.read_excel(prov_file)

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
                log_map[corr_id] = {"request_id": None, "pairs": []}

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
                        "Result": status,
                        "Date Time": resdate
                    })
                log_map[corr_id]["pairs"] = []

    result_df = pd.DataFrame(ordered_rows).drop_duplicates()
    result_df["Carrier"] = result_df["DeviceID"].apply(get_carrier)

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

    # =========================
    # ProvisioningRequester
    # =========================
    req_rows = []

    # =========================
    # ProvisioningResponder
    # =========================
    res_rows = []

    for col in df_prov.columns:
        for val in df_prov[col]:
            if pd.isna(val):
                continue

            text = str(val)
            corr_id = extract_corr_id(text)

            if not corr_id:
                continue

            # requester (multi-line)
            for ro_id, d, timeout, code, desc, dev_msg in extract_ais(text):
                req_rows.append({
                    "DeviceID": d,
                    "UUID": corr_id,
                    "ResourceOrderId": ro_id,
                    "ResourceOrderTimeOut": timeout,
                    "ResultCode": code,
                    "ResultDesc": desc,
                    "DeveloperMessage": dev_msg if dev_msg else "-"
                })

            # responder (single-line)
            for ro_id, d, code, desc, dev_msg in extract_responder(text):
                res_rows.append({
                    "DeviceID": d,
                    "UUID": corr_id,
                    "ResourceOrderId": ro_id,
                    "ResultCode": code,
                    "ResultDesc": desc,
                    "DeveloperMessage": dev_msg if dev_msg else "-"
                })

    req_df = pd.DataFrame(req_rows).drop_duplicates()
    res_df = pd.DataFrame(res_rows).drop_duplicates()

    # =========================
    # DISPLAY
    # =========================
    st.subheader("DTENLinkage")
    st.dataframe(result_df)

    st.subheader("DTENTCAPLinkage")
    st.dataframe(tcap_df)

    st.subheader("ProvisioningRequester")
    st.dataframe(req_df)

    st.subheader("ProvisioningResponder")
    st.dataframe(res_df)

    st.success(f"DTEN:{len(result_df)} | TCAP:{len(tcap_df)} | Req:{len(req_df)} | Res:{len(res_df)}")

    # =========================
    # EXPORT
    # =========================
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        result_df.to_excel(writer, index=False, sheet_name='DTENLinkage')
        tcap_df.to_excel(writer, index=False, sheet_name='DTENTCAPLinkage')
        req_df.to_excel(writer, index=False, sheet_name='ProvisioningRequester')
        res_df.to_excel(writer, index=False, sheet_name='ProvisioningResponder')

    output.seek(0)

    st.download_button(
        "📥 Download Excel",
        data=output,
        file_name="full-linkage.xlsx"
    )
