import streamlit as st
import pandas as pd
import plotly.express as px

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="SO System V15 - Python Analytics", layout="wide")

# CSS Kustom
st.markdown("""
    <style>
    .indicator-box { border-left: 4px solid #0d6efd; padding-left: 12px; margin-bottom: 5px; }
    .status-box { padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .done { background-color: #d4edda; color: #155724; }
    .empty { background-color: #f8d7da; color: #721c24; }
    .none { background-color: #e2e3e5; color: #383d41; }
    .card-lokasi { border-bottom: 1px solid #e6e9ef; padding: 12px 0; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_data(sheet_name):
    sheet_id = "1mjjDF1ETjOB_eTI6ChI6dqvg0wf9aCa7cJwx0x2K3No"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    df = pd.read_csv(url, low_memory=False)
    # NORMALISASI: Hapus spasi di nama kolom dan ubah jadi UPPERCASE
    df.columns = [str(c).replace(" ", "").upper() for c in df.columns]
    return df.fillna(0)

try:
    # Memuat data utama
    df_audit = load_data("database_stokopname")
    df_stok = load_data("database_stok")

    tab1, tab2, tab3 = st.tabs(["📊 Executive Dashboard", "📋 Progress Monitoring", "🔍 Audit Compare"])

    with tab1:
        st.title("Executive Dashboard")
        st.write("Statistik Global")
        c1, c2 = st.columns(2)
        # Menghitung VALSELLING (Gunakan kolom yang sudah dinormalisasi)
        total_val = df_stok['VALSELLING'].sum() if 'VALSELLING' in df_stok.columns else 0
        c1.metric("Total Value Selling", f"Rp {total_val:,.0f}")
        c2.metric("Total SKU", len(df_stok))

    with tab2:
        st.subheader("Progress Monitoring Database")
        search_q = st.text_input("Cari Lokasi...", key="search_log")
        
        # Filter Lokasi
        lokasi_unik = sorted(df_audit["LOKASI"].unique()) if "LOKASI" in df_audit.columns else []
        if search_q:
            lokasi_unik = [l for l in lokasi_unik if search_q.upper() in str(l).upper()]

        for lok in lokasi_unik:
            rows = df_audit[df_audit["LOKASI"] == lok]
            types = rows["JENIS_PENGHITUNG"].astype(str).unique()
            hasP1, hasP2, hasP3 = "P1" in types, "P2" in types, "P3" in types
            
            countSKU = len(rows["BARCODE_KODE"].unique()) if "BARCODE_KODE" in rows.columns else 0
            # Gunakan VAL_SELISIH_JUAL jika VAL_SELISIH_BELI tidak ada
            col_val = "VAL_SELISIH_JUAL" if "VAL_SELISIH_JUAL" in rows.columns else "VALSELLING"
            sumVal = pd.to_numeric(rows[col_val], errors='coerce').sum() if col_val in rows.columns else 0

            with st.container():
                c_loc, c_prog, c_btn = st.columns([1, 4, 1])
                c_loc.markdown(f"**{lok}**")
                html_prog = f"""
                <div class="indicator-box">
                    P1: <span class="status-box {'done' if hasP1 else 'empty'}">{'DONE' if hasP1 else 'EMPTY'}</span> &nbsp;
                    P2: <span class="status-box {'done' if hasP2 else 'empty'}">{'DONE' if hasP2 else 'EMPTY'}</span> &nbsp;
                    P3: <span class="status-box {'done' if hasP3 else 'none'}">{'DONE' if hasP3 else 'NONE'}</span> &nbsp; | &nbsp;
                    ITEMS: <b>{countSKU}</b> &nbsp; | &nbsp;
                    VALUE: <b style="color:{'red' if sumVal < 0 else 'green'}">{sumVal:,.0f}</b>
                </div>
                """
                c_prog.markdown(html_prog, unsafe_allow_html=True)
                if c_btn.button("PILIH LOKASI", key=f"sel_{lok}"):
                    st.session_state.selected_lokasi = lok
                    st.rerun()

    with tab3:
        if 'selected_lokasi' in st.session_state and st.session_state.selected_lokasi:
            lok = st.session_state.selected_lokasi
            st.subheader(f"Audit Compare Report: {lok}")
            
            data_lok = df_audit[df_audit["LOKASI"] == lok].copy()
            
            # Pivot data QTY FISIK
            df_pivot = data_lok.pivot_table(
                index=['BARCODE_KODE', 'DESKRIPSI'],
                columns='JENIS_PENGHITUNG',
                values='QTYFISIK',
                aggfunc='first'
            ).reset_index().fillna(0)

            for p in ['P1', 'P2', 'P3']:
                if p not in df_pivot.columns: df_pivot[p] = 0

            # MAPPING KOLOM ACUAN (Menghindari Error Index)
            # Kita cari kolom yang paling mendekati jika nama aslinya tidak ada
            map_cols = {
                'QTYTEORI': 'QTYTEORI' if 'QTYTEORI' in df_stok.columns else ('STOK_SISTEM' if 'STOK_SISTEM' in df_stok.columns else None),
                'HARGA': 'HARGAJUAL' if 'HARGAJUAL' in df_stok.columns else ('VALSELLING' if 'VALSELLING' in df_stok.columns else None)
            }

            # Ambil kolom yang tersedia saja dari df_stok
            cols_to_merge = ['BARCODE_KODE']
            for v in map_cols.values():
                if v: cols_to_merge.append(v)
            
            df_final = pd.merge(df_pivot, df_stok[list(set(cols_to_merge))], on='BARCODE_KODE', how='left').fillna(0)

            def determine_status(row):
                q1, q2, q3 = row.get('P1', 0), row.get('P2', 0), row.get('P3', 0)
                if q3 != 0: return "DONE (P3)", q3, True
                if q1 != 0 and q2 != 0:
                    if q1 == q2: return "DONE (MATCH)", q1, True
                    return "RE-COUNT", 0, False
                return "INCOMPLETE", 0, False

            res = df_final.apply(determine_status, axis=1)
            df_final['STATUS'] = [x[0] for x in res]
            df_final['FINAL_QTY'] = [x[1] for x in res]
            df_final['IS_REVEALED'] = [x[2] for x in res]

            # Hitung Selisih
            teori_col = map_cols['QTYTEORI']
            if teori_col:
                df_final['SELISIH'] = df_final.apply(lambda x: x['FINAL_QTY'] - x[teori_col] if x['IS_REVEALED'] else 0, axis=1)
            
            st.dataframe(df_final, use_container_width=True)

            if st.button("Tutup Audit"):
                st.session_state.selected_lokasi = None
                st.rerun()
        else:
            st.warning("Pilih lokasi di tab Progress Monitoring.")

except Exception as e:
    st.error(f"Error Detail: {e}")
