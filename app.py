import streamlit as st
import pandas as pd
import plotly.express as px

# 1. KONFIGURASI HALAMAN & LIMIT RENDER
pd.set_option("styler.render.max_elements", 1000000)
st.set_page_config(page_title="Dashboard Stok Opname", layout="wide")

# 2. SISTEM PASSWORD (MBG123)
def check_password():
    """Returns True if the user had the correct password."""
    def password_entered():
        if st.session_state["password"] == "mbg123":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Hapus password dari session
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Tampilan Form Login Center
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            st.markdown("""
                <div style='text-align: center; background-color: #ffffff; padding: 30px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);'>
                    <h2 style='color: #1f77b4;'>🔐 Restricted Access</h2>
                    <p style='color: #666;'>Sistem Monitoring Stok Opname</p>
                </div>
            """, unsafe_allow_html=True)
            st.text_input("Masukkan Password Aplikasi", type="password", on_change=password_entered, key="password")
            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.error("😕 Password salah. Silakan coba lagi.")
        return False
    return st.session_state["password_correct"]

# Cek password sebelum menjalankan sisa script
if not check_password():
    st.stop()

# 3. CSS KUSTOM UNTUK UI ELEGANT
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    /* Menyeragamkan lebar tombol di sidebar */
    [data-testid="stSidebar"] .stElementContainer button {
        width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 4. LOAD DATA DARI GOOGLE SHEETS
@st.cache_data(ttl=600)
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

    # --- SIDEBAR: FILTER & LINK AKSES ---
    with st.sidebar:
        st.header("🎯 Filter Panel")
        
        all_dept = sorted(df["DEPARTEMEN"].unique().tolist())
        dept_filter = st.multiselect("Pilih Departemen:", options=all_dept, default=all_dept)
        
        all_lokasi = sorted(df["LOKASI"].unique().tolist())
        lokasi_filter = st.multiselect("Pilih Lokasi:", options=all_lokasi, default=all_lokasi)
        
        all_status = df["STATUSSELISIH"].unique().tolist()
        status_filter = st.multiselect("Status Selisih:", options=all_status, default=all_status)

        st.markdown("---")
        
        # LINK PROGRESS GAS
        st.header("🔗 Progress Monitoring")
        st.link_button("🚀 Progress 1", "https://script.google.com/macros/s/AKfycbzy2LxYk5lZHDyLav1MD7RZj6bR8R2LGwHQRVQaftTgXI00iFMzX7jp-37iz-mra8GXKg/exec")
        st.link_button("🚀 Progress 2", "https://script.google.com/macros/s/AKfycbxWEUlPuofOGeDgGaEo1qh9QP0vs9f5NZju0WwKnnT-y3jrRpUhuBghORQPNQQRw7Ef/exec")
        st.link_button("🚀 Progress 3", "https://script.google.com/macros/s/AKfycbwYchGDTxUWDwoEVxHPrBKxsuIOQOCiyUTq02SdJ93gpgVSRlXerkSM2UnfLPxxPxvc/exec")
        
        st.markdown("---")

        # LINK SISTEM PENDUKUNG
        st.header("🛠️ Sistem Pendukung")
        st.link_button("🔍 Unlisting Product", "https://grandmitra.github.io/unlisting/")
        st.link_button("🕵️ Lost Code Hunt", "https://grandmitra.github.io/lostcodehunt/")
        st.link_button("📝 Input SO Manual", "https://grandmitra.github.io/inputso/")
        st.link_button("🚚 Anterinlah App", "https://anterinlah.web.app/")

    # 5. LOGIKA FILTER
    mask = df["DEPARTEMEN"].isin(dept_filter) & df["LOKASI"].isin(lokasi_filter) & df["STATUSSELISIH"].isin(status_filter)
    df_selection = df[mask]

    # --- MAIN DASHBOARD ---
    st.title("📦 Sistem Monitoring Stok Opname")
    st.info(f"Menampilkan {len(df_selection):,} baris data berdasarkan filter.")

    # 6. SCORECARDS (KPI)
    c1, c2, c3, c4 = st.columns(4)
    
    total_val_selling = df_selection["VALSELLING"].sum()
    total_selisih_qty = df_selection["QTYSELISIH"].sum()
    total_selisih_val = df_selection["SELISIHVALSELLING"].sum()
    
    c1.metric("Total SKU", f"{len(df_selection):,}")
    c2.metric("Total Value (Selling)", f"Rp {total_val_selling:,.0f}")
    c3.metric("Total Selisih Qty", f"{total_selisih_qty:,}", delta_color="inverse")
    c4.metric("Total Selisih Value", f"Rp {total_selisih_val:,.0f}", delta_color="inverse")

    st.markdown("---")

    # 7. VISUALISASI DATA
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

    # 8. TABEL DATA DETAIL
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

    # 9. FITUR DOWNLOAD
    csv = df_selection.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Data Filtered (CSV)",
        data=csv,
        file_name='hasil_stok_opname.csv',
        mime='text/csv',
    )

except Exception as e:
    st.error(f"Terjadi kesalahan teknis: {e}")
