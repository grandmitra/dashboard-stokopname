import streamlit as st
import pandas as pd
import numpy as np
import io

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="SO System V16 - Grand Mitra", layout="wide")

# CSS Kustom untuk UI yang elegan & scannable
st.markdown("""
    <style>
    .card-lokasi {
        border: 1px solid #e6e9ef;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
        background-color: #ffffff;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .status-box { padding: 3px 10px; border-radius: 4px; font-weight: bold; font-size: 11px; display: inline-block; }
    .done { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .empty { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    .none { background-color: #e2e3e5; color: #383d41; border: 1px solid #d6d8db; }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNGSI DATA DENGAN LOCAL STORAGE CACHE (PERSIST)
def clean_columns(df):
    df.columns = [str(c).strip().upper() for c in df.columns]
    df.columns = df.columns.str.replace(r'[^A-Z0-9_]', '_', regex=True)
    df.columns = df.columns.str.replace(r'__+', '_', regex=True)
    return df

# persist="disk" akan menyimpan cache di penyimpanan lokal untuk mempercepat loading berikutnya
@st.cache_data(ttl=300, persist="disk") 
def load_data(sheet_name):
    try:
        sheet_id = "1mjjDF1ETjOB_eTI6ChI6dqvg0wf9aCa7cJwx0x2K3No"
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        df = pd.read_csv(url, low_memory=False)
        df = clean_columns(df)
        return df.fillna(0)
    except Exception as e:
        st.error(f"Gagal memuat sheet {sheet_name}: {e}")
        return pd.DataFrame()

# 3. LOGIKA UTAMA
try:
    # Mengambil data (Jika sudah ada di cache, akan instan)
    df_audit = load_data("database_stokopname")
    df_stok = load_data("database_stok")
    df_acuan = load_data("acuan_stok_opname")

    # Standarisasi Kolom Utama
    for df_check in [df_audit, df_stok, df_acuan]:
        if not df_check.empty:
            if 'BARCODE_KODE' not in df_check.columns:
                possible = [c for c in df_check.columns if 'BARCODE' in c]
                if possible: df_check.rename(columns={possible[0]: 'BARCODE_KODE'}, inplace=True)
            if 'LOKASI' not in df_check.columns:
                possible_l = [c for c in df_check.columns if 'LOKASI' in c or 'AREA' in c]
                if possible_l: df_check.rename(columns={possible_l[0]: 'LOKASI'}, inplace=True)

    # --- PENGUNCI URUTAN (SEQUENCE) ---
    if not df_audit.empty:
        df_order = df_audit.reset_index().groupby('BARCODE_KODE')['index'].min().reset_index()
        df_order.rename(columns={'index': 'SEQ_ORDER'}, inplace=True)
        
        df_sebaran = df_audit.groupby('BARCODE_KODE')['LOKASI'].apply(lambda x: ', '.join(sorted(set(x.astype(str))))).reset_index()
        df_sebaran.rename(columns={'LOKASI': 'SEBARAN_LOKASI'}, inplace=True)
    else:
        df_order = pd.DataFrame(columns=['BARCODE_KODE', 'SEQ_ORDER'])
        df_sebaran = pd.DataFrame(columns=['BARCODE_KODE', 'SEBARAN_LOKASI'])

    # DEFINISI TAB
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Executive", "📋 Monitoring", "🔍 Audit Compare", "🚀 Progres & Apps", "🔍 Detail Barang", "📈 Track Live"
    ])

    # Tombol Refresh Cache Manual jika data di Google Sheet berubah drastis
    with st.sidebar:
        if st.button("🔄 Clear Cache & Refresh Data"):
            st.cache_data.clear()
            st.rerun()

    # --- TAB 1: EXECUTIVE ---
    with tab1:
        st.subheader("📍 Quick Filter Lokasi (Master Stok)")
        search_l = st.text_input("Cari Lokasi di Database Stok:")
        if not df_stok.empty:
            df_disp = df_stok[df_stok['LOKASI'].astype(str).str.contains(search_l, case=False)] if search_l else df_stok.head(100)
            st.dataframe(df_disp, use_container_width=True)

    # --- TAB 2: MONITORING ---
    with tab2:
        st.subheader("Progress Monitoring Per Titik")
        if not df_audit.empty:
            lokasi_unik = sorted(df_audit['LOKASI'].unique())
            search_q = st.text_input("Filter Nama Lokasi di Monitoring...")
            if search_q:
                lokasi_unik = [l for l in lokasi_unik if search_q.upper() in str(l).upper()]

            for idx, lok in enumerate(lokasi_unik):
                df_loc = df_audit[df_audit['LOKASI'] == lok].copy()
                types = df_loc['JENIS_PENGHITUNG'].astype(str).unique()
                p1_s, p2_s, p3_s = ("DONE" if "P1" in types else "EMPTY"), ("DONE" if "P2" in types else "EMPTY"), ("DONE" if "P3" in types else "NONE")
                total_items = df_loc['BARCODE_KODE'].nunique()

                st.markdown(f"""
                <div class="card-lokasi">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="flex: 1.5;"><strong>📍 {lok}</strong></div>
                        <div style="flex: 3;">
                            <span class="status-box {'done' if p1_s=='DONE' else 'empty'}">P1: {p1_s}</span>
                            <span class="status-box {'done' if p2_s=='DONE' else 'empty'}">P2: {p2_s}</span>
                            <span class="status-box {'done' if p3_s=='DONE' else 'none'}">P3: {p3_s}</span>
                        </div>
                        <div style="flex: 2; text-align: right; font-size: 13px;">📦 <b>{total_items}</b> SKU</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"ANALYZE DETAIL {lok}", key=f"btn_{lok}_{idx}", use_container_width=True):
                    st.session_state.selected_lokasi = lok
                    st.rerun()

    # --- TAB 3: AUDIT COMPARE ---
    with tab3:
        if 'selected_lokasi' in st.session_state and st.session_state.selected_lokasi:
            lok_target = st.session_state.selected_lokasi
            st.subheader(f"🔍 Deep Analysis: {lok_target}")
            
            data_lok = df_audit[df_audit['LOKASI'] == lok_target].copy()
            
            if not data_lok.empty:
                df_pivot = data_lok.pivot_table(
                    index=['BARCODE_KODE', 'DESKRIPSI'],
                    columns='JENIS_PENGHITUNG',
                    values='QTYFISIK',
                    aggfunc='sum'
                ).reset_index().fillna(0)
                
                df_petugas_agg = data_lok.groupby('BARCODE_KODE')['NAMA_PETUGAS'].apply(
                    lambda x: ', '.join(sorted(set(x.astype(str))))
                ).reset_index()
                df_petugas_agg.rename(columns={'NAMA_PETUGAS': 'TIM_AUDIT'}, inplace=True)

                for p in ['P1', 'P2', 'P3']:
                    if p not in df_pivot.columns: df_pivot[p] = 0

                df_final = pd.merge(df_pivot, df_order, on='BARCODE_KODE', how='left')
                df_final = pd.merge(df_final, df_petugas_agg, on='BARCODE_KODE', how='left')
                df_final = pd.merge(df_final, df_sebaran, on='BARCODE_KODE', how='left')
                df_final = pd.merge(df_final, df_stok[['BARCODE_KODE', 'ITEM_UNIT', 'BALANCE_QTY', 'BUYING_PRICE']], 
                                   on='BARCODE_KODE', how='left').fillna(0)

                df_final = df_final.sort_values(by='SEQ_ORDER')

                df_final['FISIK_FINAL'] = df_final.apply(lambda r: r['P3'] if r['P3'] > 0 else (r['P2'] if r['P2'] > 0 else r['P1']), axis=1)
                df_final['QTY_SELISIH'] = df_final['FISIK_FINAL'] - df_final['BALANCE_QTY']
                df_final['VAL_SELISIH'] = df_final['QTY_SELISIH'] * df_final['BUYING_PRICE']
                df_final['STATUS'] = df_final['QTY_SELISIH'].apply(lambda x: "🔴 NEGATIF" if x < 0 else ("🟢 POSITIF" if x > 0 else "⚪ BALANCE"))

                cols_view = [
                    'BARCODE_KODE', 'DESKRIPSI', 'TIM_AUDIT', 'SEBARAN_LOKASI', 
                    'ITEM_UNIT', 'BALANCE_QTY', 'P1', 'P2', 'P3', 
                    'FISIK_FINAL', 'QTY_SELISIH', 'VAL_SELISIH', 'STATUS'
                ]
                st.dataframe(df_final[cols_view], use_container_width=True)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_final[cols_view].to_excel(writer, index=False, sheet_name='Hasil_SO')
                
                st.download_button(label=f"📥 Download Excel {lok_target}", data=output.getvalue(), file_name=f"SO_{lok_target}.xlsx", use_container_width=True)
                
                if st.button("⬅️ Kembali", use_container_width=True):
                    st.session_state.selected_lokasi = None
                    st.rerun()
        else:
            st.info("Pilih lokasi di Tab Monitoring.")

    # --- TAB 4, 5, 6 ---
    with tab4:
        st.header("🔗 Navigation & Apps")
        
        # Menggunakan 2 kolom agar layout tetap rapi dan simetris
        c1, c2 = st.columns(2)
        
        with c1:
            st.link_button("🚀 Progress 1 (P1)", "https://script.google.com/macros/s/AKfycbzy2LxYk5lZHDyLav1MD7RZj6bR8R2LGwHQRVQaftTgXI00iFMzX7jp-37iz-mra8GXKg/exec", use_container_width=True)
            st.link_button("🚀 Progress 2 (P2)", "https://script.google.com/macros/s/AKfycbxWEUlPuofOGeDgGaEo1qh9QP0vs9f5NZju0WwKnnT-y3jrRpUhuBghORQPNQQRw7Ef/exec", use_container_width=True)
            st.link_button("📊 GMB Heatmap", "https://progresopname.streamlit.app/", use_container_width=True)
            st.link_button("✅ Verifikasi P3", "https://grandmitra.github.io/verifikasip3/", use_container_width=True)
            st.link_button("📝 Input SO", "https://grandmitra.github.io/inputso/", use_container_width=True)

        with c2:
            st.link_button("🔍 Unlisting Product", "https://grandmitra.github.io/unlisting/", use_container_width=True)
            st.link_button("🚚 Anterinlah App", "https://anterinlah.web.app/", use_container_width=True)
            st.link_button("🛤️ Alur Stok Opname", "https://grandmitra.github.io/alurstokopname/", use_container_width=True)
            st.link_button("🕵️ Lost Code Hunt", "https://grandmitra.github.io/lostcodehunt/", use_container_width=True)

    with tab5:
        st.subheader("🔍 Global Search Item")
        query = st.text_input("Barcode/Nama:")
        if query:
            match = df_audit[(df_audit['DESKRIPSI'].astype(str).str.contains(query, case=False)) | (df_audit['BARCODE_KODE'].astype(str).str.contains(query))]
            st.dataframe(match, use_container_width=True)

    with tab6:
        st.subheader("🚀 Live Tracking")
        if not df_acuan.empty:
            master_locs = set(df_acuan['LOKASI'].astype(str).str.strip().unique())
            loc_done = set(df_audit['LOKASI'].astype(str).str.strip().unique()) if not df_audit.empty else set()
            total_loc = len(master_locs)
            done_count = len(loc_done.intersection(master_locs))
            progress_pct = (done_count / total_loc) if total_loc > 0 else 0
            
            c1, c2, c3 = st.columns([1, 1, 2])
            c1.metric("Total Master", f"{total_loc}")
            c2.metric("Terisi", f"{done_count}")
            with c3:
                st.write(f"**Progress: {progress_pct:.1%}**")
                st.progress(progress_pct)
            
            col_list1, col_list2 = st.columns(2)
            with col_list1:
                st.write("### ✅ Terisi")
                st.dataframe(pd.DataFrame(sorted(list(loc_done.intersection(master_locs))), columns=['LOKASI']), use_container_width=True)
            with col_list2:
                st.write("### ⏳ Belum")
                st.dataframe(pd.DataFrame(sorted(list(master_locs - loc_done)), columns=['LOKASI']), use_container_width=True)

except Exception as e:
    st.error(f"⚠️ Sistem Error: {e}")
