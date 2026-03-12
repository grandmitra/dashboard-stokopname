import streamlit as st
import pandas as pd
import plotly.express as px

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="SO System V14 - Fixed Logic", layout="wide")

st.markdown("""
    <style>
    .indicator-box { border-left: 4px solid #0d6efd; padding-left: 12px; margin-bottom: 5px; }
    .status-box { padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }
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
    # Bersihkan nama kolom dari spasi dan karakter aneh
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df

try:
    df_audit = load_data("database_stokopname")
    df_stok = load_data("database_stok")

    # --- SISTEM PENCARIAN KOLOM YANG LEBIH KUAT ---
    def get_column(df, keywords, default_name):
        for k in keywords:
            for col in df.columns:
                if k.upper() in col.upper():
                    return col
        return None

    # Cari kolom di database_stok
    COL_KODE = get_column(df_stok, ["KODE", "BARCODE", "SKU", "ITEM"], "BARCODE_KODE")
    COL_TEORI = get_column(df_stok, ["TEORI", "SALDO", "STOK", "QTY"], "QTYTEORI")
    COL_BELI = get_column(df_stok, ["BELI", "PURCHASE", "HBELI"], "HARGABELI")
    COL_JUAL = get_column(df_stok, ["JUAL", "SELLING", "HJUAL"], "HARGAJUAL")

    # Cek apakah ada kolom yang None
    missing_cols = [name for name, val in {"KODE": COL_KODE, "TEORI": COL_TEORI, "BELI": COL_BELI, "JUAL": COL_JUAL}.items() if val is None]

    if missing_cols:
        st.error(f"❌ Kolom berikut tidak ditemukan di sheet database_stok: {', '.join(missing_cols)}")
        st.info(f"Kolom yang tersedia saat ini: {list(df_stok.columns)}")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["📊 Executive Dashboard", "📋 Progress Monitoring", "🔍 Audit Compare"])

    # ==========================================
    # TAB 1: EXECUTIVE DASHBOARD
    # ==========================================
    with tab1:
        st.title("📦 Executive Dashboard")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total SKU", f"{len(df_stok):,}")
        
        # Konversi ke numerik untuk kalkulasi
        total_val = pd.to_numeric(df_stok[COL_JUAL], errors='coerce').sum()
        c2.metric("Total Value Jual", f"Rp {total_val:,.0f}")
        
        # Grafik sederhana
        if "DEPARTEMEN" in df_stok.columns:
            df_dept = df_stok.groupby("DEPARTEMEN")[COL_JUAL].sum().reset_index()
            st.plotly_chart(px.bar(df_dept, x="DEPARTEMEN", y=COL_JUAL, title="Value per Departemen"), use_container_width=True)

    # ==========================================
    # TAB 2: PROGRESS MONITORING
    # ==========================================
    with tab2:
        st.subheader("Progress Monitoring Database")
        search_q = st.text_input("Cari Lokasi...", key="search_log")
        
        lokasi_unik = sorted([str(l) for l in df_audit["LOKASI"].unique() if l != 0])
        if search_q:
            lokasi_unik = [l for l in lokasi_unik if search_q.upper() in l.upper()]

        for idx, lok in enumerate(lokasi_unik):
            rows = df_audit[df_audit["LOKASI"].astype(str) == lok]
            types = rows["JENIS_PENGHITUNG"].astype(str).unique()
            
            hasP1 = any("P1" in t.upper() for t in types)
            hasP2 = any("P2" in t.upper() for t in types)
            hasP3 = any("P3" in t.upper() for t in types)

            val_jual = pd.to_numeric(rows['VAL_SELISIH_JUAL'], errors='coerce').sum()

            with st.container():
                st.markdown('<div class="card-lokasi">', unsafe_allow_html=True)
                c_loc, c_prog, c_btn = st.columns([1, 4, 1])
                c_loc.markdown(f"**{lok}**")
                
                html_prog = f"""
                <div class="indicator-box">
                    P1: <span class="status-box {'done' if hasP1 else 'empty'}">{'DONE' if hasP1 else 'EMPTY'}</span> &nbsp;
                    P2: <span class="status-box {'done' if hasP2 else 'empty'}">{'DONE' if hasP2 else 'EMPTY'}</span> &nbsp;
                    P3: <span class="status-box {'done' if hasP3 else 'none'}">{'DONE' if hasP3 else 'NONE'}</span> &nbsp; | &nbsp;
                    ITEMS: <b>{len(rows['BARCODE_KODE'].unique())}</b> &nbsp; | &nbsp;
                    VAL_JUAL: <b style="color:{'red' if val_jual < 0 else 'green'}">{val_jual:,.0f}</b>
                </div>
                """
                c_prog.markdown(html_prog, unsafe_allow_html=True)
                
                if c_btn.button("PILIH LOKASI", key=f"sel_{lok}"):
                    st.session_state.selected_lokasi = lok
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # ==========================================
    # TAB 3: AUDIT COMPARE (Logika SO V14)
    # ==========================================
    with tab3:
        if 'selected_lokasi' in st.session_state and st.session_state.selected_lokasi:
            lok = st.session_state.selected_lokasi
            st.subheader(f"📋 Audit Compare Report: {lok}")
            
            # Data Transaksi
            df_det = df_audit[df_audit["LOKASI"].astype(str) == lok].copy()
            df_det['QTYFISIK'] = pd.to_numeric(df_det['QTYFISIK'], errors='coerce').fillna(0)

            # Pivot P1, P2, P3
            df_piv = df_det.pivot_table(
                index=['BARCODE_KODE', 'DESKRIPSI'],
                columns='JENIS_PENGHITUNG',
                values='QTYFISIK',
                aggfunc='sum'
            ).reset_index().fillna(0)

            for p in ['P1', 'P2', 'P3']:
                if p not in df_piv.columns: df_piv[p] = 0

            # Join dengan Acuan
            df_acuan = df_stok[[COL_KODE, COL_TEORI, COL_BELI, COL_JUAL]].copy()
            df_piv['BARCODE_KODE'] = df_piv['BARCODE_KODE'].astype(str)
            df_acuan[COL_KODE] = df_acuan[COL_KODE].astype(str)

            df_final = pd.merge(df_piv, df_acuan, left_on='BARCODE_KODE', right_on=COL_KODE, how='left').fillna(0)

            # Logika Status
            def get_status(row):
                q1, q2, q3 = row['P1'], row['P2'], row['P3']
                if q3 != 0: return "DONE (P3)", q3, True
                if q1 != 0 and q2 != 0:
                    if q1 == q2: return "DONE (MATCH)", q1, True
                    return "RE-COUNT", 0, False
                return "INCOMPLETE", 0, False

            status_res = df_final.apply(get_status, axis=1)
            df_final['STATUS'] = [x[0] for x in status_res]
            df_final['FINAL_QTY'] = [x[1] for x in status_res]
            df_final['OK'] = [x[2] for x in status_res]

            # Kalkulasi Selisih
            df_final['SELISIH'] = df_final.apply(lambda x: x['FINAL_QTY'] - x[COL_TEORI] if x['OK'] else 0, axis=1)
            df_final['VAL_BELI'] = df_final['SELISIH'] * df_final[COL_BELI]

            # Metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("SKU", len(df_final))
            m2.metric("MISMATCH", len(df_final[df_final['STATUS'] == "RE-COUNT"]))
            m3.metric("MATCHED", len(df_final[df_final['STATUS'].str.contains("DONE")]))

            st.dataframe(df_final[['BARCODE_KODE', 'DESKRIPSI', COL_TEORI, 'P1', 'P2', 'P3', 'FINAL_QTY', 'SELISIH', 'STATUS']], 
                         use_container_width=True)

            if st.button("❌ Tutup Detail"):
                st.session_state.selected_lokasi = None
                st.rerun()
        else:
            st.info("Pilih lokasi di Tab 2.")

except Exception as e:
    st.error(f"Terjadi Kesalahan Sistem: {e}")
