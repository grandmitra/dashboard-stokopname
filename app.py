import streamlit as st
import pandas as pd
import plotly.express as px

# 1. KONFIGURASI HALAMAN & LIMIT PANDAS
pd.set_option("styler.render.max_elements", 1000000)
st.set_page_config(page_title="Sistem Monitoring Stok Opname", layout="wide")

# 2. CSS KUSTOM (Fancy UI & Status Indicators)
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .status-box { padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .done { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .empty { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    .none { background-color: #e2e3e5; color: #383d41; border: 1px solid #d6d8db; }
    .card-lokasi { border-bottom: 1px solid #e6e9ef; padding: 12px 0; transition: 0.3s; }
    .card-lokasi:hover { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

# 3. FUNGSI LOAD DATA (Google Sheets)
@st.cache_data(ttl=600)
def load_data(sheet_name):
    sheet_id = "1mjjDF1ETjOB_eTI6ChI6dqvg0wf9aCa7cJwx0x2K3No"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    df = pd.read_csv(url, low_memory=False)
    # Mapping fillna sesuai kebutuhan
    if sheet_name == "database_stok":
        fill_values = {'DEPARTEMEN': 'Tanpa Dept', 'LOKASI': 'Tanpa Lokasi', 'STATUSSELISIH': 'Normal'}
        df = df.fillna(value=fill_values)
    return df

# 4. NAVIGASI TAB
tab1, tab2 = st.tabs(["📊 Executive Dashboard", "📋 Progress Monitoring"])

# ==========================================
# TAB 1: EXECUTIVE DASHBOARD
# ==========================================
with tab1:
    try:
        df_stok = load_data("database_stok")
        
        st.title("📦 Executive Dashboard")
        
        # --- SIDEBAR FILTER ---
        with st.sidebar:
            st.header("🎯 Filter Panel")
            all_dept = sorted(df_stok["DEPARTEMEN"].unique().tolist())
            dept_filter = st.multiselect("Pilih Departemen:", options=all_dept, default=all_dept)
            
            all_lokasi = sorted(df_stok["LOKASI"].unique().tolist())
            lokasi_filter = st.multiselect("Pilih Lokasi:", options=all_lokasi, default=all_lokasi)
            
            all_status = df_stok["STATUSSELISIH"].unique().tolist()
            status_filter = st.multiselect("Status Selisih:", options=all_status, default=all_status)

        # Apply Filter
        mask = df_stok["DEPARTEMEN"].isin(dept_filter) & \
               df_stok["LOKASI"].isin(lokasi_filter) & \
               df_stok["STATUSSELISIH"].isin(status_filter)
        df_selection = df_stok[mask]

        st.info(f"Menampilkan {len(df_selection):,} SKU berdasarkan filter.")

        # --- SCORECARDS ---
        c1, c2, c3, c4 = st.columns(4)
        val_selling = df_selection["VALSELLING"].sum()
        selisih_qty = df_selection["QTYSELISIH"].sum()
        selisih_val = df_selection["SELISIHVALSELLING"].sum()
        
        c1.metric("Total SKU", f"{len(df_selection):,}")
        c2.metric("Total Value (Selling)", f"Rp {val_selling:,.0f}")
        c3.metric("Total Selisih Qty", f"{selisih_qty:,}", delta_color="inverse")
        c4.metric("Total Selisih Value", f"Rp {selisih_val:,.0f}", delta_color="inverse")

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
                               title='<b>Proporsi Status Stok</b>', hole=0.5,
                               color_discrete_sequence=px.colors.qualitative.Safe)
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
        st.error(f"Gagal memuat Executive Dashboard: {e}")

# ==========================================
# TAB 2: PROGRESS MONITORING
# ==========================================
with tab2:
    try:
        df_audit = load_data("database_stokopname")
        st.title("🔍 Progress Monitoring Database")

        # Search Bar Lokasi
        search_loc = st.text_input("Cari Lokasi...", placeholder="Contoh: FD3008")

        if 'selected_lokasi' not in st.session_state:
            st.session_state.selected_lokasi = None

        # Header List
        st.markdown("---")
        h_col1, h_col2, h_col3 = st.columns([1, 4, 1])
        h_col1.markdown("**LOKASI**")
        h_col2.markdown("**INDIKATOR PROGRES & AGREGASI NILAI**")
        h_col3.markdown("**AKSI**")

        lokasi_list = sorted(df_audit["LOKASI"].unique())
        
        # Filter lokasi berdasarkan search bar
        if search_loc:
            lokasi_list = [l for l in lokasi_list if search_loc.upper() in l.upper()]

        for idx, loc in enumerate(lokasi_list):
            df_loc = df_audit[df_audit["LOKASI"] == loc]
            
            # --- LOGIKA STATUS DINAMIS P1, P2, P3 ---
            # P1: Done jika data QTYFISIK sudah terisi (tidak 0)
            qty_p1 = pd.to_numeric(df_loc['QTYFISIK'], errors='coerce').sum()
            p1_status = "DONE" if qty_p1 != 0 else "EMPTY"
            
            # P2 & P3: Berdasarkan ketersediaan data (Logika bisa disesuaikan kolom sheetmu)
            p2_status = "DONE" if p1_status == "DONE" else "EMPTY" # Contoh sinkronisasi P1 & P2
            p3_status = "NONE" # Default NONE jika belum ada input P3

            # Agregasi
            val_beli = pd.to_numeric(df_loc['VAL_SELISIH_BELI'], errors='coerce').sum()
            val_jual = pd.to_numeric(df_loc['VAL_SELISIH_JUAL'], errors='coerce').sum()
            
            with st.container():
                st.markdown('<div class="card-lokasi">', unsafe_allow_html=True)
                c_loc, c_prog, c_btn = st.columns([1, 4, 1])
                
                c_loc.markdown(f"**{loc}**")
                
                # Render Indikator ala UI referensi
                prog_html = f"""
                <span class="status-box {'done' if p1_status=='DONE' else 'empty'}">P1: {p1_status}</span> &nbsp;
                <span class="status-box {'done' if p2_status=='DONE' else 'empty'}">P2: {p2_status}</span> &nbsp;
                <span class="status-box {'done' if p3_status=='DONE' else 'none'}">P3: {p3_status}</span> &nbsp; | &nbsp;
                ITEMS: <b>{len(df_loc)}</b> &nbsp; | &nbsp; 
                VAL_BELI: <span style="color:{'red' if val_beli < 0 else 'green'}">{val_beli:,.0f}</span> &nbsp; | &nbsp;
                VAL_JUAL: <span style="color:{'red' if val_jual < 0 else 'green'}">{val_jual:,.0f}</span>
                """
                c_prog.markdown(prog_html, unsafe_allow_html=True)
                
                if c_btn.button("DETAIL COMPARE", key=f"btn_{loc}_{idx}", use_container_width=True):
                    st.session_state.selected_lokasi = loc
                st.markdown('</div>', unsafe_allow_html=True)

        # --- DETAIL PANEL (Audit Compare Report) ---
        if st.session_state.selected_lokasi:
            st.write("---")
            sel_loc = st.session_state.selected_lokasi
            d_col1, d_col2 = st.columns([4, 1])
            d_col1.subheader(f"📋 Audit Compare Report: {sel_loc}")
            if d_col2.button("❌ Tutup Detail", use_container_width=True):
                st.session_state.selected_lokasi = None
                st.rerun()

            df_detail = df_audit[df_audit["LOKASI"] == sel_loc]
            st.dataframe(
                df_detail, 
                use_container_width=True,
                column_config={
                    "VAL_SELISIH_BELI": st.column_config.NumberColumn("VAL_BELI", format="Rp %d"),
                    "VAL_SELISIH_JUAL": st.column_config.NumberColumn("VAL_JUAL", format="Rp %d"),
                    "QTYTEORI": "TEORI",
                    "QTYFISIK": "FISIK",
                    "QTYSELISIH": "SELISIH"
                }
            )

    except Exception as e:
        st.error(f"Gagal memuat Progress Monitoring: {e}")
