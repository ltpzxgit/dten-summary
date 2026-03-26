import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="DeviceID Compare Tool", layout="wide")

st.title("🔍 DeviceID Compare Tool")

# =========================
# Upload Files
# =========================
file1 = st.file_uploader("📥 Upload File 1 (System)", type=["xlsx", "csv"])
file2 = st.file_uploader("📥 Upload File 2 (TCAP Cloud)", type=["xlsx", "csv"])


# =========================
# Helper Functions
# =========================
def load_file(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)


def normalize_column(df):
    df.columns = df.columns.str.strip()
    return df


def clean_deviceid(series):
    return series.astype(str).str.strip()


# =========================
# Main Logic
# =========================
if file1 and file2:

    df1 = load_file(file1)
    df2 = load_file(file2)

    df1 = normalize_column(df1)
    df2 = normalize_column(df2)

    st.success("✅ Upload สำเร็จ")

    # =========================
    # Select Column
    # =========================
    col1, col2 = st.columns(2)

    with col1:
        device_col1 = st.selectbox("เลือก DeviceID column (File 1)", df1.columns)

    with col2:
        device_col2 = st.selectbox("เลือก DeviceID column (File 2)", df2.columns)

    # =========================
    # Process Button
    # =========================
    if st.button("🚀 Start Compare"):

        # Clean Data
        df1[device_col1] = clean_deviceid(df1[device_col1])
        df2[device_col2] = clean_deviceid(df2[device_col2])

        # =========================
        # Compare
        # =========================
        df1["Sent to TCAP Cloud"] = df1[device_col1].isin(df2[device_col2]).map({
            True: "Yes",
            False: "No"
        })

        # =========================
        # Mismatch (File2 not in File1)
        # =========================
        df_mismatch = df2[~df2[device_col2].isin(df1[device_col1])].copy()

        # =========================
        # Metrics
        # =========================
        colA, colB, colC = st.columns(3)

        with colA:
            st.metric("Total File1", len(df1))

        with colB:
            st.metric("Matched (Yes)", (df1["Sent to TCAP Cloud"] == "Yes").sum())

        with colC:
            st.metric("Not Match (File2)", len(df_mismatch))

        st.divider()

        # =========================
        # Show Data
        # =========================
        st.subheader("📄 Sheet1: Matched Result")
        st.dataframe(df1, use_container_width=True)

        st.subheader("❌ Sheet2: DeviceID not in System")
        st.dataframe(df_mismatch, use_container_width=True)

        # =========================
        # Export Excel
        # =========================
        output = BytesIO()

        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df1.to_excel(writer, sheet_name="Matched", index=False)
            df_mismatch.to_excel(writer, sheet_name="NotMatch", index=False)

        st.download_button(
            label="📥 Download Excel",
            data=output.getvalue(),
            file_name="deviceid_compare_result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# =========================
# Footer
# =========================
st.caption("Made for comparing DeviceID between System vs TCAP Cloud 🚀")
