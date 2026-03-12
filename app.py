import streamlit as st
import pandas as pd
import plotly.express as px

# Konfigurasi
pd.set_option("styler.render.max_elements", 1000000)
st.set_page_config(page_title="Monitoring Stok Opname", layout="wide")

# CSS untuk styling Progress (DONE/EMPTY/NONE)
st.markdown("""
<style>
    .status-box { padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .done { background-color: #d4edda; color: #155724; }
    .empty { background-color: #f8d7da; color: #721c24; }
    .none { background-color: #e2e3e5; color: #383d41; }
    .card-lokasi { border-bottom: 1px solid #e6e9ef; padding: 10px 0; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data(sheet_name):
    sheet_id = "1mjjDF1ETjOB_eTI6ChI6dqvg0wf9aCa7cJwx0x2K3No"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(url, low_memory=False).fillna("-")

try:
    # Load data dari kedua sheet
    df_stok = load_data("database_stok")
    df_audit = load_data("database_stokopname")

    tab1, tab2 = st.tabs(["📊 Executive Dashboard", "📋 Progress Monitoring"])

    # --- TAB 1: EXECUTIVE DASHBOARD ---
    with tab1:
        st.title("Executive Dashboard")
        st.sidebar.header("Filter Dashboard")
        depts = st.sidebar.multiselect("Filter Departemen", df_stok["DEPARTEMEN"].unique(), df_stok["DEPARTEMEN"].unique())
        df_dash = df_stok[df_stok["DEPARTEMEN"].isin(depts)]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total SKU", f"{len(df_dash):,}")
        c2.metric("Total Val Jual", f"Rp {pd.to_numeric(df_dash['VALSELLING'], errors='coerce').sum():,.0f}")
        c3.metric("Total Selisih", f"Rp {pd.to_numeric(df_dash['SELISIHVALSELLING'], errors='coerce').sum():,.0f}")
        
        st.plotly_chart(px.bar(df_dash.groupby("DEPARTEMEN")["VALSELLING"].sum().reset_index(), x="DEPARTEMEN", y="VALSELLING"), use_container_width=True)

    # --- TAB 2: PROGRESS MONITORING ---
    with tab2:
        st.subheader("Progress Monitoring Database")
        
        # State management untuk menyimpan lokasi yang dipilih
        if 'selected_lokasi' not in st.session_state:
            st.session_state.selected_lokasi = None

        # Container untuk List Lokasi
        with st.container():
            # Header List
            h_col1, h_col2, h_col3 = st.columns([1, 4, 1])
            h_col1.caption("LOKASI")
            h_col2.caption("INDIKATOR PROGRES & AGREGASI NILAI")
            h_col3.caption("AKSI")

            # Ambil resume unik per lokasi
            lokasi_list = df_audit["LOKASI"].unique()
            
            for loc in lokasi_list:
                df_loc = df_audit[df_audit["LOKASI"] == loc]
                
                # Hitung Agregasi (Contoh logika penentuan status P1-P3)
                # Anda bisa menyesuaikan kolom ini dengan data asli jika ada di sheet
                p1_status = "DONE" if len(df_loc) > 0 else "EMPTY"
                p2_status = "DONE" if index % 2 == 0 else "EMPTY" # Contoh logic dummy
                
                with st.container():
                    st.markdown(f'<div class="card-lokasi">', unsafe_allow_html=True)
                    c_loc, c_prog, c_btn = st.columns([1, 4, 1])
                    
                    c_loc.markdown(f"**{loc}**")
                    
                    # Tampilan Indikator P1, P2, P3
                    prog_html = f"""
                    <span class="status-box {'done' if p1_status=='DONE' else 'empty'}">P1: {p1_status}</span> &nbsp;
                    <span class="status-box {'done' if p2_status=='DONE' else 'empty'}">P2: {p2_status}</span> &nbsp;
                    <span class="status-box none">P3: NONE</span> &nbsp; | &nbsp;
                    ITEMS: <b>{len(df_loc)}</b> &nbsp; | &nbsp; 
                    VAL_BELI: <span style="color:red">Rp {pd.to_numeric(df_loc['VAL_SELISIH_BELI'], errors='coerce').sum():,.0f}</span>
                    """
                    c_prog.markdown(prog_html, unsafe_allow_html=True)
                    
                    if c_btn.button("DETAIL COMPARE", key=f"btn_{loc}"):
                        st.session_state.selected_lokasi = loc
                    st.markdown('</div>', unsafe_allow_html=True)

        st.divider()

        # --- BAGIAN DETAIL: AUDIT COMPARE REPORT ---
        if st.session_state.selected_lokasi:
            sel_loc = st.session_state.selected_lokasi
            st.subheader(f"Audit Compare Report - Lokasi: {sel_loc}")
            
            df_filtered = df_audit[df_audit["LOKASI"] == sel_loc]
            
            # Format Tabel seperti Gambar 1
            st.dataframe(
                df_filtered,
                use_container_width=True,
                column_order=(
                    "BARCODE_KODE", "DESKRIPSI", "TITIKLOKASI", "SEBARANLOKASI", 
                    "QTYTEORI", "QTYFISIK", "QTYSELISIH", "VAL_SELISIH_BELI", "KETERANGAN"
                ),
                column_config={
                    "BARCODE_KODE": "KODE",
                    "QTYTEORI": st.column_config.NumberColumn("TEORI", format="%d"),
                    "QTYFISIK": st.column_config.NumberColumn("FISIK", format="%d"),
                    "QTYSELISIH": st.column_config.NumberColumn("SELISIH", format="%d"),
                    "VAL_SELISIH_BELI": st.column_config.NumberColumn("VAL_BELI", format="Rp %d"),
                }
            )
            
            if st.button("Tutup Detail"):
                st.session_state.selected_lokasi = None
                st.rerun()

except Exception as e:
    st.error(f"Error: {e}")
