import streamlit as st
import pandas as pd

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="Dashboard Stok Opname", layout="wide")

# 2. SISTEM PASSWORD
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            st.markdown("<div style='text-align: center;'><h2>🔐 Login Sistem</h2></div>", unsafe_allow_html=True)
            pwd = st.text_input("Masukkan Password", type="password")
            if st.button("Masuk"):
                if pwd == "mbg123":
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("😕 Password salah.")
        return False
    return True

if not check_password():
    st.stop()

# 3. LOAD DATA & LOCAL STORAGE
@st.cache_data(ttl=600)
def fetch_data():
    sheet_id = "1mjjDF1ETjOB_eTI6ChI6dqvg0wf9aCa7cJwx0x2K3No"
    url_stok = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=database_stok"
    url_audit = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=database_stokopname"
    
    df_s = pd.read_csv(url_stok, low_memory=False)
    df_a = pd.read_csv(url_audit, low_memory=False)
    df_a.columns = [str(c).strip().upper() for c in df_a.columns]
    return df_s, df_a

if 'data_stok' not in st.session_state:
    s, a = fetch_data()
    st.session_state['data_stok'] = s
    st.session_state['data_audit'] = a

df_stok = st.session_state['data_stok']
df_audit = st.session_state['data_audit']

# 4. SIDEBAR - TOMBOL SISTEM PENDUKUNG
with st.sidebar:
    st.image("https://grandmitra.site/wp-content/uploads/2023/10/Logo-GMB-New-1.png", width=150) # Opsional: Logo GMB
    st.header("🛠️ Sistem Pendukung")
    
    st.link_button("🔍 Unlisting Product", "https://grandmitra.github.io/unlisting/", use_container_width=True)
    st.link_button("🕵️ Lost Code Hunt", "https://grandmitra.github.io/lostcodehunt/", use_container_width=True)
    st.link_button("📝 Input SO Manual", "https://grandmitra.github.io/inputso/", use_container_width=True)
    st.link_button("🚚 Anterinlah App", "https://anterinlah.web.app/", use_container_width=True)
    
    st.markdown("---")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        if 'data_stok' in st.session_state: del st.session_state['data_stok']
        if 'data_audit' in st.session_state: del st.session_state['data_audit']
        st.rerun()

# 5. PEMROSESAN DATA AUDIT (PIVOT)
for c in ['QTYFISIK', 'QTYTEORI']:
    if c in df_audit.columns:
        df_audit[c] = pd.to_numeric(df_audit[c], errors='coerce').fillna(0)

df_pivot = df_audit.pivot_table(
    index=['BARCODE_KODE', 'DESKRIPSI', 'LOKASI', 'QTYTEORI'],
    columns='JENIS_PENGHITUNG',
    values='QTYFISIK',
    aggfunc='sum'
).fillna(0).reset_index()

for p in ['P1', 'P2', 'P3']:
    if p not in df_pivot.columns:
        df_pivot[p] = 0

def hitung_selisih(row):
    fisik_akhir = row['P3'] if row['P3'] != 0 else row['P1']
    return row['QTYTEORI'] - fisik_akhir

df_pivot['SELISIH'] = df_pivot.apply(hitung_selisih, axis=1)

# --- UI INTERFACE ---
tab_dash, tab_prog, tab_res = st.tabs(["📊 Dashboard Lokasi", "📋 Audit Pivot", "📡 Resume"])

# TAB 1: DASHBOARD LOKASI
with tab_dash:
    st.subheader("Pencarian Item di Banyak Titik")
    search_l = st.text_input("📍 Filter Lokasi (Contoh: W5030):")
    df_dash_filt = df_stok[df_stok['LOKASI'].astype(str).str.contains(search_l, case=False, na=False)] if search_l else df_stok
    st.metric("SKU Terdeteksi", f"{len(df_dash_filt):,}")
    st.dataframe(df_dash_filt, use_container_width=True)

# TAB 2: AUDIT PIVOT (Sejajar)
with tab_prog:
    st.subheader("Data Audit Sejajar (P1, P2, P3)")
    q = st.text_input("🔍 Cari Barcode/Nama Barang:")
    df_view = df_pivot
    if q:
        df_view = df_pivot[df_pivot['DESKRIPSI'].str.contains(q, case=False) | df_pivot['BARCODE_KODE'].astype(str).str.contains(q)]
    
    st.dataframe(
        df_view[['BARCODE_KODE', 'DESKRIPSI', 'LOKASI', 'QTYTEORI', 'P1', 'P2', 'P3', 'SELISIH']],
        use_container_width=True
    )

# TAB 3: RESUME
with tab_res:
    st.subheader("Resume Per Titik Lokasi Audit")
    df_res = df_pivot.groupby('LOKASI').agg({'BARCODE_KODE': 'count', 'SELISIH': 'sum'}).reset_index()
    st.dataframe(df_res, use_container_width=True)
