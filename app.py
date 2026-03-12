import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="SO System V14 - Python Analytics", layout="wide")

# CSS untuk menyamakan style GAS (Indicator Box & Badges)
st.markdown("""
    <style>
    .indicator-box { border-left: 4px solid #0d6efd; padding-left: 12px; margin-bottom: 5px; }
    .status-box { padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .done { background-color: #d4edda; color: #155724; }
    .empty { background-color: #f8d7da; color: #721c24; }
    .none { background-color: #e2e3e5; color: #383d41; }
    .re-count { background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
    .card-lokasi { border-bottom: 1px solid #e6e9ef; padding: 12px 0; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_data(sheet_name):
    sheet_id = "1mjjDF1ETjOB_eTI6ChI6dqvg0wf9aCa7cJwx0x2K3No"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(url, low_memory=False).fillna(0)

try:
    # Memuat data utama
    df_audit = load_data("database_stokopname")
    df_stok = load_data("database_stok") # Sebagai acuan_stok_opname di GAS

    tab1, tab2, tab3 = st.tabs(["📊 Executive Dashboard", "📋 Progress Monitoring", "🔍 Audit Compare"])

    # --- TAB 1 & 2 (Diringkas agar fokus ke Logika Progres) ---
    with tab1:
        st.title("Executive Dashboard")
        # ... (Logika visualisasi seperti sebelumnya)

    # --- TAB 2: PROGRESS MONITORING (Sesuai Logika renderLogMaster di GAS) ---
    with tab2:
        st.subheader("Progress Monitoring Database")
        search_q = st.text_input("Cari Lokasi...", key="search_log")
        
        lokasi_unik = sorted(df_audit["LOKASI"].unique())
        if search_q:
            lokasi_unik = [l for l in lokasi_unik if search_q.upper() in str(l).upper()]

        for idx, lok in enumerate(lokasi_unik):
            rows = df_audit[df_audit["LOKASI"] == lok]
            
            # LOGIKA GAS: hasP1, hasP2, hasP3
            types = rows["JENIS_PENGHITUNG"].astype(str).unique()
            hasP1 = "P1" in types
            hasP2 = "P2" in types
            hasP3 = "P3" in types

            # Agregasi
            countSKU = len(rows["BARCODE_KODE"].unique())
            sumValBeli = pd.to_numeric(rows["VAL_SELISIH_BELI"], errors='coerce').sum()

            with st.container():
                st.markdown(f'<div class="card-lokasi">', unsafe_allow_html=True)
                c_loc, c_prog, c_btn = st.columns([1, 4, 1])
                c_loc.markdown(f"**{lok}**")
                
                # HTML Indicator Box (Meniru GAS)
                html_prog = f"""
                <div class="indicator-box">
                    P1: <span class="status-box {'done' if hasP1 else 'empty'}">{'DONE' if hasP1 else 'EMPTY'}</span> &nbsp;
                    P2: <span class="status-box {'done' if hasP2 else 'empty'}">{'DONE' if hasP2 else 'EMPTY'}</span> &nbsp;
                    P3: <span class="status-box {'done' if hasP3 else 'none'}">{'DONE' if hasP3 else 'NONE'}</span> &nbsp; | &nbsp;
                    ITEMS: <b>{countSKU}</b> &nbsp; | &nbsp;
                    VAL_BELI: <b style="color:{'red' if sumValBeli < 0 else 'green'}">{sumValBeli:,.0f}</b>
                </div>
                """
                c_prog.markdown(html_prog, unsafe_allow_html=True)
                
                if c_btn.button("PILIH LOKASI", key=f"sel_{lok}"):
                    st.session_state.selected_lokasi = lok
                st.markdown('</div>', unsafe_allow_html=True)

    # --- TAB 3: AUDIT COMPARE (Logika showAudit & renderDetailTable di GAS) ---
    with tab3:
        if 'selected_lokasi' in st.session_state and st.session_state.selected_lokasi:
            lok = st.session_state.selected_lokasi
            st.subheader(f"Audit Compare Report: {lok}")
            
            # Filter data khusus lokasi terpilih
            data_lok = df_audit[df_audit["LOKASI"] == lok].copy()
            
            # PIVOT data agar P1, P2, P3 sejajar (Logika renderDetailTable)
            df_pivot = data_lok.pivot_table(
                index=['BARCODE_KODE', 'DESKRIPSI', 'TITIKLOKASI'],
                columns='JENIS_PENGHITUNG',
                values='QTYFISIK',
                aggfunc='first'
            ).reset_index().fillna(0)

            # Pastikan kolom tersedia
            for p in ['P1', 'P2', 'P3']:
                if p not in df_pivot.columns: df_pivot[p] = 0

            # Gabungkan dengan QTY TEORI dari acuan (df_stok)
            df_final = pd.merge(df_pivot, df_stok[['BARCODE_KODE', 'QTYTEORI', 'HARGABELI', 'HARGAJUAL']], on='BARCODE_KODE', how='left').fillna(0)

            # --- LOGIKA PENENTUAN STATUS (INTI DARI SCRIPT GAS ANDA) ---
            def determine_status(row):
                q1, q2, q3 = row['P1'], row['P2'], row['P3']
                
                if q3 != 0:
                    return "DONE (P3)", q3, True
                elif q1 != 0 and q2 != 0:
                    if q1 == q2:
                        return "DONE (MATCH)", q1, True
                    else:
                        return "RE-COUNT", 0, False
                else:
                    return "INCOMPLETE", 0, False

            # Terapkan fungsi logika
            res = df_final.apply(determine_status, axis=1)
            df_final['STATUS'] = [x[0] for x in res]
            df_final['FINAL_QTY'] = [x[1] for x in res]
            df_final['IS_REVEALED'] = [x[2] for x in res]

            # Hitung Selisih & Value
            df_final['SELISIH'] = df_final.apply(lambda x: x['FINAL_QTY'] - x['QTYTEORI'] if x['IS_REVEALED'] else 0, axis=1)
            df_final['VAL_BELI'] = df_final['SELISIH'] * df_final['HARGABELI']

            # Metrik Summary
            m1, m2, m3 = st.columns(3)
            m1.metric("TOTAL SKU", len(df_final))
            m2.metric("MISMATCH (RE-COUNT)", len(df_final[df_final['STATUS'] == "RE-COUNT"]))
            m3.metric("MATCH DONE", len(df_final[df_final['STATUS'].str.contains("DONE")]))

            # Filter Tampilan (Sesuai fltrAudit di GAS)
            view_opt = st.radio("Tampilkan:", ["Semua SKU", "Mismatch Saja (RE-COUNT)"], horizontal=True)
            if "Mismatch" in view_opt:
                df_final = df_final[df_final['STATUS'] == "RE-COUNT"]

            # Style DataFrame
            def style_status(val):
                if val == "RE-COUNT": return 'background-color: #fff3cd'
                if "DONE" in str(val): return 'background-color: #d4edda'
                return ''

            st.dataframe(
                df_final[['BARCODE_KODE', 'DESKRIPSI', 'QTYTEORI', 'P1', 'P2', 'P3', 'FINAL_QTY', 'SELISIH', 'VAL_BELI', 'STATUS']],
                use_container_width=True,
                column_config={
                    "QTYTEORI": st.column_config.NumberColumn("TEORI", help="Data Sensor di GAS jika belum match"),
                    "FINAL_QTY": "FINAL",
                    "VAL_BELI": st.column_config.NumberColumn("VAL BELI", format="Rp %d")
                }
            )

            if st.button("Tutup Audit"):
                st.session_state.selected_lokasi = None
                st.rerun()
        else:
            st.warning("Silakan pilih lokasi di tab 'Progress Monitoring' terlebih dahulu.")

except Exception as e:
    st.error(f"Error: {e}")
