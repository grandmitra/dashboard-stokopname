import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Menaikkan limit render Pandas agar tidak error pada 18k+ baris
pd.set_option("styler.render.max_elements", 1000000)

st.set_page_config(page_title="Dashboard Stok Opname", layout="wide")

# CSS Kustom untuk tampilan lebih elegant
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    /* Style khusus untuk tombol agar terlihat seragam */
    div.stButton > button:first-child {
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600) # Data disimpan di cache selama 10 menit
def load_data():
    sheet_id = "1mjjDF1ETjOB_eTI6ChI6dqvg0wf9aCa7cJwx0x2K3No"
    sheet_name = "database_stok"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    df = pd.read_csv(url, low_memory=False)
    
    # Pembersihan data dasar
    fill_values = {'DEPARTEMEN': 'Tanpa Dept', 'LOKASI': 'Tanpa Lokasi', 'STATUSSELISIH': 'Sesuai'}
    return df.fillna(value=fill_values)

try:
    df = load_data()

    # --- SIDEBAR FILTER & LINKS ---
    st.sidebar.header("🎯 Filter Panel")
    
    # Filter Departemen
    all_dept = sorted(df["DEPARTEMEN"].unique().tolist())
    dept_filter = st.sidebar.multiselect("Pilih Departemen:", options=all_dept, default=all_dept)
    
    # Filter Lokasi
    all_lokasi = sorted(df["LOKASI"].unique().tolist())
    lokasi_filter = st.sidebar.multiselect("Pilih Lokasi:", options=all_lokasi, default=all_lokasi)
    
    # Filter Status
    all_status = df["STATUSSELISIH"].unique().tolist()
    status_filter = st.sidebar.multiselect("Status Selisih:", options=all_status, default=all_status)

    st.sidebar.markdown("---")
    st.sidebar.header("🔗 Akses Progress GAS")
    
    # Menambahkan Tombol Progress dengan target="_blank" otomatis (default Streamlit link_button)
    st.sidebar.link_button("🚀 Buka Progress 1", "https://script.google.com/macros/s/AKfycbzy2LxYk5lZHDyLav1MD7RZj6bR8R2LGwHQRVQaftTgXI00iFMzX7jp-37iz-mra8GXKg/exec")
    st.sidebar.link_button("🚀 Buka Progress 2", "https://script.google.com/macros/s/AKfycbxWEUlPuofOGeDgGaEo1qh9QP0vs9f5NZju0WwKnnT-y3jrRpUhuBghORQPNQQRw7Ef/exec")
    st.sidebar.link_button("🚀 Buka Progress 3", "https://script.google.com/macros/s/AKfycbwYchGDTxUWDwoEVxHPrBKxsuIOQOCiyUTq02SdJ93gpgVSRlXerkSM2UnfLPxxPxvc/exec")

    # Filter Logic
    mask = df["DEPARTEMEN"].isin(dept_filter) & df["LOKASI"].isin(lokasi_filter) & df["STATUSSELISIH"].isin(status_filter)
    df_selection = df[mask]

    # --- HEADER ---
    st.title("📦 Sistem Monitoring Stok Opname")
    st.info(f"Menampilkan {len(df_selection):,} baris data berdasarkan filter.")

    # --- SCORECARDS ---
    c1, c2, c3, c4 = st.columns(4)
    
    # Menghitung metrik
    total_val_selling = df_selection["VALSELLING"].sum()
    total_selisih_qty = df_selection["QTYSELISIH"].sum()
    total_selisih_val = df_selection["SELISIHVALSELLING"].sum()
    
    c1.metric("Total SKU", f"{len(df_selection):,}")
    c2.metric("Total Value (Selling)", f"Rp {total_val_selling:,.0f}")
    c3.metric("Total Selisih Qty", f"{total_selisih_qty:,}", delta_color="inverse")
    c4.metric("Total Selisih Value", f"Rp {total_selisih_val:,.0f}", delta_color="inverse")

    st.markdown("---")

    # --- VISUALISASI ---
    col_left, col_right = st.columns([6, 4])

    with col_left:
        dept_summary = df_selection.groupby("DEPARTEMEN")[["SELISIHVALSELLING"]].sum().sort_values(by="SELISIHVALSELLING", ascending=True).reset_index()
        fig_dept = px.bar(
            dept_summary, 
            x="SELISIHVALSELLING", 
            y="DEPARTEMEN", 
            orientation='h',
            title="<b>Nilai Selisih per Departemen</b>",
            color="SELISIHVALSELLING",
            color_continuous_scale="RdBu"
        )
        st.plotly_chart(fig_dept, use_container_width=True)

    with col_right:
        fig_status = px.pie(
            df_selection, 
            names='STATUSSELISIH', 
            values='VALSELLING',
            title='<b>Persentase Status Stok</b>',
            hole=0.5,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_status, use_container_width=True)

    # --- TABEL DATA ---
    st.subheader("📋 Rincian Data")
    st.dataframe(
        df_selection, 
        use_container_width=True,
        column_config={
            "SELLING_PRICE": st.column_config.NumberColumn("Harga Jual", format="Rp %d"),
            "VALSELLING": st.column_config.NumberColumn("Total Val", format="Rp %d"),
            "QTYSELISIH": st.column_config.NumberColumn("Selisih", format="%d")
        }
    )

    # Tombol Download
    csv = df_selection.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Data Filtered (CSV)",
        data=csv,
        file_name='hasil_stok_opname.csv',
        mime='text/csv',
    )

except Exception as e:
    st.error(f"Terjadi kesalahan teknis: {e}")
