import streamlit as st
import pandas as pd
import plotly.express as px

# 1. KONFIGURASI GLOBAL
pd.set_option("styler.render.max_elements", 1000000)
st.set_page_config(page_title="Sistem Monitoring Stok Opname", layout="wide")

# CSS Kustom
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .status-box { padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .done { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .empty { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    .none { background-color: #e2e3e5; color: #383d41; border: 1px solid #d6d8db; }
    .card-lokasi { border-bottom: 1px solid #e6e9ef; padding: 12px 0; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_data(sheet_name):
    sheet_id = "1mjjDF1ETjOB_eTI6ChI6dqvg0wf9aCa7cJwx0x2K3No"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    df = pd.read_csv(url, low_memory=False)
    
    # FIX: Paksa kolom kunci menjadi String agar tidak error saat sorting/filter
    for col in ["LOKASI", "BARCODE_KODE", "DEPARTEMEN", "JENIS_PENGHITUNG"]:
        if col in df.columns:
            df[col] = df[col].astype(str).replace('0', '0').replace('nan', '-')
            
    return df.fillna(0)

try:
    df_stok = load_data("database_stok")
    df_audit = load_data("database_stokopname")

    tab1, tab2 = st.tabs(["📊 Executive Dashboard", "📋 Progress Monitoring"])

    # ==========================================
    # TAB 1: EXECUTIVE DASHBOARD
    # ==========================================
    with tab1:
        st.title("📦 Executive Dashboard")
        with st.sidebar:
            st.header("🎯 Filter Panel")
            # Gunakan sorted(list(set(...))) untuk memastikan data unik dan terurut sebagai string
            dept_f = st.multiselect("Departemen:", options=sorted(df_stok["DEPARTEMEN"].unique()), default=df_stok["DEPARTEMEN"].unique())
            lokasi_f = st.multiselect("Lokasi:", options=sorted(df_stok["LOKASI"].unique()), default=df_stok["LOKASI"].unique())
        
        mask = df_stok["DEPARTEMEN"].isin(dept_f) & df_stok["LOKASI"].isin(lokasi_f)
        df_dash = df_stok[mask]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total SKU", f"{len(df_dash):,}")
        c2.metric("Total Val Jual", f"Rp {pd.to_numeric(df_dash['VALSELLING'], errors='coerce').sum():,.0f}")
        c3.metric("Qty Selisih", f"{pd.to_numeric(df_dash['QTYSELISIH'], errors='coerce').sum():,}", delta_color="inverse")
        c4.metric("Val Selisih", f"Rp {pd.to_numeric(df_dash['SELISIHVALSELLING'], errors='coerce').sum():,.0f}", delta_color="inverse")
        
        st.plotly_chart(px.bar(df_dash.groupby("DEPARTEMEN")[["SELISIHVALSELLING"]].sum().reset_index(), x="SELISIHVALSELLING", y="DEPARTEMEN", orientation='h', title="Selisih per Dept"), use_container_width=True)

    # ==========================================
    # TAB 2: PROGRESS MONITORING
    # ==========================================
    with tab2:
        st.title("🔍 Progress Monitoring Database")
        search_loc = st.text_input("Cari Lokasi...", placeholder="Contoh: FD3008")

        if 'selected_lokasi' not in st.session_state:
            st.session_state.selected_lokasi = None

        # Ambil list lokasi unik dan pastikan semuanya string sebelum disortir
        lokasi_list = sorted([str(x) for x in df_audit["LOKASI"].unique()])
        
        if search_loc:
            lokasi_list = [l for l in lokasi_list if search_loc.upper() in l.upper()]

        # --- LIST LOKASI ---
        for idx, loc in enumerate(lokasi_list):
            df_loc = df_audit[df_audit["LOKASI"] == loc]
            
            # Cek status P1, P2, P3 sejajar dari kolom JENIS_PENGHITUNG
            tersedia = df_loc["JENIS_PENGHITUNG"].astype(str).unique()
            p1_stat = "DONE" if "P1" in tersedia else "EMPTY"
            p2_stat = "DONE" if "P2" in tersedia else "EMPTY"
            p3_stat = "DONE" if "P3" in tersedia else "NONE"

            val_jual = pd.to_numeric(df_loc['VAL_SELISIH_JUAL'], errors='coerce').sum()

            with st.container():
                st.markdown('<div class="card-lokasi">', unsafe_allow_html=True)
                c_loc, c_prog, c_btn = st.columns([1, 4, 1])
                c_loc.markdown(f"**{loc}**")
                
                prog_html = f"""
                <span class="status-box {'done' if p1_stat=='DONE' else 'empty'}">P1: {p1_stat}</span> &nbsp;
                <span class="status-box {'done' if p2_stat=='DONE' else 'empty'}">P2: {p2_stat}</span> &nbsp;
                <span class="status-box {'done' if p3_stat=='DONE' else 'none'}">P3: {p3_stat}</span> &nbsp; | &nbsp;
                ITEMS: <b>{len(df_loc['BARCODE_KODE'].unique())}</b> &nbsp; | &nbsp; 
                VAL_JUAL: <span style="color:{'red' if val_jual < 0 else 'green'}">Rp {val_jual:,.0f}</span>
                """
                c_prog.markdown(prog_html, unsafe_allow_html=True)
                
                if c_btn.button("DETAIL COMPARE", key=f"btn_{loc}_{idx}"):
                    st.session_state.selected_lokasi = loc
                st.markdown('</div>', unsafe_allow_html=True)

        # --- DETAIL PANEL (PIVOT P1, P2, P3 SEJAJAR) ---
        if st.session_state.selected_lokasi:
            st.divider()
            sel_loc = st.session_state.selected_lokasi
            st.subheader(f"📋 Audit Compare Report: {sel_loc}")
            
            df_det = df_audit[df_audit["LOKASI"] == sel_loc].copy()
            
            # Pastikan kolom QTYFISIK numerik sebelum pivot
            df_det['QTYFISIK'] = pd.to_numeric(df_det['QTYFISIK'], errors='coerce').fillna(0)
            
            # Proses Pivot agar P1, P2, P3 sejajar
            df_pivot = df_det.pivot_table(
                index=['BARCODE_KODE', 'DESKRIPSI', 'TITIKLOKASI', 'QTYTEORI'],
                columns='JENIS_PENGHITUNG',
                values='QTYFISIK',
                aggfunc='sum'
            ).reset_index().fillna(0)

            # Pastikan kolom P1, P2, P3 ada
            for p in ['P1', 'P2', 'P3']:
                if p not in df_pivot.columns:
                    df_pivot[p] = 0

            # Hitung Final (P2 prioritas, jika 0 pakai P1)
            df_pivot['FINAL'] = df_pivot.apply(lambda x: x['P2'] if x['P2'] != 0 else x['P1'], axis=1)
            df_pivot['SELISIH'] = df_pivot['FINAL'] - pd.to_numeric(df_pivot['QTYTEORI'], errors='coerce').fillna(0)

            st.dataframe(
                df_pivot[['BARCODE_KODE', 'DESKRIPSI', 'TITIKLOKASI', 'QTYTEORI', 'P1', 'P2', 'P3', 'FINAL', 'SELISIH']],
                use_container_width=True
            )
            
            if st.button("❌ Tutup Detail"):
                st.session_state.selected_lokasi = None
                st.rerun()

except Exception as e:
    st.error(f"Error Aplikasi: {e}")
