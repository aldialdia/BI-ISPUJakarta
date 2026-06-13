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
st.sidebar.title("🌫️ Menu Navigasi")
menu = st.sidebar.radio(
    "Pilih Halaman Dashboard:",
    [
        "🏠 Home (Ringkasan)", 
        "📈 Analisis Tren", 
        "🗺️ Peta Spasial", 
        "⚠️ Peringatan Dini"
    ]
)

st.sidebar.divider()

# --- TAMBAHAN: SISTEM PERINGATAN GLOBAL DI SIDEBAR ---
# Mencari data di tanggal paling akhir
latest_date = df['tanggal'].max()
df_latest = df[df['tanggal'] == latest_date]

# Mengecek apakah ada stasiun yang ISPU-nya di atas 100
jumlah_kritis = len(df_latest[df_latest['nilai_max_ispu'] > 100])

st.sidebar.subheader("Status Hari Ini")
if jumlah_kritis > 0:
    st.sidebar.error(f"🚨 **AWAS:** Terdeteksi **{jumlah_kritis} stasiun** dengan polusi TIDAK SEHAT! \n\nCek menu Peringatan Dini untuk detailnya.")
else:
    st.sidebar.success("✅ Kualitas udara Jakarta terpantau AMAN.")
# ------------------------------------------------------

st.sidebar.divider()
st.sidebar.info("Sistem Business Intelligence - Pemantauan Kualitas Udara DKI Jakarta.")

# ==========================================
# ROUTING (PENGATUR HALAMAN)
# ==========================================
if menu == "🏠 Home (Ringkasan)":
    import screens.home as home
    home.render(df)

elif menu == "📈 Analisis Tren":
    import screens.trend_analysis as trend_analysis
    trend_analysis.render(df)

elif menu == "🗺️ Peta Spasial":
    import screens.spatial_map as spatial_map
    spatial_map.render(df)

elif menu == "⚠️ Peringatan Dini":
    import screens.early_warning as early_warning
    early_warning.render(df)