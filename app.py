import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Konfigurasi Global & Limit Render
pd.set_option("styler.render.max_elements", 1000000)
st.set_page_config(page_title="Sistem Monitoring Stok Opname", layout="wide")

# CSS Kustom untuk tampilan Fancy
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .status-box { padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .done { background-color: #d4edda; color: #155724; }
    .empty { background-color: #f8d7da; color: #721c24; }
    .none { background-color: #e2e3e5; color: #383d41; }
    .card-lokasi { border-bottom: 1px solid #e6e9ef; padding: 10px 0; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_data(sheet_name):
    sheet_id = "1mjjDF1ETjOB_eTI6ChI6dqvg0wf9aCa7cJwx0x2K3No"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    df = pd.read_csv(url, low_memory=False)
    fill_values = {'DEPARTEMEN': 'Tanpa Dept', 'LOKASI': 'Tanpa Lokasi', 'STATUSSELISIH': 'Sesuai'}
    return df.fillna(value=fill_values)

# Navigasi Tab
tab1, tab2 = st.tabs(["📊 Executive Dashboard", "📋 Progress Monitoring"])

# ==========================================
# TAB 1: EXECUTIVE DASHBOARD
# ==========================================
with tab1:
    try:
        df = load_data("database_stok")

        st.title("📦 Executive Dashboard")
        
        # --- SIDEBAR FILTER (Hanya muncul untuk Tab Eksekutif) ---
        with st.sidebar:
            st.header("🎯 Filter Panel")
            all_dept = sorted(df["DEPARTEMEN"].unique().tolist())
            dept_filter = st.multiselect("Pilih Departemen:", options=all_dept, default=all_dept)
            
            all_lokasi = sorted(df["LOKASI"].unique().tolist())
            lokasi_filter = st.multiselect("Pilih Lokasi:", options=all_lokasi, default=all_lokasi)
            
            all_status = df["STATUSSELISIH"].unique().tolist()
            status_filter = st.multiselect("Status Selisih:", options=all_status, default=all_status)

        mask = df["DEPARTEMEN"].isin(dept_filter) & df["LOKASI"].isin(lokasi_filter) & df["STATUSSELISIH"].isin(status_filter)
        df_selection = df[mask]

        st.info(f"Menampilkan {len(df_selection):,} SKU berdasarkan filter.")

        # --- SCORECARDS ---
        c1, c2, c3, c4 = st.columns(4)
        total_val_selling = df_selection["VALSELLING"].sum()
        total_selisih_qty = df_selection["QTYSELISIH"].sum()
        total_selisih_val = df_selection["SELISIHVALSELLING"].sum()
        
        c1.metric("Total SKU", f"{len(df_selection):,}")
        c2.metric("Total Value (Selling)", f"Rp {total_val_selling:,.0f}")
        c3.metric("Total Selisih Qty", f"{total_selisih_qty:,}", delta_color="inverse")
        c4.metric("Total Selisih Value", f"Rp {total_selisih_val:,.0f}", delta_color="inverse")

        st.markdown("---")

        # --- VISUALISASI ---
        col_l, col_r = st.columns([6, 4])
        with col_l:
            dept_sum = df_selection.groupby("DEPARTEMEN")[["SELISIHVALSELLING"]].sum().sort_values(by="SELISIHVALSELLING").reset_index()
            fig_dept = px.bar(dept_sum, x="SELISIHVALSELLING", y="DEPARTEMEN", orientation='h', 
                             title="<b>Selisih per Departemen</b>", color="SELISIHVALSELLING", color_continuous_scale="RdBu")
            st.plotly_chart(fig_dept, use_container_width=True)

        with col_r:
            fig_status = px.pie(df_selection, names='STATUSSELISIH', values='VALSELLING', 
                               title='<b>Persentase Status Stok</b>', hole=0.5)
            st.plotly_chart(fig_status, use_container_width=True)

        # --- TABEL DATA ---
        st.subheader("📋 Rincian Data")
        st.dataframe(df_selection, use_container_width=True, 
                     column_config={
                         "SELLING_PRICE": st.column_config.NumberColumn("Harga Jual", format="Rp %d"),
                         "VALSELLING": st.column_config.NumberColumn("Total Val", format="Rp %d"),
                         "QTYSELISIH": st.column_config.NumberColumn("Selisih", format="%d")
                     })

    except Exception as e:
        st.error(f"Error Eksekutif: {e}")

# ==========================================
# TAB 2: PROGRESS MONITORING
# ==========================================
with tab2:
    try:
        df_audit = load_data("database_stokopname")
        st.title("🔍 Progress Monitoring Database")

        if 'selected_lokasi' not in st.session_state:
            st.session_state.selected_lokasi = None

        # List Lokasi Resume
        h_col1, h_col2, h_col3 = st.columns([1, 4, 1])
        h_col1.caption("LOKASI")
        h_col2.caption("INDIKATOR & AGREGASI")
        h_col3.caption("AKSI")

        lokasi_list = sorted(df_audit["LOKASI"].unique())
        for idx, loc in enumerate(lokasi_list):
            df_loc = df_audit[df_audit["LOKASI"] == loc]
            
            # Logic Status Dummy (Bisa Anda ganti dengan kolom asli)
            p1 = "DONE" if len(df_loc) > 0 else "EMPTY"
            p2 = "EMPTY" 
            
            val_beli = pd.to_numeric(df_loc['VAL_SELISIH_BELI'], errors='coerce').sum()
            
            with st.container():
                st.markdown('<div class="card-lokasi">', unsafe_allow_html=True)
                c_loc, c_prog, c_btn = st.columns([1, 4, 1])
                c_loc.markdown(f"**{loc}**")
                
                prog_html = f"""
                <span class="status-box {'done' if p1=='DONE' else 'empty'}">P1: {p1}</span> &nbsp;
                <span class="status-box {'done' if p2=='DONE' else 'empty'}">P2: {p2}</span> &nbsp;
                <span class="status-box none">P3: NONE</span> &nbsp; | &nbsp;
                ITEMS: <b>{len(df_loc)}</b> &nbsp; | &nbsp; 
                VAL_BELI: <span style="color:{'red' if val_beli < 0 else 'green'}">{val_beli:,.0f}</span>
                """
                c_prog.markdown(prog_html, unsafe_allow_html=True)
                
                if c_btn.button("DETAIL COMPARE", key=f"btn_{loc}_{idx}"):
                    st.session_state.selected_lokasi = loc
                st.markdown('</div>', unsafe_allow_html=True)

        # Tampilan Detail jika lokasi diklik
        if st.session_state.selected_lokasi:
            st.markdown("---")
            st.subheader(f"Audit Compare Report: {st.session_state.selected_lokasi}")
            df_det = df_audit[df_audit["LOKASI"] == st.session_state.selected_lokasi]
            st.dataframe(df_det, use_container_width=True)
            if st.button("Tutup Detail"):
                st.session_state.selected_lokasi = None
                st.rerun()

    except Exception as e:
        st.error(f"Error Progress: {e}")
