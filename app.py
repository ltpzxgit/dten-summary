import streamlit as st
import pandas as pd
import re
import json
from io import BytesIO

st.set_page_config(page_title="ITOSE - DTEN", layout="wide")
st.title("ITOSE Tools - DTEN Summary")

# =========================
# CSS (🔥 UPGRADED STYLE)
# =========================
st.markdown("""
<style>

/* ===== GLOBAL ===== */
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

/* ===== CARD BASE ===== */
.card {
    padding: 24px;
    border-radius: 18px;
    background: linear-gradient(145deg, #0f172a, #020617);
    border: 1px solid rgba(148, 163, 184, 0.2);
    text-align: center;
    margin-bottom: 16px;
    transition: all 0.25s ease;
    box-shadow: 0 6px 20px rgba(0,0,0,0.35);
}

.card:hover {
    transform: translateY(-3px);
    border: 1px solid rgba(148, 163, 184, 0.4);
    box-shadow: 0 10px 28px rgba(0,0,0,0.55);
}

/* ===== RED CARD ===== */
.card-red {
    padding: 24px;
    border-radius: 18px;
    background: linear-gradient(145deg, #3b0a0a, #1a0f0f);
    border: 1px solid rgba(239, 68, 68, 0.5);
    text-align: center;
    margin-bottom: 16px;
    transition: all 0.25s ease;
    box-shadow: 0 6px 20px rgba(0,0,0,0.35);
}

.card-red:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 28px rgba(0,0,0,0.55);
}

/* ===== TITLE ===== */
.card-title {
    font-size: 15px;
    color: #9ca3af;
    margin-bottom: 8px;
    letter-spacing: 0.3px;
}

/* ===== VALUE ===== */
.card-value {
    font-size: 52px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 1px;
}

/* ===== FIX COLUMN GAP ===== */
div[data-testid="column"] > div {
    margin-bottom: 10px;
}

/* ===== SUMMARY TITLE ===== */
h2 {
    margin-bottom: 20px !important;
}

</style>
""", unsafe_allow_html=True)

# =========================
# REGEX
# =========================
DATETIME_ID_REGEX = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ([a-f0-9\-]{36})'
REQUEST_ID_REGEX = r'Request ID:\s*([a-f0-9\-]{36})'

PAIR_REGEX = r'"LDCMID":"([A-Za-z0-9\-]+)".*?"StatusReg":"([^"]+)".*?"ResDate":"([^"]+)"'
TCAP_REGEX = r'"deviceId":"([^"]+)".*?"IMEI":"([^"]+)".*?"ICCID":"([^"]+)".*?"IMSI":"([^"]+)".*?"prodStatus":"([^"]+)".*?"prodDate":"([^"]+)".*?"sendDate":"([^"]+)".*?"typeStatus":"([^"]+)"'
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
    return re.findall(AIS_REGEX, text, re.DOTALL)

def get_carrier(deviceid):
    if isinstance(deviceid, str) and deviceid.startswith(("A", "Z")):
        return "AIS"
    return "TRUE"

# =========================
# CARD
# =========================
def card(title, total, is_error=False):
    card_class = "card-red" if is_error else "card"
    return f"""
    <div class="{card_class}">
        <div class="card-title">{title}</div>
        <div class="card-value">{total}</div>
    </div>
    """

# =========================
# HIGHLIGHT
# =========================
def highlight_error_dten(row):
    return ['background-color: #ffcccc' if row["Result"] != "Process completed successfully" else '' for _ in row]

def highlight_error_tcap(row):
    return ['background-color: #ffcccc' if row["TypeStatus"] != "OK" else '' for _ in row]

def highlight_error_req(row):
    return ['background-color: #ffcccc' if row["ResultCode"] != "20000" else '' for _ in row]

def highlight_error_res(row):
    return ['background-color: #ffcccc' if row["ResultCode"] != "20000" else '' for _ in row]

# =========================
# UPLOAD
# =========================
col1, col2, col3, col4 = st.columns(4)

with col1:
    dten_file = st.file_uploader("DTEN", type=["xlsx", "csv"])
with col2:
    tcap_file = st.file_uploader("DTENTCAP", type=["xlsx", "csv"])
with col3:
    req_file = st.file_uploader("ProvisioningRequester", type=["xlsx", "csv"])
with col4:
    res_file = st.file_uploader("ProvisioningResponder", type=["xlsx", "csv"])

# =========================
# INIT
# =========================
dten_total = dten_error = 0
tcap_total = tcap_error = 0
req_total = req_error = 0
res_total = res_error = 0

true_total = 0
ais_total = 0

df1 = df2 = df3 = df4 = pd.DataFrame()
df7 = pd.DataFrame()
df8 = pd.DataFrame()
df_summary = pd.DataFrame()

# =========================
# SUMMARY UI
# =========================
summary_placeholder = st.empty()

def render_summary():
    with summary_placeholder.container():
        st.markdown("## DTEN - Summary")

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.markdown(card("DTEN", dten_total, dten_error > 0), unsafe_allow_html=True)
        with c2:
            st.markdown(card("DTENTCAP", tcap_total, tcap_error > 0), unsafe_allow_html=True)
        with c3:
            st.markdown(card("ProvisioningRequester", req_total, req_error > 0), unsafe_allow_html=True)
        with c4:
            st.markdown(card("ProvisioningResponder", res_total, res_error > 0), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        c5, c6, c7, c8 = st.columns(4)

        with c5:
            st.markdown(card("TRUE", true_total, False), unsafe_allow_html=True)
        with c6:
            st.markdown(card("AIS", ais_total, False), unsafe_allow_html=True)
        with c7:
            st.markdown(card("Requester Error", len(df7), len(df7) > 0), unsafe_allow_html=True)
        with c8:
            st.markdown(card("Responder Error", len(df8), len(df8) > 0), unsafe_allow_html=True)

render_summary()

# =========================
# DTEN
# =========================
if dten_file:
    df_dten = pd.read_csv(dten_file) if dten_file.name.endswith(".csv") else pd.read_excel(dten_file)

    log_map = {}
    rows = []

    for col in df_dten.columns:
        for val in df_dten[col]:
            if pd.isna(val): continue

            text = str(val)
            cid = extract_corr_id(text)
            if not cid: continue

            log_map.setdefault(cid, {"req": None, "pairs": []})

            rid = extract_request_id(text)
            if rid:
                log_map[cid]["req"] = rid

            pairs = extract_pairs(text)
            if pairs:
                log_map[cid]["pairs"].extend(pairs)

            data = log_map[cid]
            if data["pairs"] and data["req"]:
                for d, s, dt in data["pairs"]:
                    rows.append({
                        "DeviceID": d,
                        "Request ID": data["req"],
                        "Result": s,
                        "Date Time": dt
                    })
                log_map[cid]["pairs"] = []

    df1 = pd.DataFrame(rows).drop_duplicates(subset=["DeviceID","Request ID","Date Time"])
    df1["Result"] = df1["Result"].astype(str).str.strip()
    df1["Carrier"] = df1["DeviceID"].apply(get_carrier)

    dten_total = len(df1)
    dten_error = len(df1[df1["Result"] != "Process completed successfully"])

    true_total = len(df1[df1["Carrier"] == "TRUE"])
    ais_total = len(df1[df1["Carrier"] == "AIS"])

    render_summary()
    st.subheader("DTENLinkage")
    st.dataframe(df1.style.apply(highlight_error_dten, axis=1))

# =========================
# TCAP
# =========================
if tcap_file:
    df_tcap = pd.read_csv(tcap_file) if tcap_file.name.endswith(".csv") else pd.read_excel(tcap_file)

    trows = []

    for col in df_tcap.columns:
        for val in df_tcap[col]:
            if pd.isna(val): continue

            for d, imei, iccid, imsi, prod, pd1, sd, ts in extract_tcap(str(val)):
                trows.append({
                    "DeviceID": d,
                    "IMEI": imei,
                    "ICCID": iccid,
                    "IMSI": imsi,
                    "ProdStatus": prod,
                    "ProdDate": pd1,
                    "SendDate": sd,
                    "TypeStatus": ts
                })

    df2 = pd.DataFrame(trows).drop_duplicates(subset=["DeviceID","IMEI"])
    df2["TypeStatus"] = df2["TypeStatus"].astype(str).str.strip()

    tcap_total = len(df2)
    tcap_error = len(df2[df2["TypeStatus"] != "OK"])

    render_summary()
    st.subheader("DTENTCAPLinkage")
    st.dataframe(df2.style.apply(highlight_error_tcap, axis=1))

# =========================
# REQUESTER
# =========================
if req_file:
    df_req = pd.read_csv(req_file) if req_file.name.endswith(".csv") else pd.read_excel(req_file)

    rrows = []

    for col in df_req.columns:
        for val in df_req[col]:
            if pd.isna(val): continue

            text = str(val)
            cid = extract_corr_id(text)
            if not cid: continue

            for ro, d, to, code, desc, msg in extract_ais(text):
                rrows.append({
                    "DeviceID": d,
                    "UUID": cid,
                    "ResourceOrderId": ro,
                    "ResultCode": code,
                    "ResultDesc": desc
                })

    df3 = pd.DataFrame(rrows).drop_duplicates(subset=["DeviceID","UUID"])
    df3["ResultCode"] = df3["ResultCode"].astype(str).str.strip()

    df7 = df3[df3["ResultCode"] != "20000"]

    req_total = len(df3)
    req_error = len(df7)

    render_summary()
    st.subheader("ProvisioningRequester")
    st.dataframe(df3.style.apply(highlight_error_req, axis=1))

# =========================
# RESPONDER
# =========================
if res_file:
    df_res = pd.read_csv(res_file) if res_file.name.endswith(".csv") else pd.read_excel(res_file)

    srows = []

    for col in df_res.columns:
        for val in df_res[col]:
            if pd.isna(val): continue

            text = str(val)
            cid = extract_corr_id(text)
            if not cid: continue

            try:
                json_part = text.split("Response:")[-1].strip()
                data = json.loads(json_part)

                srows.append({
                    "DeviceID": data.get("resourceGroupId"),
                    "UUID": cid,
                    "ResourceOrderId": data.get("resourceOrderId"),
                    "ResultCode": data.get("resultCode"),
                    "ResultDesc": data.get("resultDesc"),
                    "DeveloperMessage": data.get("developerMessage") or "-"
                })
            except:
                continue

    df4 = pd.DataFrame(srows).drop_duplicates(subset=["DeviceID","UUID"])
    df4["ResultCode"] = df4["ResultCode"].astype(str).str.strip()

    df8 = df4[df4["ResultCode"] != "20000"]

    res_total = len(df4)
    res_error = len(df8)

    render_summary()
    st.subheader("ProvisioningResponder")
    st.dataframe(df4.style.apply(highlight_error_res, axis=1))

# =========================
# ERROR TABLE
# =========================
if not df7.empty:
    st.subheader("ProvisioningRequester Error")
    st.dataframe(df7)

if not df8.empty:
    st.subheader("Responder Error")
    st.dataframe(df8)

# =========================
# CLEAN DUPLICATE (เอาแถวบนสุด)
# =========================
df3_clean = df3.drop_duplicates(subset=["DeviceID"], keep="first") if not df3.empty else pd.DataFrame(columns=["DeviceID","ResultDesc"])
df4_clean = df4.drop_duplicates(subset=["DeviceID"], keep="first") if not df4.empty else pd.DataFrame(columns=["DeviceID","ResultDesc"])

# =========================
# SUMMARY
# =========================
if not df1.empty:
    df_summary = df1.copy()

    df_summary.insert(0, "No.", range(1, len(df_summary) + 1))

    df_summary = df_summary.merge(
        df2[["DeviceID", "ProdStatus"]] if not df2.empty else pd.DataFrame(columns=["DeviceID", "ProdStatus"]),
        on="DeviceID",
        how="left"
    )

    df_summary["sent to TCAP Cloud"] = df_summary["DeviceID"].isin(df2["DeviceID"]).map({True: "Yes", False: "No"})
    df_summary["sent to AIS"] = df_summary["DeviceID"].isin(df3_clean["DeviceID"]).map({True: "Yes", False: "No"})

    df_summary = df_summary.merge(df3_clean[["DeviceID", "ResultDesc"]], on="DeviceID", how="left")

    df_summary["sent results"] = df_summary.apply(
        lambda x: "-" if (x["Carrier"] == "TRUE" or str(x["ProdStatus"]) == "SVCP") else x["ResultDesc"],
        axis=1
    )

    df_summary.drop(columns=["ResultDesc"], inplace=True)

    df_summary["received from AIS"] = df_summary["DeviceID"].isin(df4_clean["DeviceID"]).map({True: "Yes", False: "No"})

    df_summary = df_summary.merge(df4_clean[["DeviceID", "ResultDesc"]], on="DeviceID", how="left")

    df_summary["received results"] = df_summary.apply(
        lambda x: "-" if (x["Carrier"] == "TRUE" or str(x["ProdStatus"]) == "SVCP") else x["ResultDesc"],
        axis=1
    )

    df_summary.rename(columns={
        "Result": "DTENLinkage Result",
        "ProdStatus": "ProStatus"
    }, inplace=True)

    df_summary = df_summary[
        ["No.","Request ID","DeviceID","ProStatus","Carrier",
         "DTENLinkage Result",
         "sent to TCAP Cloud","sent to AIS","sent results",
         "received from AIS","received results"]
    ]

    st.subheader("Summary")
    st.dataframe(df_summary)

# =========================
# EXPORT
# =========================
if not df1.empty or not df2.empty or not df3.empty or not df4.empty:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if not df1.empty:
            df1.to_excel(writer, index=False, sheet_name='DTENLinkage')
        if not df2.empty:
            df2.to_excel(writer, index=False, sheet_name='DTENTCAPLinkage')
        if not df3.empty:
            df3.to_excel(writer, index=False, sheet_name='ProvisioningRequester')
        if not df4.empty:
            df4.to_excel(writer, index=False, sheet_name='ProvisioningResponder')
        if not df7.empty:
            df7.to_excel(writer, index=False, sheet_name='Requester_Error')
        if not df8.empty:
            df8.to_excel(writer, index=False, sheet_name='Responder_Error')
        if not df_summary.empty:
            df_summary.to_excel(writer, index=False, sheet_name='Summary')

    output.seek(0)

    st.download_button(
        "Download Summary",
        data=output,
        file_name="dten-summary.xlsx"
    )
