import streamlit as st
import pandas as pd

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="Dashboard Stok Opname GMB", layout="wide")

# 2. SISTEM PASSWORD
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            st.markdown("<div style='text-align: center;'><h2>🔐 Login Sistem</h2></div>", unsafe_allow_html=True)
            pwd = st.text_input("Masukkan Password", type="password")
            if st.button("Masuk", use_container_width=True):
                if pwd == "mbg123":
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("😕 Password salah.")
        return False
    return True

if not check_password():
    st.stop()

# 3. LOAD DATA & SESSION STATE
@st.cache_data(ttl=300)
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

# 4. SIDEBAR
with st.sidebar:
    st.header("🛠️ Sistem Pendukung")
    st.link_button("🔍 Unlisting Product", "https://grandmitra.github.io/unlisting/", use_container_width=True)
    st.link_button("🕵️ Lost Code Hunt", "https://grandmitra.github.io/lostcodehunt/", use_container_width=True)
    st.link_button("📝 Input SO Manual", "https://grandmitra.github.io/inputso/", use_container_width=True)
    st.link_button("🚚 Anterinlah App", "https://anterinlah.web.app/", use_container_width=True)
    st.markdown("---")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        for k in ['data_stok', 'data_audit']: 
            if k in st.session_state: del st.session_state[k]
        st.rerun()

# 5. PIVOT LOGIC
for c in ['QTYFISIK', 'QTYTEORI']:
    if c in df_audit.columns:
        df_audit[c] = pd.to_numeric(df_audit[c], errors='coerce').fillna(0)

df_pivot = df_audit.pivot_table(
    index=['BARCODE_KODE', 'DESKRIPSI', 'LOKASI', 'QTYTEORI'],
    columns='JENIS_PENGHITUNG', values='QTYFISIK', aggfunc='sum'
).fillna(0).reset_index()

for p in ['P1', 'P2', 'P3']:
    if p not in df_pivot.columns: df_pivot[p] = 0

df_pivot['SELISIH'] = df_pivot.apply(lambda r: (r['P3'] if r['P3'] != 0 else r['P1'])-r['QTYTEORI'], axis=1)

# --- UI TABS ---
tab_dash, tab_prog, tab_res = st.tabs(["📊 Dashboard Lokasi", "📋 Audit Pivot Detail", "📡 Live Tracking Progress"])

# TAB 1: DASHBOARD
with tab_dash:
    search_l = st.text_input("📍 Filter Lokasi:")
    df_filt = df_stok[df_stok['LOKASI'].astype(str).str.contains(search_l, case=False, na=False)] if search_l else df_stok
    st.dataframe(df_filt, use_container_width=True)

# TAB 2: PIVOT
with tab_prog:
    q = st.text_input("🔍 Cari Barang:")
    df_v = df_pivot[(df_pivot['DESKRIPSI'].str.contains(q, case=False)) | (df_pivot['BARCODE_KODE'].astype(str).str.contains(q))] if q else df_pivot
    st.dataframe(df_v[['BARCODE_KODE', 'DESKRIPSI', 'LOKASI', 'QTYTEORI', 'P1', 'P2', 'P3', 'SELISIH']], use_container_width=True)

# TAB 3: LIVE TRACKING (NEW)
with tab_res:
    st.subheader("🚀 Live Tracking Penyelesaian Lokasi")
    
    # Hitung Progress Berdasarkan Lokasi Master di database_stok
    all_locations = set()
    for loc_str in df_stok['LOKASI'].dropna().unique():
        for loc in str(loc_str).split(','):
            all_locations.add(loc.strip())
    
    loc_done = set(df_pivot[df_pivot['P1'] > 0]['LOKASI'].unique())
    
    total_loc = len(all_locations)
    done_count = len(loc_done.intersection(all_locations))
    progress_pct = (done_count / total_loc) if total_loc > 0 else 0
    
    # Tampilan Visual
    c1, c2, c3 = st.columns([1, 1, 2])
    c1.metric("Total Titik Lokasi", f"{total_loc} Titik")
    c2.metric("Lokasi Terisi", f"{done_count} Titik")
    with c3:
        st.write(f"**Progress SO: {progress_pct:.1%}**")
        st.progress(progress_pct)
    
    st.markdown("---")
    
    # Tabel Detail Per Lokasi
    df_res_loc = df_pivot.groupby('LOKASI').agg({
        'BARCODE_KODE': 'count',
        'SELISIH': lambda x: (x != 0).sum()
    }).reset_index()
    df_res_loc.columns = ['LOKASI', 'SKU TERINPUT', 'SKU SELISIH']
    
    st.write("### Detail Input per Lokasi")
    st.dataframe(df_res_loc, use_container_width=True)
