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
            st.markdown("<div style='text-align: center;'><h2>🔐 Login Sistem</h2></div>", unsafe_allow_html=True)
            st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    return st.session_state["password_correct"]

if not check_password():
    st.stop()

# 3. FUNGSI LOCAL STORAGE (Cache & Session Management)
@st.cache_data(ttl=600) # Data disimpan di cache selama 10 menit
def fetch_data_from_gsheets():
    sheet_id = "1mjjDF1ETjOB_eTI6ChI6dqvg0wf9aCa7cJwx0x2K3No"
    url_stok = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=database_stok"
    url_audit = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=database_stokopname"
    
    df_stok = pd.read_csv(url_stok, low_memory=False)
    df_audit = pd.read_csv(url_audit, low_memory=False)
    
    # Normalisasi Header Audit
    df_audit.columns = [str(c).strip().upper() for c in df_audit.columns]
    return df_stok, df_audit

# Inisialisasi Data di Local Session State
if 'data_stok' not in st.session_state:
    df_s, df_a = fetch_data_from_gsheets()
    st.session_state['data_stok'] = df_s
    st.session_state['data_audit'] = df_a

# 4. PRE-PROCESSING & LOGIKA PIVOT (DIPANGGIL DARI SESSION)
df_stok = st.session_state['data_stok']
df_audit = st.session_state['data_audit']

# Deteksi Kolom Harga
col_harga = "HARGAJUAL" if "HARGAJUAL" in df_audit.columns else "HARGA_JUAL"

# Konversi Numerik
for c in ['QTYFISIK', 'QTYTEORI', 'VAL_SELISIH_JUAL', col_harga]:
    if c in df_audit.columns:
        df_audit[c] = pd.to_numeric(df_audit[c], errors='coerce').fillna(0)

# Hitung Val Teori
df_audit['VAL_TEORI'] = df_audit[col_harga] * df_audit['QTYTEORI']

# PIVOT TABEL (Kembali ke versi detail)
df_pivot = df_audit.pivot_table(
    index=['BARCODE_KODE', 'DESKRIPSI', 'DEPARTEMEN', 'LOKASI', 'QTYTEORI', 'VAL_TEORI'],
    columns='JENIS_PENGHITUNG',
    values=['QTYFISIK', 'VAL_SELISIH_JUAL', 'NAMA_PETUGAS'],
    aggfunc={
        'QTYFISIK': 'sum', 
        'VAL_SELISIH_JUAL': 'sum',
        'NAMA_PETUGAS': lambda x: ', '.join(sorted(set(x.astype(str))))
    }
).fillna(0)

df_pivot.columns = [f"{col}_{type}" for col, type in df_pivot.columns]
df_pivot = df_pivot.reset_index()

# Proteksi Kolom P1-P3
for p in ['P1', 'P2', 'P3']:
    for f in ['QTYFISIK', 'VAL_SELISIH_JUAL', 'NAMA_PETUGAS']:
        if f"{f}_{p}" not in df_pivot.columns:
            df_pivot[f"{f}_{p}"] = 0 if f != 'NAMA_PETUGAS' else "-"

# Logika Final Per Item
def apply_logic(row):
    q1, q2, q3 = row['QTYFISIK_P1'], row['QTYFISIK_P2'], row['QTYFISIK_P3']
    v1, v3 = row['VAL_SELISIH_JUAL_P1'], row['VAL_SELISIH_JUAL_P3']
    
    final_f = q3 if q3 != 0 else (q1 if q1 != 0 else 0)
    final_v = v3 if q3 != 0 else (v1 if q1 != 0 else 0)
    
    # Keterangan Match/Unmatch
    if q1 == 0 and q2 == 0: ket = "BELUM INPUT"
    elif q1 == q2: ket = "MATCH"
    else: ket = "UNMATCH"
    if q3 != 0: ket = "DONE (P3)"
    
    # Gabungan Petugas
    nms = [str(row['NAMA_PETUGAS_P1']), str(row['NAMA_PETUGAS_P2']), str(row['NAMA_PETUGAS_P3'])]
    clean_nms = ', '.join(sorted(set([n for n in nms if n not in ["-", "0", "0.0", "nan", "None"]])))
    
    return final_f, final_v, ket, clean_nms

df_pivot[['FINAL_FISIK', 'FINAL_VAL_SELISIH', 'KETERANGAN', 'PETUGAS_JOIN']] = df_pivot.apply(
    lambda x: pd.Series(apply_logic(x)), axis=1
)

# --- UI INTERFACE ---
tab_dash, tab_prog, tab_res = st.tabs(["📊 Dashboard Lokasi", "📋 Progres Audit (Pivot)", "📡 Monitoring RESUME"])

# TAB 1: DASHBOARD LOKASI (HANDLING MULTI-LOKASI KOMA)
with tab_dash:
    st.title("📦 Dashboard Lokasi Tersebar")
    
    # Filter Lokasi Spesifik
    search_lok = st.text_input("🔍 Cari Lokasi Tertentu (Contoh: W5030):")
    
    if search_lok:
        # Mencari string lokasi di dalam teks yang dipisahkan koma
        df_dash_filt = df_stok[df_stok['LOKASI'].astype(str).str.contains(search_lok, case=False, na=False)]
    else:
        df_dash_filt = df_stok

    c1, c2, c3 = st.columns(3)
    c1.metric("Total SKU Ditemukan", f"{len(df_dash_filt):,}")
    c2.metric("Total Value", f"Rp {df_dash_filt['VALSELLING'].sum():,.0f}")
    c3.metric("Selisih Qty", f"{df_dash_filt['QTYSELISIH'].sum():,}")
    
    st.dataframe(df_dash_filt, use_container_width=True)

# TAB 2: PROGRES AUDIT (PIVOT DETAIL)
with tab_prog:
    st.title("📋 Pivot Progres Audit Detail")
    s_query = st.text_input("🔍 Cari Barcode/Deskripsi:", key="p_search")
    
    if s_query:
        df_p_filt = df_pivot[df_pivot["DESKRIPSI"].str.contains(s_query, case=False) | df_pivot["BARCODE_KODE"].astype(str).str.contains(s_query)]
        st.dataframe(df_p_filt, use_container_width=True)
    else:
        st.dataframe(df_pivot.head(500), use_container_width=True)
        st.info("Menampilkan 500 data pertama. Gunakan kolom pencarian untuk data spesifik.")

# TAB 3: RESUME (OPTIMIZED)
with tab_res:
    st.title("📡 Resume Per Lokasi Audit")
    
    df_res_loc = df_pivot.groupby('LOKASI').agg({
        'BARCODE_KODE': 'count',
        'FINAL_VAL_SELISIH': 'sum',
        'PETUGAS_JOIN': lambda x: ', '.join(sorted(set(', '.join(x).split(', '))))
    }).reset_index()
    
    df_res_loc['PETUGAS_JOIN'] = df_res_loc['PETUGAS_JOIN'].str.strip(', ')
    
    sc1, sc2 = st.columns(2)
    sc1.metric("Total Lokasi Terinput", len(df_res_loc))
    sc2.metric("Net Selisih Rupiah", f"Rp {df_res_loc['FINAL_VAL_SELISIH'].sum():,.0f}")
    
    st.dataframe(df_res_loc, use_container_width=True)

# Tombol Refresh Local Storage
if st.sidebar.button("🔄 Refresh Data (Clear Cache)"):
    st.cache_data.clear()
    del st.session_state['data_stok']
    del st.session_state['data_audit']
    st.rerun()
