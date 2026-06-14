import streamlit as st
from utils.db_loader import load_all_data

# Konfigurasi dasar web
st.set_page_config(
    page_title="Dashboard Kualitas Udara DKI", 
    page_icon="🌫️", 
    layout="wide"
)

# Tarik data dari database
try:
    df = load_all_data()
except Exception as e:
    st.error(f"Gagal memuat data dari database: {e}")
    st.stop() 

# ==========================================
# SIDEBAR (NAVIGASI & GLOBAL WARNING)
# ==========================================
st.sidebar.title("🌫️ Dashboard Kualitas Udara DKI")
menu = st.sidebar.radio(
    "Pilih Halaman Dashboard:",
    [
        "🏠 Home", 
        "📈 Analisis Tren", 
    ]
)

st.sidebar.divider()

# Memberikan jarak kosong agar teks terdorong ke bawah
st.sidebar.markdown("<br><br><br><br><br><br><br><br><br><br>", unsafe_allow_html=True)

# Teks kecil berwarna putih/abu-abu terang tanpa latar belakang di paling bawah
st.sidebar.markdown(
    """
    <div style="font-size: 12px; color: #b0b0b0; text-align: left;">
        Sistem Business Intelligence - Pemantauan Kualitas Udara DKI Jakarta.
    </div>
    """,
    unsafe_allow_html=True
)

# ==========================================
# ROUTING (PENGATUR HALAMAN)
# ==========================================
if menu == "🏠 Home":
    import screens.home as home
    home.render(df)

elif menu == "📈 Analisis Tren":
    import screens.trend_analysis as trend_analysis
    trend_analysis.render(df)