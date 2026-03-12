import streamlit as st
import pandas as pd
import plotly.express as px

# 1. KONFIGURASI HALAMAN
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

# 3. CSS KUSTOM (Untuk Animasi & Badge)
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    [data-testid="stSidebar"] .stElementContainer button { width: 100% !important; }
    
    /* Animasi Status */
    .status-done { color: #ffffff; background-color: #28a745; padding: 4px 8px; border-radius: 5px; font-weight: bold; animation: pulse 2s infinite; }
    .status-empty { color: #ffffff; background-color: #dc3545; padding: 4px 8px; border-radius: 5px; font-weight: bold; }
    .status-complete { color: #ffffff; background-color: #007bff; padding: 4px 8px; border-radius: 5px; font-weight: bold; border: 2px solid #0056b3; }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    </style>
    """, unsafe_allow_html=True)

# 4. LOAD DATA
@st.cache_data(ttl=300)
def load_all_data():
    sheet_id = "1mjjDF1ETjOB_eTI6ChI6dqvg0wf9aCa7cJwx0x2K3No"
    url_stok = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=database_stok"
    url_audit = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=database_stokopname"
    
    df_stok = pd.read_csv(url_stok, low_memory=False)
    df_audit = pd.read_csv(url_audit, low_memory=False)
    
    df_stok = df_stok.fillna({'DEPARTEMEN': 'Tanpa Dept', 'LOKASI': 'Tanpa Lokasi', 'STATUSSELISIH': 'Sesuai'})
    df_audit.columns = [str(c).strip().upper() for c in df_audit.columns]
    
    return df_stok, df_audit

try:
    df_stok, df_audit = load_all_data()

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("🎯 Filter Global")
        all_dept = sorted(df_stok["DEPARTEMEN"].unique().tolist())
        dept_filter = st.multiselect("Pilih Departemen:", options=all_dept, default=all_dept)
        
        st.markdown("---")
        st.header("🛠️ Sistem Pendukung")
        st.link_button("🔍 Unlisting Product", "https://grandmitra.github.io/unlisting/")
        st.link_button("🕵️ Lost Code Hunt", "https://grandmitra.github.io/lostcodehunt/")
        st.link_button("📝 Input SO Manual", "https://grandmitra.github.io/inputso/")
        st.link_button("🚚 Anterinlah App", "https://anterinlah.web.app/")

    # Pre-processing Data Audit
    df_audit['QTYFISIK'] = pd.to_numeric(df_audit['QTYFISIK'], errors='coerce').fillna(0)
    df_audit['QTYTEORI'] = pd.to_numeric(df_audit['QTYTEORI'], errors='coerce').fillna(0)

    # Transformasi Pivot (Join Petugas & Sejajarkan P1-P3)
    df_pivot = df_audit.pivot_table(
        index=['BARCODE_KODE', 'DESKRIPSI', 'DEPARTEMEN', 'LOKASI', 'QTYTEORI'],
        columns='JENIS_PENGHITUNG',
        values=['QTYFISIK', 'NAMA_PETUGAS'],
        aggfunc={'QTYFISIK': 'sum', 'NAMA_PETUGAS': lambda x: ', '.join(sorted(set(x.astype(str))))}
    ).fillna(0)

    df_pivot.columns = [f"{col}_{type}" for col, type in df_pivot.columns]
    df_pivot = df_pivot.reset_index()

    # Pastikan Kolom Eksis
    for p in ['P1', 'P2', 'P3']:
        if f'QTYFISIK_{p}' not in df_pivot.columns: df_pivot[f'QTYFISIK_{p}'] = 0
        if f'NAMA_PETUGAS_{p}' not in df_pivot.columns: df_pivot[f'NAMA_PETUGAS_{p}'] = "-"

    # 5. LOGIKA BARU: SELISIH & MATCH/UNMATCH
    def process_logic(row):
        q1, q2, q3 = row['QTYFISIK_P1'], row['QTYFISIK_P2'], row['QTYFISIK_P3']
        teori = row['QTYTEORI']
        
        # Penentuan QTY FISIK FINAL
        final_fisik = q3 if q3 != 0 else (q1 if q1 != 0 else 0)
        selisih = teori - final_fisik # Rumus: Teori - Fisik
        
        # Penentuan Keterangan Match
        if q1 == 0 and q2 == 0: ket = "BELUM INPUT"
        elif q1 == q2: ket = "MATCH"
        else: ket = "UNMATCH"
        
        # Override jika ada P3
        if q3 != 0: ket = "DONE (ADJUSTED P3)"
            
        return final_fisik, selisih, ket

    df_pivot[['FINAL_FISIK', 'QTYSELISIH', 'KETERANGAN']] = df_pivot.apply(
        lambda x: pd.Series(process_logic(x)), axis=1
    )

    # --- TABS SISTEM ---
    tab_dash, tab_prog, tab_res = st.tabs(["📊 Dashboard", "📋 Progres Audit", "📡 Monitoring RESUME"])

    # TAB 1: DASHBOARD
    with tab_dash:
        mask = df_stok["DEPARTEMEN"].isin(dept_filter)
        df_sel = df_stok[mask]
        st.title("📦 Executive Summary")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total SKU", f"{len(df_sel):,}")
        c2.metric("Total Value", f"Rp {df_sel['VALSELLING'].sum():,.0f}")
        c3.metric("Total Selisih", f"{df_sel['QTYSELISIH'].sum():,}")
        st.dataframe(df_sel, use_container_width=True)

    # TAB 2: PROGRES AUDIT
    with tab_prog:
        st.title("📋 Detail Per Item (Pivot)")
        col_search, col_lok = st.columns([2, 1])
        with col_search:
            s_query = st.text_input("🔍 Cari Barcode/Barang:", key="p_search")
        with col_lok:
            l_filt = st.multiselect("📍 Lokasi:", options=sorted(df_pivot["LOKASI"].unique()), default=df_pivot["LOKASI"].unique())
        
        df_prog_filt = df_pivot[df_pivot["LOKASI"].isin(l_filt)]
        if s_query:
            df_prog_filt = df_prog_filt[df_prog_filt["DESKRIPSI"].str.contains(s_query, case=False) | df_prog_filt["BARCODE_KODE"].astype(str).str.contains(s_query)]
        
        st.dataframe(df_prog_filt[['BARCODE_KODE', 'DESKRIPSI', 'LOKASI', 'QTYTEORI', 'QTYFISIK_P1', 'QTYFISIK_P2', 'QTYFISIK_P3', 'QTYSELISIH', 'KETERANGAN']], use_container_width=True)

    # TAB 3: MONITORING RESUME (NEW)
    with tab_res:
        st.title("📡 Status Penginputan Per Lokasi")
        
        # Aggregate data per LOKASI
        df_resume = df_pivot.groupby('LOKASI').agg({
            'QTYFISIK_P1': lambda x: 'DONE' if (x != 0).any() else 'EMPTY',
            'QTYFISIK_P2': lambda x: 'DONE' if (x != 0).any() else 'EMPTY',
            'QTYFISIK_P3': lambda x: 'DONE' if (x != 0).any() else 'EMPTY'
        }).reset_index()

        def get_final_status(row):
            if row['QTYFISIK_P1'] == 'DONE' and row['QTYFISIK_P2'] == 'DONE' and row['QTYFISIK_P3'] == 'DONE':
                return 'COMPLETE'
            return 'IN PROGRESS'

        df_resume['OVERALL_STATUS'] = df_resume.apply(get_final_status, axis=1)

        # Tampilan Bergaya Card/Table dengan Emoji & Badge
        st.write("### Monitoring Real-Time Lokasi")
        
        # Konfigurasi Tampilan Kolom agar Animasi Terlihat
        st.table(df_resume.style.applymap(lambda x: 
            'background-color: #28a745; color: white' if x == 'DONE' else (
            'background-color: #dc3545; color: white' if x == 'EMPTY' else (
            'background-color: #007bff; color: white' if x == 'COMPLETE' else '')),
            subset=['QTYFISIK_P1', 'QTYFISIK_P2', 'QTYFISIK_P3', 'OVERALL_STATUS']
        ))
        
        st.info("💡 Keterangan: DONE (Hijau), EMPTY (Merah), COMPLETE (Biru - Semua P1-P3 terisi)")

except Exception as e:
    st.error(f"Terjadi kesalahan teknis: {e}")
