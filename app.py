import streamlit as st
import pandas as pd

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="Dashboard Stok Opname GMB", layout="wide")

# 2. SISTEM PASSWORD (STABIL)
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            st.markdown("""
                <div style='text-align: center; background-color: #ffffff; padding: 30px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);'>
                    <h2 style='color: #1f77b4;'>🔐 Login Sistem</h2>
                    <p style='color: #666;'>Dashboard Monitoring Stok Opname</p>
                </div>
            """, unsafe_allow_html=True)
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

# 3. LOAD DATA & LOCAL STORAGE (SESSION STATE)
@st.cache_data(ttl=600)
def fetch_data():
    sheet_id = "1mjjDF1ETjOB_eTI6ChI6dqvg0wf9aCa7cJwx0x2K3No"
    url_stok = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=database_stok"
    url_audit = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=database_stokopname"
    
    df_s = pd.read_csv(url_stok, low_memory=False)
    df_a = pd.read_csv(url_audit, low_memory=False)
    
    # Normalisasi Header Audit
    df_a.columns = [str(c).strip().upper() for c in df_a.columns]
    return df_s, df_a

# Inisialisasi Data ke Session State agar kencang
if 'data_stok' not in st.session_state:
    with st.spinner("Sedang mengambil data terbaru..."):
        s, a = fetch_data()
        st.session_state['data_stok'] = s
        st.session_state['data_audit'] = a

df_stok = st.session_state['data_stok']
df_audit = st.session_state['data_audit']

# 4. SIDEBAR - SISTEM PENDUKUNG & REFRESH
with st.sidebar:
    st.markdown("<div style='text-align: center;'><h2>🏢 Grand Mitra</h2></div>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.header("🛠️ Sistem Pendukung")
    st.link_button("🔍 Unlisting Product", "https://grandmitra.github.io/unlisting/", use_container_width=True)
    st.link_button("🕵️ Lost Code Hunt", "https://grandmitra.github.io/lostcodehunt/", use_container_width=True)
    st.link_button("📝 Input SO Manual", "https://grandmitra.github.io/inputso/", use_container_width=True)
    st.link_button("🚚 Anterinlah App", "https://anterinlah.web.app/", use_container_width=True)
    
    st.markdown("---")
    st.header("⚙️ Kontrol")
    if st.button("🔄 Refresh Data G-Sheets", use_container_width=True):
        st.cache_data.clear()
        if 'data_stok' in st.session_state: del st.session_state['data_stok']
        if 'data_audit' in st.session_state: del st.session_state['data_audit']
        st.rerun()
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.caption("Dashboard v23.0 - Grand Mitra Bangunan")

# 5. PEMROSESAN DATA AUDIT (PIVOT SEJAJAR)
# Pastikan kolom numerik benar
for c in ['QTYFISIK', 'QTYTEORI']:
    if c in df_audit.columns:
        df_audit[c] = pd.to_numeric(df_audit[c], errors='coerce').fillna(0)

# Membuat Pivot P1, P2, P3
df_pivot = df_audit.pivot_table(
    index=['BARCODE_KODE', 'DESKRIPSI', 'LOKASI', 'QTYTEORI'],
    columns='JENIS_PENGHITUNG',
    values='QTYFISIK',
    aggfunc='sum'
).fillna(0).reset_index()

# Pastikan kolom P1, P2, P3 selalu ada meski belum ada input
for p in ['P1', 'P2', 'P3']:
    if p not in df_pivot.columns:
        df_pivot[p] = 0

# Rumus Selisih: Prioritas P3, Jika P3 Kosong pakai P1
def hitung_selisih(row):
    fisik_akhir = row['P3'] if row['P3'] != 0 else row['P1']
    return row['QTYTEORI'] - fisik_akhir

df_pivot['SELISIH'] = df_pivot.apply(hitung_selisih, axis=1)

# --- UI INTERFACE TABS ---
tab_dash, tab_prog, tab_res = st.tabs(["📊 Dashboard Lokasi", "📋 Audit Pivot Detail", "📡 Monitoring Resume"])

# TAB 1: DASHBOARD LOKASI (HANDLING MULTI-LOKASI KOMA)
with tab_dash:
    st.subheader("Pencarian Item Berdasarkan Lokasi")
    search_l = st.text_input("📍 Filter Lokasi (Ketik lokasi, misal: W5030):", help="Mencari lokasi meskipun item berada di banyak titik (dipisah koma)")
    
    if search_l:
        # Mencari string lokasi di dalam teks lokasi yang mungkin berisi koma
        df_dash_filt = df_stok[df_stok['LOKASI'].astype(str).str.contains(search_l, case=False, na=False)]
    else:
        df_dash_filt = df_stok

    c1, c2, c3 = st.columns(3)
    c1.metric("Total SKU Terfilter", f"{len(df_dash_filt):,}")
    c2.metric("Total Value Selling", f"Rp {df_dash_filt['VALSELLING'].sum():,.0f}")
    c3.metric("Total Selisih Qty", f"{df_dash_filt['QTYSELISIH'].sum():,}")
    
    st.dataframe(df_dash_filt, use_container_width=True)

# TAB 2: AUDIT PIVOT (URUTAN SEJAJAR)
with tab_prog:
    st.subheader("Monitoring Hasil Audit Per Item")
    q = st.text_input("🔍 Cari Barcode atau Nama Barang:", key="search_pivot")
    
    df_view = df_pivot
    if q:
        df_view = df_pivot[df_pivot['DESKRIPSI'].str.contains(q, case=False) | df_pivot['BARCODE_KODE'].astype(str).str.contains(q)]
    
    # Menampilkan kolom secara sejajar sesuai instruksi
    st.dataframe(
        df_view[['BARCODE_KODE', 'DESKRIPSI', 'LOKASI', 'QTYTEORI', 'P1', 'P2', 'P3', 'SELISIH']],
        use_container_width=True
    )

# TAB 3: RESUME PER TITIK
with tab_res:
    st.subheader("Ringkasan Progress Per Titik Lokasi")
    
    # Agregasi data per lokasi dari hasil audit
    df_res_loc = df_pivot.groupby('LOKASI').agg({
        'BARCODE_KODE': 'count',
        'QTYTEORI': 'sum',
        'SELISIH': 'sum'
    }).reset_index()
    
    df_res_loc.columns = ['LOKASI', 'JUMLAH_SKU', 'TOTAL_QTY_TEORI', 'TOTAL_SELISIH']
    
    st.dataframe(df_res_loc, use_container_width=True)

# CSS Footer Sederhana
st.markdown("""
    <style>
    footer {visibility: hidden;}
    .stApp {bottom: 10px;}
    </style>
    """, unsafe_allow_html=True)
