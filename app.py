import streamlit as st
import pandas as pd
import plotly.express as px

# 1. KONFIGURASI & LIMIT RENDER
pd.set_option("styler.render.max_elements", 1000000)
st.set_page_config(page_title="Dashboard Stok Opname", layout="wide")

# CSS Kustom untuk tampilan elegant & animasi status
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    [data-testid="stSidebar"] .stElementContainer button { width: 100% !important; }
    
    /* Animasi Status untuk Monitoring Resume */
    .status-done { color: white; background-color: #28a745; padding: 5px; border-radius: 5px; animation: pulse 2s infinite; }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
    """, unsafe_allow_html=True)

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
            st.text_input("Password Aplikasi", type="password", on_change=password_entered, key="password")
        return False
    return st.session_state["password_correct"]

if not check_password():
    st.stop()

# 3. FUNGSI LOAD DATA (LOCAL STORAGE / SESSION CACHE)
@st.cache_data(ttl=600)
def fetch_raw_data():
    sheet_id = "1mjjDF1ETjOB_eTI6ChI6dqvg0wf9aCa7cJwx0x2K3No"
    url_stok = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=database_stok"
    url_audit = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=database_stokopname"
    
    ds = pd.read_csv(url_stok, low_memory=False).fillna({'DEPARTEMEN': 'Tanpa Dept', 'LOKASI': 'Tanpa Lokasi', 'STATUSSELISIH': 'Sesuai'})
    da = pd.read_csv(url_audit, low_memory=False)
    da.columns = [str(c).strip().upper() for c in da.columns]
    return ds, da

# Simpan ke Session State (Local Storage)
if 'stok_db' not in st.session_state:
    st.session_state['stok_db'], st.session_state['audit_db'] = fetch_raw_data()

df = st.session_state['stok_db']
df_audit = st.session_state['audit_db']

# --- SIDEBAR & TOMBOL PROGRESS ---
with st.sidebar:
    st.header("🎯 Filter Panel")
    all_dept = sorted(df["DEPARTEMEN"].unique().tolist())
    dept_filter = st.multiselect("Pilih Departemen:", options=all_dept, default=all_dept)
    
    st.markdown("---")
    st.header("🚀 Quick Input (New Tab)")
    st.link_button("📝 Progress 1 (P1)", "https://script.google.com/macros/s/AKfycbzy2LxYk5lZHDyLav1MD7RZj6bR8R2LGwHQRVQaftTgXI00iFMzX7jp-37iz-mra8GXKg/exec")
    st.link_button("📝 Progress 2 (P2)", "https://script.google.com/macros/s/AKfycbxWEUlPuofOGeDgGaEo1qh9QP0vs9f5NZju0WwKnnT-y3jrRpUhuBghORQPNQQRw7Ef/exec")
    st.link_button("📝 Progress 3 (P3)", "https://script.google.com/macros/s/AKfycbwYchGDTxUWDwoEVxHPrBKxsuIOQOCiyUTq02SdJ93gpgVSRlXerkSM2UnfLPxxPxvc/exec")
    
    if st.button("🔄 Refresh Data G-Sheets"):
        st.cache_data.clear()
        del st.session_state['stok_db']
        st.rerun()

# --- LOGIKA PIVOT AUDIT ---
col_harga = "HARGAJUAL" if "HARGAJUAL" in df_audit.columns else "HARGA_JUAL"
for c in ['QTYFISIK', 'QTYTEORI', 'VAL_SELISIH_JUAL', col_harga]:
    if c in df_audit.columns: df_audit[c] = pd.to_numeric(df_audit[c], errors='coerce').fillna(0)

df_pivot = df_audit.pivot_table(
    index=['BARCODE_KODE', 'DESKRIPSI', 'DEPARTEMEN', 'LOKASI', 'QTYTEORI'],
    columns='JENIS_PENGHITUNG',
    values=['QTYFISIK', 'VAL_SELISIH_JUAL', 'NAMA_PETUGAS'],
    aggfunc={'QTYFISIK': 'sum', 'VAL_SELISIH_JUAL': 'sum', 'NAMA_PETUGAS': lambda x: ', '.join(sorted(set(x.astype(str))))}
).fillna(0)
df_pivot.columns = [f"{col}_{type}" for col, type in df_pivot.columns]
df_pivot = df_pivot.reset_index()

# Proteksi Kolom P1-P3 & Logika Selisih
for p in ['P1', 'P2', 'P3']:
    for f in ['QTYFISIK', 'VAL_SELISIH_JUAL', 'NAMA_PETUGAS']:
        if f"{f}_{p}" not in df_pivot.columns: df_pivot[f"{f}_{p}"] = 0 if f != 'NAMA_PETUGAS' else "-"

def get_audit_logic(row):
    q1, q2, q3 = row['QTYFISIK_P1'], row['QTYFISIK_P2'], row['QTYFISIK_P3']
    final_f = q3 if q3 != 0 else (q1 if q1 != 0 else 0)
    selisih = row['QTYTEORI'] - final_f
    ket = "MATCH" if q1 == q2 else "UNMATCH"
    if q1 == 0 and q2 == 0: ket = "EMPTY"
    if q3 != 0: ket = "DONE (P3)"
    p_join = ', '.join(sorted(set([str(row['NAMA_PETUGAS_P1']), str(row['NAMA_PETUGAS_P2']), str(row['NAMA_PETUGAS_P3'])])))
    return final_f, selisih, ket, p_join.replace("-, ", "").replace("-", "")

df_pivot[['FINAL_FISIK', 'QTYSELISIH_AUDIT', 'STATUS_AUDIT', 'PETUGAS_JOIN']] = df_pivot.apply(lambda x: pd.Series(get_audit_logic(x)), axis=1)

# --- TABS INTERFACE ---
tab1, tab2, tab3 = st.tabs(["📊 Dashboard Stok", "📋 Progres Audit (Pivot)", "📡 Monitoring RESUME"])

with tab1:
    mask = df["DEPARTEMEN"].isin(dept_filter)
    df_sel = df[mask]
    st.title("📦 Monitoring Dashboard")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total SKU", f"{len(df_sel):,}")
    c2.metric("Total Value", f"Rp {df_sel['VALSELLING'].sum():,.0f}")
    c3.metric("Selisih Qty", f"{df_sel['QTYSELISIH'].sum():,}", delta_color="inverse")
    c4.metric("Selisih Value", f"Rp {df_sel['SELISIHVALSELLING'].sum():,.0f}", delta_color="inverse")
    
    st.dataframe(df_sel, use_container_width=True)

with tab2:
    st.title("📋 Pivot Detail Audit P1-P2-P3")
    s_query = st.text_input("🔍 Cari Barcode/Deskripsi:", key="p_search")
    df_p_filt = df_pivot[df_pivot["DESKRIPSI"].str.contains(s_query, case=False)] if s_query else df_pivot
    st.dataframe(df_p_filt, use_container_width=True)

with tab3:
    st.title("📡 Resume Per Lokasi Audit")
    df_res = df_pivot.groupby('LOKASI').agg({
        'BARCODE_KODE': 'count',
        'QTYFISIK_P1': lambda x: 'DONE' if (x != 0).any() else 'EMPTY',
        'QTYFISIK_P2': lambda x: 'DONE' if (x != 0).any() else 'EMPTY',
        'QTYFISIK_P3': lambda x: 'DONE' if (x != 0).any() else 'EMPTY',
        'PETUGAS_JOIN': lambda x: ', '.join(sorted(set(', '.join(x).split(', '))))
    }).reset_index()
    
    st.table(df_res.style.applymap(lambda x: 'background-color: #28a745; color: white' if x == 'DONE' else ('background-color: #dc3545; color: white' if x == 'EMPTY' else ''), subset=['QTYFISIK_P1', 'QTYFISIK_P2', 'QTYFISIK_P3']))
