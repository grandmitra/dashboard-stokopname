import streamlit as st
import pandas as pd
import plotly.express as px

# 1. KONFIGURASI HALAMAN & LIMIT RENDER
pd.set_option("styler.render.max_elements", 1000000)
st.set_page_config(page_title="Dashboard Stok Opname", layout="wide")

# 2. SISTEM PASSWORD (MBG123)
def check_password():
    def password_entered():
        if st.session_state["password"] == "mbg123":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
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

if not check_password():
    st.stop()

# 3. CSS KUSTOM
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    [data-testid="stSidebar"] .stElementContainer button { width: 100% !important; }
    </style>
    """, unsafe_allow_html=True)

# 4. LOAD DATA
@st.cache_data(ttl=600)
def load_all_data():
    sheet_id = "1mjjDF1ETjOB_eTI6ChI6dqvg0wf9aCa7cJwx0x2K3No"
    
    # Load Database Stok
    url_stok = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=database_stok"
    df_stok = pd.read_csv(url_stok, low_memory=False)
    df_stok = df_stok.fillna({'DEPARTEMEN': 'Tanpa Dept', 'LOKASI': 'Tanpa Lokasi', 'STATUSSELISIH': 'Sesuai'})
    
    # Load Database Stokopname (Audit)
    url_audit = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=database_stokopname"
    df_audit = pd.read_csv(url_audit, low_memory=False)
    
    # Standarisasi Nama Kolom (Uppercase & Strip)
    df_audit.columns = [str(c).strip().upper() for c in df_audit.columns]
    return df_stok, df_audit

try:
    df_stok, df_audit = load_all_data()

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("🎯 Global Filter")
        all_dept = sorted(df_stok["DEPARTEMEN"].unique().tolist())
        dept_filter = st.multiselect("Filter Departemen (Dashboard):", options=all_dept, default=all_dept)
        
        st.markdown("---")
        st.header("🔗 Progress Monitoring")
        st.link_button("🚀 Progress 1", "https://script.google.com/macros/s/AKfycbzy2LxYk5lZHDyLav1MD7RZj6bR8R2LGwHQRVQaftTgXI00iFMzX7jp-37iz-mra8GXKg/exec")
        st.link_button("🚀 Progress 2", "https://script.google.com/macros/s/AKfycbxWEUlPuofOGeDgGaEo1qh9QP0vs9f5NZju0WwKnnT-y3jrRpUhuBghORQPNQQRw7Ef/exec")
        st.link_button("🚀 Progress 3", "https://script.google.com/macros/s/AKfycbwYchGDTxUWDwoEVxHPrBKxsuIOQOCiyUTq02SdJ93gpgVSRlXerkSM2UnfLPxxPxvc/exec")
        
        st.markdown("---")
        st.header("🛠️ Sistem Pendukung")
        st.link_button("🔍 Unlisting Product", "https://grandmitra.github.io/unlisting/")
        st.link_button("🕵️ Lost Code Hunt", "https://grandmitra.github.io/lostcodehunt/")
        st.link_button("📝 Input SO Manual", "https://grandmitra.github.io/inputso/")
        st.link_button("🚚 Anterinlah App", "https://anterinlah.web.app/")

    tab_dashboard, tab_progres = st.tabs(["📊 Executive Dashboard", "📋 Progres Audit (Pivot)"])

    # ==========================================
    # TAB 1: EXECUTIVE DASHBOARD
    # ==========================================
    with tab_dashboard:
        st.title("📦 Sistem Monitoring Stok Opname")
        mask = df_stok["DEPARTEMEN"].isin(dept_filter)
        df_selection = df_stok[mask]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total SKU", f"{len(df_selection):,}")
        c2.metric("Total Value", f"Rp {df_selection['VALSELLING'].sum():,.0f}")
        c3.metric("Selisih Qty", f"{df_selection['QTYSELISIH'].sum():,}")
        c4.metric("Selisih Value", f"Rp {df_selection['SELISIHVALSELLING'].sum():,.0f}")

        st.markdown("---")
        col_left, col_right = st.columns([6, 4])
        with col_left:
            dept_sum = df_selection.groupby("DEPARTEMEN")[["SELISIHVALSELLING"]].sum().reset_index()
            st.plotly_chart(px.bar(dept_sum, x="SELISIHVALSELLING", y="DEPARTEMEN", orientation='h', title="Selisih per Dept"), use_container_width=True)
        with col_right:
            st.plotly_chart(px.pie(df_selection, names='STATUSSELISIH', values='VALSELLING', title='Status Stok', hole=0.5), use_container_width=True)

    # ==========================================
    # TAB 2: PROGRES AUDIT (PIVOT SEJAJAR)
    # ==========================================
    with tab_progres:
        st.title("🔍 Audit Progress & Pivot Analysis")
        
        # Identifikasi kolom yang tersedia secara fleksibel
        cols = df_audit.columns
        COL_TITIK = "TITIKLOKASI" if "TITIKLOKASI" in cols else cols[0]
        COL_SEBARAN = "SEBARANLOKASI" if "SEBARANLOKASI" in cols else cols[0]
        
        col_search, col_lok = st.columns([2, 1])
        with col_search:
            search_query = st.text_input("🔍 Cari Barcode atau Nama Barang...", key="audit_search")
        with col_lok:
            all_lok_audit = sorted(df_audit["LOKASI"].unique().astype(str).tolist())
            lok_filter = st.multiselect("📍 Filter By Lokasi:", options=all_lok_audit, default=all_lok_audit)

        # Pre-processing Numerik
        for col in ['QTYFISIK', 'QTYTEORI', 'VAL_SELISIH_JUAL']:
            if col in df_audit.columns:
                df_audit[col] = pd.to_numeric(df_audit[col], errors='coerce').fillna(0)

        # Pivot Table
        # Menggunakan kolom yang sudah divalidasi (TITIKLOKASI, SEBARANLOKASI)
        df_pivot = df_audit.pivot_table(
            index=['BARCODE_KODE', 'DESKRIPSI', 'DEPARTEMEN', 'LOKASI', COL_TITIK, COL_SEBARAN, 'NAMA_PETUGAS', 'QTYTEORI'],
            columns='JENIS_PENGHITUNG',
            values=['QTYFISIK', 'VAL_SELISIH_JUAL'],
            aggfunc='sum'
        ).fillna(0)

        # Flatten Columns
        df_pivot.columns = [f"{col}_{type}" for col, type in df_pivot.columns]
        df_pivot = df_pivot.reset_index()

        # Proteksi Kolom P1, P2, P3
        for p in ['P1', 'P2', 'P3']:
            if f'QTYFISIK_{p}' not in df_pivot.columns: df_pivot[f'QTYFISIK_{p}'] = 0
            if f'VAL_SELISIH_JUAL_{p}' not in df_pivot.columns: df_pivot[f'VAL_SELISIH_JUAL_{p}'] = 0

        # Logika Status SO V14
        def process_audit(row):
            q1, q2, q3 = row['QTYFISIK_P1'], row['QTYFISIK_P2'], row['QTYFISIK_P3']
            if q3 != 0: return q3, q3 - row['QTYTEORI'], "DONE (P3)"
            if q1 == q2 and q1 != 0: return q1, q1 - row['QTYTEORI'], "DONE (MATCH)"
            if q1 != q2: return 0, 0, "MISMATCH (WAIT P3)"
            return 0, 0, "INCOMPLETE"

        df_pivot[['FINAL_FISIK', 'QTYSELISIH', 'KETERANGAN']] = df_pivot.apply(
            lambda x: pd.Series(process_audit(x)), axis=1
        )

        # Apply Filters
        mask_audit = df_pivot["LOKASI"].astype(str).isin(lok_filter)
        if search_query:
            mask_audit = mask_audit & (df_pivot["BARCODE_KODE"].astype(str).str.contains(search_query, case=False) | df_pivot["DESKRIPSI"].str.contains(search_query, case=False))
        
        df_final = df_pivot[mask_audit]

        st.dataframe(
            df_final[['BARCODE_KODE', 'DESKRIPSI', 'LOKASI', COL_TITIK, COL_SEBARAN, 'NAMA_PETUGAS', 'QTYTEORI', 'QTYFISIK_P1', 'QTYFISIK_P2', 'QTYFISIK_P3', 'QTYSELISIH', 'KETERANGAN']],
            use_container_width=True
        )

except Exception as e:
    st.error(f"Terjadi kesalahan teknis: {e}")
    st.info("Pastikan kolom TITIKLOKASI dan SEBARANLOKASI tersedia di sheet database_stokopname.")
