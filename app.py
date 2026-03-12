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
            st.markdown("""
                <div style='text-align: center; background-color: #ffffff; padding: 30px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);'>
                    <h2 style='color: #1f77b4;'>🔐 Restricted Access</h2>
                    <p style='color: #666;'>Sistem Monitoring Stok Opname</p>
                </div>
            """, unsafe_allow_html=True)
            st.text_input("Masukkan Password Aplikasi", type="password", on_change=password_entered, key="password")
            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.error("😕 Password salah. Silakan coba lagi.")
        return False
    return st.session_state["password_correct"]

if not check_password():
    st.stop()

# 3. CSS KUSTOM
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    [data-testid="stSidebar"] .stElementContainer button { width: 100% !important; }
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
    
    df_stok = df_stok.fillna({'DEPARTEMEN': 'Tanpa Dept', 'LOKASI': 'Tanpa Lokasi', 'STATUSSELISIH': 'Sesuai'})
    df_audit.columns = [str(c).strip().upper() for c in df_audit.columns]
    
    return df_stok, df_audit

try:
    df_stok, df_audit = load_all_data()

    # Pre-processing Numerik
    for col in ['QTYFISIK', 'QTYTEORI', 'VAL_SELISIH_JUAL', 'HARGA_JUAL']:
        if col in df_audit.columns:
            df_audit[col] = pd.to_numeric(df_audit[col], errors='coerce').fillna(0)
    
    # Tambahkan hitungan Nilai Teori (Harga Jual * Qty Teori)
    df_audit['VAL_TEORI'] = df_audit['HARGA_JUAL'] * df_audit['QTYTEORI']

    # Transformasi Pivot Dasar
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

    # Proteksi Kolom
    for p in ['P1', 'P2', 'P3']:
        if f'QTYFISIK_{p}' not in df_pivot.columns: df_pivot[f'QTYFISIK_{p}'] = 0
        if f'VAL_SELISIH_JUAL_{p}' not in df_pivot.columns: df_pivot[f'VAL_SELISIH_JUAL_{p}'] = 0
        if f'NAMA_PETUGAS_{p}' not in df_pivot.columns: df_pivot[f'NAMA_PETUGAS_{p}'] = "-"

    # Logika Final Per Item
    def process_logic(row):
        q1, q2, q3 = row['QTYFISIK_P1'], row['QTYFISIK_P2'], row['QTYFISIK_P3']
        v1, v2, v3 = row['VAL_SELISIH_JUAL_P1'], row['VAL_SELISIH_JUAL_P2'], row['VAL_SELISIH_JUAL_P3']
        
        # Final Fisik & Nilai Selisih
        final_f = q3 if q3 != 0 else (q1 if q1 != 0 else 0)
        final_v_selisih = v3 if q3 != 0 else (v1 if q1 != 0 else 0)
        
        # Gabungan Petugas
        all_n = [str(row['NAMA_PETUGAS_P1']), str(row['NAMA_PETUGAS_P2']), str(row['NAMA_PETUGAS_P3'])]
        clean_n = ', '.join(sorted(set([n for n in all_n if n not in ["-", "0", "0.0", "nan"]])))
        
        return final_f, final_v_selisih, clean_n

    df_pivot[['FINAL_FISIK', 'FINAL_VAL_SELISIH', 'GABUNGAN_PETUGAS']] = df_pivot.apply(
        lambda x: pd.Series(process_logic(x)), axis=1
    )

    # --- TABS ---
    tab_dash, tab_prog, tab_res = st.tabs(["📊 Dashboard", "📋 Progres Audit", "📡 Monitoring RESUME"])

    # TAB 1 & 2 tetap seperti sebelumnya (Skip detail untuk singkatnya)
    with tab_prog:
        st.dataframe(df_pivot, use_container_width=True)

    # ==========================================
    # TAB 3: MONITORING RESUME (ADVANCED)
    # ==========================================
    with tab_res:
        st.title("📡 Monitoring Resume Per Lokasi")

        # Agregasi Data Per Lokasi
        df_res_loc = df_pivot.groupby('LOKASI').agg({
            'BARCODE_KODE': 'count',
            'VAL_TEORI': 'sum',
            'VAL_SELISIH_JUAL_P3': 'sum',
            'FINAL_VAL_SELISIH': 'sum',
            'GABUNGAN_PETUGAS': lambda x: ', '.join(sorted(set(', '.join(x).split(', '))))
        }).reset_index()
        
        df_res_loc.columns = ['LOKASI', 'COUNT_SKU', 'TOTAL_VAL_TEORI', 'VAL_SELISIH_P3', 'TOTAL_SELISIH_FINAL', 'PETUGAS_LOKASI']
        
        # Cleaning Petugas String
        df_res_loc['PETUGAS_LOKASI'] = df_res_loc['PETUGAS_LOKASI'].str.strip(', ')

        # --- SCORE CARDS (VAL SELISIH) ---
        st.write("### 📈 Ringkasan Nilai Selisih (Final)")
        sc1, sc2, sc3 = st.columns(3)
        
        pos_val = df_res_loc[df_res_loc['TOTAL_SELISIH_FINAL'] > 0]['TOTAL_SELISIH_FINAL'].sum()
        neg_val = df_res_loc[df_res_loc['TOTAL_SELISIH_FINAL'] < 0]['TOTAL_SELISIH_FINAL'].sum()
        total_balance = df_res_loc['TOTAL_SELISIH_FINAL'].sum()

        sc1.metric("➕ Selisih Positif (Lebih)", f"Rp {pos_val:,.0f}", delta_color="normal")
        sc2.metric("➖ Selisih Negatif (Kurang)", f"Rp {neg_val:,.0f}", delta_color="inverse")
        sc3.metric("⚖️ Net Balance", f"Rp {total_balance:,.0f}")

        # --- FILTER RESUME ---
        st.markdown("---")
        f_col1, f_col2 = st.columns([1, 2])
        with f_col1:
            status_filter = st.radio("Filter Tipe Selisih:", ["Semua", "Hanya Selisih", "Balance (0)"], horizontal=True)
        
        # Logika Filter
        if status_filter == "Hanya Selisih":
            df_res_loc = df_res_loc[df_res_loc['TOTAL_SELISIH_FINAL'] != 0]
        elif status_filter == "Balance (0)":
            df_res_loc = df_res_loc[df_res_loc['TOTAL_SELISIH_FINAL'] == 0]

        # --- TABEL RESUME FINAL ---
        st.dataframe(
            df_res_loc,
            use_container_width=True,
            column_config={
                "COUNT_SKU": st.column_config.NumberColumn("Jml SKU", format="%d 📦"),
                "TOTAL_VAL_TEORI": st.column_config.NumberColumn("Val Teori", format="Rp %d"),
                "VAL_SELISIH_P3": st.column_config.NumberColumn("Val Selisih P3", format="Rp %d"),
                "TOTAL_SELISIH_FINAL": st.column_config.NumberColumn("Total Selisih", format="Rp %d"),
                "PETUGAS_LOKASI": st.column_config.TextColumn("👤 Petugas (Joined)")
            }
        )

except Exception as e:
    st.error(f"Terjadi kesalahan teknis: {e}")
