import streamlit as st
import pandas as pd
import plotly.express as px

# Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Stok Opname", layout="wide")

# Fungsi untuk memuat data dari Google Sheets
@st.cache_data
def load_data():
    sheet_id = "1mjjDF1ETjOB_eTI6ChI6dqvg0wf9aCa7cJwx0x2K3No"
    sheet_name = "database_stok"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    df = pd.read_csv(url)
    return df

try:
    df = load_data()

    # --- SIDEBAR FILTER ---
    st.sidebar.header("Filter Data")
    
    dept_filter = st.sidebar.multiselect(
        "Pilih Departemen:", 
        options=df["DEPARTEMEN"].unique(), 
        default=df["DEPARTEMEN"].unique()
    )
    
    lokasi_filter = st.sidebar.multiselect(
        "Pilih Lokasi:", 
        options=df["LOKASI"].unique(), 
        default=df["LOKASI"].unique()
    )
    
    status_filter = st.sidebar.multiselect(
        "Pilih Status Selisih:", 
        options=df["STATUSSELISIH"].unique(), 
        default=df["STATUSSELISIH"].unique()
    )

    # Apply Filters
    df_selection = df.query(
        "DEPARTEMEN == @dept_filter & LOKASI == @lokasi_filter & STATUSSELISIH == @status_filter"
    )

    # --- MAIN PAGE ---
    st.title("📊 Dashboard Hasil Stok Opname")
    st.markdown("##")

    # --- SCORECARDS ---
    total_item = len(df_selection)
    total_val_selling = df_selection["VALSELLING"].sum()
    total_selisih_qty = df_selection["QTYSELISIH"].sum()
    total_selisih_val = df_selection["SELISIHVALSELLING"].sum()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Item", f"{total_item:,}")
    with col2:
        st.metric("Total Value (Selling)", f"Rp {total_val_selling:,.0f}")
    with col3:
        st.metric("Total Selisih Qty", f"{total_selisih_qty:,}")
    with col4:
        st.metric("Total Selisih Value", f"Rp {total_selisih_val:,.0f}")

    st.markdown("---")

    # --- GRAFIK ---
    left_column, right_column = st.columns(2)

    # Bar Chart: Selisih per Departemen
    fig_dept = px.bar(
        df_selection.groupby("DEPARTEMEN")[["SELISIHVALSELLING"]].sum().reset_index(),
        x="DEPARTEMEN",
        y="SELISIHVALSELLING",
        title="<b>Total Selisih Value per Departemen</b>",
        color_discrete_sequence=["#0083B8"] * len(df_selection),
        template="plotly_white",
    )
    left_column.plotly_chart(fig_dept, use_container_width=True)

    # Pie Chart: Status Selisih
    fig_status = px.pie(
        df_selection, 
        values='QTYFISIK', 
        names='STATUSSELISIH', 
        title='<b>Proporsi Status Selisih</b>',
        hole=0.4
    )
    right_column.plotly_chart(fig_status, use_container_width=True)

    # --- TABEL DATA ---
    st.markdown("### Detail Data Stok Opname")
    st.dataframe(
        df_selection.style.highlight_max(axis=0, subset=['QTYSELISIH']),
        use_container_width=True
    )

except Exception as e:
    st.error(f"Gagal memuat data. Pastikan ID Spreadsheet benar dan akses publik terbuka. Error: {e}")
