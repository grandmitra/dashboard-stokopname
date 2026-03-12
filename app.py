import streamlit as st
import pandas as pd
import plotly.express as px

# Konfigurasi Dasar
pd.set_option("styler.render.max_elements", 1000000)
st.set_page_config(page_title="Sistem Monitoring Stok Opname", layout="wide")

@st.cache_data(ttl=300)
def load_data(sheet_name):
    sheet_id = "1mjjDF1ETjOB_eTI6ChI6dqvg0wf9aCa7cJwx0x2K3No"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(url, low_memory=False)

# Main App Navigation
tab1, tab2 = st.tabs(["📊 Executive Dashboard", "📋 Progress Monitoring"])

# ==========================================
# TAB 1: EXECUTIVE DASHBOARD
# ==========================================
with tab1:
    try:
        df_stok = load_data("database_stok")
        st.title("Executive Dashboard")
        
        # Sidebar Filter Khusus Dashboard
        st.sidebar.header("Filter Dashboard")
        depts = st.sidebar.multiselect("Departemen", df_stok["DEPARTEMEN"].unique(), df_stok["DEPARTEMEN"].unique())
        
        df_dash = df_stok[df_stok["DEPARTEMEN"].isin(depts)]
        
        # Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Total SKU", f"{len(df_dash):,}")
        m2.metric("Total Val Jual", f"Rp {df_dash['VALSELLING'].sum():,.0f}")
        m3.metric("Total Selisih", f"Rp {df_dash['SELISIHVALSELLING'].sum():,.0f}")
        
        # Chart
        fig = px.bar(df_dash.groupby("DEPARTEMEN")["SELISIHVALSELLING"].sum().reset_index(), 
                     x="DEPARTEMEN", y="SELISIHVALSELLING", title="Selisih per Departemen")
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Gagal memuat Database Stok: {e}")

# ==========================================
# TAB 2: PROGRESS MONITORING (Audit Report)
# ==========================================
with tab2:
    try:
        df_audit = load_data("database_stokopname")
        st.title("Progress Monitoring Database")
        
        # --- BAGIAN 1: RESUME PROGRES TIAP LOKASI ---
        st.subheader("📍 Resume Progres Lokasi")
        
        # Agregasi data per lokasi
        resume_lokasi = df_audit.groupby("LOKASI").agg({
            "BARCODE_KODE": "count",
            "VAL_SELISIH_BELI": "sum",
            "VAL_SELISIH_JUAL": "sum"
        }).reset_index()
        resume_lokasi.columns = ["LOKASI", "TOTAL ITEMS", "TOTAL SELISIH BELI", "TOTAL SELISIH JUAL"]
        
        # Menampilkan resume dengan gaya kartu list (seperti gambar 2)
        for index, row in resume_lokasi.iterrows():
            with st.container():
                cols = st.columns([1, 4, 1])
                cols[0].markdown(f"### **{row['LOKASI']}**")
                
                # Indikator visual sederhana
                info_text = f"📦 Items: **{row['TOTAL ITEMS']}** | 💰 Val Beli: `Rp {row['TOTAL SELISIH BELI']:,.0f}` | 🏷️ Val Jual: `Rp {row['TOTAL SELISIH JUAL']:,.0f}`"
                cols[1].info(info_text)
                
                if cols[2].button(f"Lihat Detail", key=f"btn_{row['LOKASI']}"):
                    st.write(f"Menampilkan detail untuk {row['LOKASI']}...")
        
        st.divider()

        # --- BAGIAN 2: AUDIT COMPARE REPORT (TABEL DETAIL) ---
        st.subheader("🔍 Audit Compare Report")
        
        # Pencarian & Filter di atas tabel
        search_col1, search_col2 = st.columns([3, 1])
        search_query = search_col1.text_input("Cari Deskripsi Barang atau Barcode...", "")
        filter_status = search_col2.selectbox("Filter Selisih", ["Semua", "Hanya Selisih", "Match"])

        # Filter Logic
        filtered_audit = df_audit.copy()
        if search_query:
            filtered_audit = filtered_audit[filtered_audit['DESKRIPSI'].str.contains(search_query, case=False) | 
                                            filtered_audit['BARCODE_KODE'].astype(str).str.contains(search_query)]
        
        if filter_status == "Hanya Selisih":
            filtered_audit = filtered_audit[filtered_audit['QTYSELISIH'] != 0]
        elif filter_status == "Match":
            filtered_audit = filtered_audit[filtered_audit['QTYSELISIH'] == 0]

        # Menampilkan Tabel Detail seperti Gambar 1
        st.dataframe(
            filtered_audit[[
                "LOKASI", "BARCODE_KODE", "DESKRIPSI", "QTYTEORI", "QTYFISIK", 
                "QTYSELISIH", "VAL_SELISIH_BELI", "VAL_SELISIH_JUAL", "NAMA_PETUGAS"
            ]],
            use_container_width=True,
            column_config={
                "QTYTEORI": st.column_config.NumberColumn("TEORI", format="%d", help="Stok di Sistem"),
                "QTYFISIK": st.column_config.NumberColumn("FISIK", format="%d", help="Hasil Hitung"),
                "QTYSELISIH": st.column_config.NumberColumn("SELISIH", format="%d"),
                "VAL_SELISIH_BELI": st.column_config.NumberColumn("VAL_BELI", format="Rp %d"),
                "VAL_SELISIH_JUAL": st.column_config.NumberColumn("VAL_JUAL", format="Rp %d"),
            }
        )
        
        # Tombol Export
        csv_audit = filtered_audit.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Result (CSV)", csv_audit, "audit_report.csv", "text/csv")

    except Exception as e:
        st.error(f"Gagal memuat Database Stok Opname: {e}")
