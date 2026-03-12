import streamlit as st
import pandas as pd
import plotly.express as px

# 1. KONFIGURASI HALAMAN
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
            st.markdown("<div style='text-align: center;'><h2>🔐 Login</h2></div>", unsafe_allow_html=True)
            st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    return st.session_state["password_correct"]

if not check_password():
    st.stop()

# 3. LOAD DATA (OPTIMIZED)
@st.cache_data(ttl=300, show_spinner="Sedang mengambil data besar...")
def load_all_data():
    sheet_id = "1mjjDF1ETjOB_eTI6ChI6dqvg0wf9aCa7cJwx0x2K3No"
    # Menggunakan usecols untuk membatasi memori
    url_audit = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=database_stokopname"
    
    # Load database audit (Prioritas Utama)
    df_audit = pd.read_csv(url_audit, low_memory=False)
    df_audit.columns = [str(c).strip().upper() for c in df_audit.columns]
    
    # Minimal cleaning agar tidak berat
    for col in ['QTYFISIK', 'QTYTEORI', 'VAL_SELISIH_JUAL', 'HARGAJUAL', 'HARGA_JUAL']:
        if col in df_audit.columns:
            df_audit[col] = pd.to_numeric(df_audit[col], errors='coerce').fillna(0)
            
    return df_audit

try:
    df_raw = load_all_data()

    # --- TABEL PIVOT (Heavy Logic) ---
    # Kita hanya ambil kolom yang BENAR-BENAR dibutuhkan untuk pivot
    col_harga = "HARGAJUAL" if "HARGAJUAL" in df_raw.columns else "HARGA_JUAL"
    
    df_pivot = df_raw.pivot_table(
        index=['BARCODE_KODE', 'DESKRIPSI', 'LOKASI', 'QTYTEORI'],
        columns='JENIS_PENGHITUNG',
        values=['QTYFISIK', 'VAL_SELISIH_JUAL', 'NAMA_PETUGAS'],
        aggfunc={
            'QTYFISIK': 'sum', 
            'VAL_SELISIH_JUAL': 'sum',
            'NAMA_PETUGAS': lambda x: ', '.join(set(x.astype(str)))
        }
    ).fillna(0)

    df_pivot.columns = [f"{col}_{type}" for col, type in df_pivot.columns]
    df_pivot = df_pivot.reset_index()

    # Logika Final (Optimized)
    def fast_logic(row):
        q1, q3 = row.get('QTYFISIK_P1', 0), row.get('QTYFISIK_P3', 0)
        final_f = q3 if q3 != 0 else q1
        return final_f, row['QTYTEORI'] - final_f

    df_pivot[['FINAL_FISIK', 'QTYSELISIH']] = df_pivot.apply(lambda x: pd.Series(fast_logic(x)), axis=1)

    # --- UI TABS ---
    tab_prog, tab_res = st.tabs(["📋 Progres Audit", "📡 Monitoring RESUME"])

    with tab_prog:
        st.subheader("Detail Item")
        # PENCARIAN ADALAH KUNCI (Agar browser tidak render 60rb baris sekaligus)
        search = st.text_input("🔍 Cari Barcode/Deskripsi (Tekan Enter)")
        if search:
            df_display = df_pivot[df_pivot['DESKRIPSI'].str.contains(search, case=False) | df_pivot['BARCODE_KODE'].astype(str).str.contains(search)]
            st.dataframe(df_display.head(1000), use_container_width=True) # Limit 1000 baris untuk kecepatan browser
        else:
            st.warning("Silakan gunakan kolom pencarian untuk menampilkan data.")

    with tab_res:
        st.subheader("Resume Per Lokasi")
        # Resume biasanya lebih ringan karena jumlah lokasi jauh lebih sedikit dibanding jumlah SKU
        df_res_loc = df_pivot.groupby('LOKASI').agg({
            'BARCODE_KODE': 'count',
            'QTYSELISIH': 'sum',
            'NAMA_PETUGAS_P1': lambda x: ', '.join(set(', '.join(x.astype(str)).split(', ')))
        }).reset_index()
        
        # Scorecards
        c1, c2 = st.columns(2)
        c1.metric("Total SKU Terinput", len(df_pivot))
        c2.metric("Total Selisih Qty", int(df_res_loc['QTYSELISIH'].sum()))

        st.dataframe(df_res_loc, use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
