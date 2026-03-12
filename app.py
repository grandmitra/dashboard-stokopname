import streamlit as st
import pandas as pd
import numpy as np

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="SO System V16 - Fixed", layout="wide")

# CSS Kustom
st.markdown("""
    <style>
    .indicator-box { border-left: 4px solid #0d6efd; padding-left: 12px; margin-bottom: 5px; }
    .status-box { padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .done { background-color: #d4edda; color: #155724; }
    .empty { background-color: #f8d7da; color: #721c24; }
    .none { background-color: #e2e3e5; color: #383d41; }
    </style>
    """, unsafe_allow_html=True)

# FUNGSI MEMBERSIHKAN KOLOM SECARA TOTAL
def clean_columns(df):
    # 1. Ubah jadi string, buang spasi ujung, ubah ke UPPER
    df.columns = [str(c).strip().upper() for c in df.columns]
    # 2. Ganti spasi di tengah atau karakter aneh dengan underscore
    df.columns = df.columns.str.replace(r'[^A-Z0-9_]', '_', regex=True)
    # 3. Hilangkan double underscore jika ada
    df.columns = df.columns.str.replace(r'__+', '_', regex=True)
    return df

@st.cache_data(ttl=600)
def load_data(sheet_name):
    sheet_id = "1mjjDF1ETjOB_eTI6ChI6dqvg0wf9aCa7cJwx0x2K3No"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    df = pd.read_csv(url, low_memory=False)
    df = clean_columns(df)
    return df.fillna(0)

try:
    df_audit = load_data("database_stokopname")
    df_stok = load_data("database_stok")

    # VALIDASI KRUSIAL: Cek apakah BARCODE_KODE benar-benar ada
    # Jika nama kolomnya sedikit beda (misal: BARCODE saja), kita ganti namanya
    for dataframe in [df_audit, df_stok]:
        if 'BARCODE_KODE' not in dataframe.columns:
            # Cari kolom yang mengandung kata 'BARCODE'
            possible_cols = [c for c in dataframe.columns if 'BARCODE' in c]
            if possible_cols:
                dataframe.rename(columns={possible_cols[0]: 'BARCODE_KODE'}, inplace=True)

    tab1, tab2, tab3 = st.tabs(["📊 Executive", "📋 Monitoring", "🔍 Audit Compare"])

    with tab2:
        st.subheader("Progress Monitoring")
        # Kita pakai get() supaya tidak crash jika kolom LOKASI hilang
        lok_col = 'LOKASI' if 'LOKASI' in df_audit.columns else df_audit.columns[0]
        lokasi_unik = sorted(df_audit[lok_col].unique())
        
        search_q = st.text_input("Cari Lokasi...")
        if search_q:
            lokasi_unik = [l for l in lokasi_unik if search_q.upper() in str(l).upper()]

        for lok in lokasi_unik:
            rows = df_audit[df_audit[lok_col] == lok]
            # Pastikan kolom JENIS_PENGHITUNG ada
            jp_col = 'JENIS_PENGHITUNG' if 'JENIS_PENGHITUNG' in df_audit.columns else None
            if jp_col:
                types = rows[jp_col].astype(str).unique()
                hasP1, hasP2, hasP3 = "P1" in types, "P2" in types, "P3" in types
                
                with st.container():
                    c_loc, c_prog, c_btn = st.columns([1, 4, 1])
                    c_loc.write(f"**{lok}**")
                    c_prog.markdown(f"""
                        <div class="indicator-box">
                            P1: <span class="status-box {'done' if hasP1 else 'empty'}">{'DONE' if hasP1 else 'EMPTY'}</span> | 
                            P2: <span class="status-box {'done' if hasP2 else 'empty'}">{'DONE' if hasP2 else 'EMPTY'}</span> | 
                            P3: <span class="status-box {'done' if hasP3 else 'none'}">{'DONE' if hasP3 else 'NONE'}</span>
                        </div>""", unsafe_allow_html=True)
                    if c_btn.button("PILIH", key=f"btn_{lok}"):
                        st.session_state.selected_lokasi = lok
                        st.rerun()

    with tab3:
        if 'selected_lokasi' in st.session_state and st.session_state.selected_lokasi:
            lok = st.session_state.selected_lokasi
            st.subheader(f"Audit Compare: {lok}")
            
            data_lok = df_audit[df_audit[lok_col] == lok].copy()
            
            # PIVOT aman dengan verifikasi kolom
            if 'BARCODE_KODE' in data_lok.columns:
                df_pivot = data_lok.pivot_table(
                    index=['BARCODE_KODE', 'DESKRIPSI'],
                    columns='JENIS_PENGHITUNG',
                    values='QTYFISIK',
                    aggfunc='sum'
                ).reset_index().fillna(0)
                
                for p in ['P1', 'P2', 'P3']:
                    if p not in df_pivot.columns: df_pivot[p] = 0

                # MERGE dengan database stok
                df_final = pd.merge(df_pivot, df_stok, on='BARCODE_KODE', how='left', suffixes=('', '_REF')).fillna(0)
                
                # Tampilkan Tabel Hasil
                st.dataframe(df_final, use_container_width=True)
            else:
                st.error("Kolom BARCODE_KODE tidak ditemukan di data audit!")

            if st.button("Tutup"):
                st.session_state.selected_lokasi = None
                st.rerun()

except Exception as e:
    st.error(f"⚠️ Error Detail: {e}")
    st.info("Saran: Cek kembali nama kolom di Google Sheets, pastikan tidak ada karakter aneh di judul kolom.")
