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
            st.markdown("<div style='text-align: center;'><h2>🔐 Restricted Access</h2></div>", unsafe_allow_html=True)
            st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    return st.session_state["password_correct"]

if not check_password():
    st.stop()

# 3. CSS KUSTOM
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
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
    
    df_stok = df_stok.fillna({'DEPARTEMEN': 'Tanpa Dept', 'LOKASI': 'Tanpa Lokasi'})
    df_audit.columns = [str(c).strip().upper() for c in df_audit.columns]
    
    return df_stok, df_audit

try:
    df_stok, df_audit = load_all_data()

    # Pre-processing Numerik
    col_harga = "HARGAJUAL" if "HARGAJUAL" in df_audit.columns else "HARGA_JUAL"
    for col in ['QTYFISIK', 'QTYTEORI', 'VAL_SELISIH_JUAL', col_harga]:
        if col in df_audit.columns:
            df_audit[col] = pd.to_numeric(df_audit[col], errors='coerce').fillna(0)
    
    # Hitung Nilai Teori
    df_audit['VAL_TEORI'] = df_audit[col_harga] * df_audit['QTYTEORI']

    # Transformasi Pivot
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

    # Pastikan Kolom P1-P3 ada
    for p in ['P1', 'P2', 'P3']:
        for f in ['QTYFISIK', 'VAL_SELISIH_JUAL', 'NAMA_PETUGAS']:
            if f"{f}_{p}" not in df_pivot.columns:
                df_pivot[f"{f}_{p}"] = 0 if f != 'NAMA_PETUGAS' else "-"

    # Logika Final Per Item
    def process_logic(row):
        q1, q2, q3 = row['QTYFISIK_P1'], row['QTYFISIK_P2'], row['QTYFISIK_P3']
        v1, v3 = row['VAL_SELISIH_JUAL_P1'], row['VAL_SELISIH_JUAL_P3']
        
        # Final Fisik (Prioritas P3)
        final_f = q3 if q3 != 0 else (q1 if q1 != 0 else 0)
        final_v = v3 if q3 != 0 else (v1 if q1 != 0 else 0)
        
        # Gabungan Petugas
        all_n = [str(row['NAMA_PETUGAS_P1']), str(row['NAMA_PETUGAS_P2']), str(row['NAMA_PETUGAS_P3'])]
        clean_n = ', '.join(sorted(set([n for n in all_n if n not in ["-", "0", "0.0", "nan", "None"]])))
        
        return final_f, final_v, clean_n

    df_pivot[['FINAL_FISIK', 'FINAL_VAL_SELISIH', 'PETUGAS_JOIN']] = df_pivot.apply(
        lambda x: pd.Series(process_logic(x)), axis=1
    )

    tab_dash, tab_prog, tab_res = st.tabs(["📊 Dashboard", "📋 Progres Audit", "📡 Monitoring RESUME"])

    # --- TAB DASHBOARD ---
    with tab_dash:
        st.title("📦 Executive Summary")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total SKU", f"{len(df_stok):,}")
        c2.metric("Total Value", f"Rp {df_stok['VALSELLING'].sum():,.0f}")
        c3.metric("Total Selisih (Qty)", f"{df_stok['QTYSELISIH'].sum():,}")
        st.dataframe(df_stok, use_container_width=True)

    # --- TAB PROGRES ---
    with tab_prog:
        st.title("📋 Detail Per Item")
        s_query = st.text_input("🔍 Cari Barcode/Deskripsi:", key="p_search")
        if s_query:
            df_filt = df_pivot[df_pivot["DESKRIPSI"].str.contains(s_query, case=False) | df_pivot["BARCODE_KODE"].astype(str).str.contains(s_query)]
            st.dataframe(df_filt.head(1000), use_container_width=True)
        else:
            st.info("Gunakan kolom pencarian di atas untuk menampilkan detail data.")

    # --- TAB RESUME (FINAL REQUEST) ---
    with tab_res:
        st.title("📡 Monitoring Resume Per Lokasi")

        # Agregasi per Lokasi
        df_res_loc = df_pivot.groupby('LOKASI').agg({
            'BARCODE_KODE': 'count',
            'VAL_TEORI': 'sum',
            'VAL_SELISIH_JUAL_P3': 'sum',
            'FINAL_VAL_SELISIH': 'sum',
            'PETUGAS_JOIN': lambda x: ', '.join(sorted(set(', '.join(x).split(', '))))
        }).reset_index()

        df_res_loc.columns = ['LOKASI', 'COUNT_SKU', 'TOT_VAL_TEORI', 'VAL_P3', 'TOT_SELISIH', 'PETUGAS']
        df_res_loc['PETUGAS'] = df_res_loc['PETUGAS'].str.strip(', ')

        # --- SCORE CARDS ---
        sc1, sc2, sc3 = st.columns(3)
        pos = df_res_loc[df_res_loc['TOT_SELISIH'] > 0]['TOT_SELISIH'].sum()
        neg = df_res_loc[df_res_loc['TOT_SELISIH'] < 0]['TOT_SELISIH'].sum()
        
        sc1.metric("➕ Selisih Positif", f"Rp {pos:,.0f}")
        sc2.metric("➖ Selisih Negatif", f"Rp {neg:,.0f}", delta_color="inverse")
        sc3.metric("⚖️ Net Balance", f"Rp {df_res_loc['TOT_SELISIH'].sum():,.0f}")

        # --- FILTER & TABLE ---
        f_type = st.radio("Filter Tabel:", ["Semua", "Hanya Selisih", "Balance (0)"], horizontal=True)
        if f_type == "Hanya Selisih": df_res_loc = df_res_loc[df_res_loc['TOT_SELISIH'] != 0]
        elif f_type == "Balance (0)": df_res_loc = df_res_loc[df_res_loc['TOT_SELISIH'] == 0]

        st.dataframe(df_res_loc, use_container_width=True, column_config={
            "TOT_VAL_TEORI": st.column_config.NumberColumn("Val Teori", format="Rp %d"),
            "VAL_P3": st.column_config.NumberColumn("Val P3", format="Rp %d"),
            "TOT_SELISIH": st.column_config.NumberColumn("Total Selisih", format="Rp %d")
        })

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
