import streamlit as st
import pandas as pd
import plotly.express as px

# 1. SISTEM PASSWORD (MBG123)
def check_password():
    """Returns True if the user had the correct password."""
    def password_entered():
        if st.session_state["password"] == "mbg123":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # hapus password dari session state
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Tampilan Form Login
        st.markdown("<h2 style='text-align: center;'>🔐 Restricted Access</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.text_input("Masukkan Password Aplikasi", type="password", on_change=password_entered, key="password")
            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.error("😕 Password salah. Silakan coba lagi.")
        return False
    else:
        return st.session_state["password_correct"]

if not check_password():
    st.stop()  # Berhenti di sini jika password belum benar

# --- LANJUTAN SCRIPT DASHBOARD KAMU ---
pd.set_option("styler.render.max_elements", 1000000)
# ... dst (copy paste script dashboard yang sebelumnya di sini)
