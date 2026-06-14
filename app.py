import streamlit as st
from utils.db_loader import load_all_data

# Konfigurasi dasar web
st.set_page_config(
    page_title="Dashboard Kualitas Udara DKI", 
    layout="wide"
)

# ==========================================
# CUSTOM CSS - Premium Dark Theme
# ==========================================
st.markdown("""
<style>
    /* ===== Import Google Fonts ===== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ===== Root & Global ===== */
    html, body {
        font-family: 'Inter', sans-serif;
    }

    /* ===== Main Background ===== */
    .stApp {
        background: linear-gradient(135deg, #0E1117 0%, #13161F 50%, #0E1117 100%);
    }

    /* ===== Reduce top padding ===== */
    .stMainBlockContainer, .block-container {
        padding-top: 2rem !important;
    }

    #MainMenu, footer {
        display: none !important;
    }

    /* ===== Sidebar Styling ===== */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #141820 0%, #0D1017 100%);
        border-right: 1px solid rgba(108, 99, 255, 0.15);
    }

    section[data-testid="stSidebar"] .stRadio > label {
        font-weight: 500;
        letter-spacing: 0.3px;
    }

    /* ===== Header / Title Styling ===== */
    h1 {
        font-weight: 700 !important;
        letter-spacing: -0.5px !important;
        background: linear-gradient(135deg, #A5B4FC, #6C63FF, #818CF8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        padding-bottom: 8px !important;
    }
    
    h2, h3 {
        font-weight: 600 !important;
        color: #C7D2FE !important;
        letter-spacing: -0.3px !important;
    }

    /* ===== Metric Cards ===== */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(108, 99, 255, 0.08), rgba(99, 102, 241, 0.04));
        border: 1px solid rgba(108, 99, 255, 0.2);
        border-radius: 16px;
        padding: 20px 24px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 20px rgba(108, 99, 255, 0.05);
    }

    [data-testid="stMetric"]:hover {
        border-color: rgba(108, 99, 255, 0.4);
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(108, 99, 255, 0.12);
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        color: #94A3B8 !important;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }

    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #E2E8F0 !important;
    }

    /* ===== Custom Alert Boxes ===== */
    .premium-card {
        background: linear-gradient(135deg, rgba(30, 33, 48, 0.9), rgba(20, 22, 35, 0.9));
        border: 1px solid rgba(108, 99, 255, 0.15);
        border-radius: 16px;
        padding: 24px;
        margin: 12px 0;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }
    
    .premium-card:hover {
        border-color: rgba(108, 99, 255, 0.35);
        box-shadow: 0 8px 32px rgba(108, 99, 255, 0.08);
    }

    .premium-card h4 {
        color: #A5B4FC;
        font-weight: 600;
        margin-bottom: 8px;
        font-size: 1rem;
    }

    .premium-card p {
        color: #CBD5E1;
        font-size: 0.9rem;
        line-height: 1.6;
        margin: 0;
    }

    /* ===== Status Cards ===== */
    .status-safe {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(6, 78, 59, 0.08));
        border: 1px solid rgba(16, 185, 129, 0.25);
        border-radius: 14px;
        padding: 18px 24px;
        margin: 10px 0;
    }

    .status-safe p {
        color: #6EE7B7;
        font-weight: 500;
    }

    .status-warning {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.08), rgba(217, 119, 6, 0.08));
        border: 1px solid rgba(245, 158, 11, 0.25);
        border-radius: 14px;
        padding: 18px 24px;
        margin: 10px 0;
    }

    .status-warning p {
        color: #FCD34D;
        font-weight: 500;
    }

    .status-danger {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.08), rgba(185, 28, 28, 0.08));
        border: 1px solid rgba(239, 68, 68, 0.25);
        border-radius: 14px;
        padding: 18px 24px;
        margin: 10px 0;
    }

    .status-danger p {
        color: #FCA5A5;
        font-weight: 500;
    }

    /* ===== Custom KPI/Stats Grid ===== */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 20px;
        margin-bottom: 24px;
    }

    .kpi-stat {
        background: rgba(20, 24, 35, 0.6);
        border: 1px solid rgba(108, 99, 255, 0.1);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        transition: all 0.2s ease;
    }

    .kpi-stat:hover {
        background: rgba(108, 99, 255, 0.05);
        border-color: rgba(108, 99, 255, 0.3);
    }

    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #E2E8F0, #94A3B8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 4px;
    }

    .kpi-label {
        font-size: 0.75rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
    }

    /* ===== Charts Container ===== */
    .chart-container {
        background: rgba(20, 24, 35, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 20px;
        margin-top: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
    }

    /* ===== Info Boxes ===== */
    .insight-card {
        background: rgba(20, 24, 35, 0.8);
        border: 1px solid rgba(108, 99, 255, 0.12);
        border-radius: 14px;
        padding: 18px 20px;
        margin-top: 12px;
    }

    /* ===== Section Title ===== */
    .section-title {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 28px 0 12px 0;
    }

    .section-title .icon-circle {
        width: 36px;
        height: 36px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
        background: linear-gradient(135deg, rgba(108, 99, 255, 0.15), rgba(99, 102, 241, 0.08));
        color: #A5B4FC;
        border: 1px solid rgba(108, 99, 255, 0.2);
    }

    /* ===== DataFrames ===== */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(108, 99, 255, 0.15);
    }
    
    [data-testid="stDataFrame"] > div {
        border-radius: 12px;
    }

    /* ===== Button Styling ===== */
    .stButton > button {
        border-radius: 10px !important;
        border: 1px solid rgba(108, 99, 255, 0.3) !important;
        background: linear-gradient(135deg, rgba(108, 99, 255, 0.12), rgba(99, 102, 241, 0.06)) !important;
        color: #A5B4FC !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
    }

    .stButton > button:hover {
        border-color: rgba(108, 99, 255, 0.6) !important;
        box-shadow: 0 4px 20px rgba(108, 99, 255, 0.15) !important;
    }
    
    /* ===== Tab Styling ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: rgba(20, 24, 35, 0.5);
        border-radius: 12px;
        padding: 4px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background: rgba(108, 99, 255, 0.15) !important;
    }

    /* ===== Legend Box ===== */
    .legend-box {
        background: rgba(20, 24, 35, 0.8);
        border: 1px solid rgba(108, 99, 255, 0.12);
        border-radius: 14px;
        padding: 18px 20px;
        margin-top: 12px;
    }

    .legend-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 5px 0;
        font-size: 0.85rem;
        color: #CBD5E1;
    }

    .legend-dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        display: inline-block;
        flex-shrink: 0;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# SIDEBAR (NAVIGASI & GLOBAL WARNING)
# ==========================================
st.sidebar.title("Dashboard Kualitas Udara DKI")
menu = st.sidebar.radio(
    "Pilih Halaman Dashboard:",
    [
        "Beranda", 
        "Analisis Tren",
        "Upload Data"
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
if menu == "Upload Data":
    import screens.upload as upload
    upload.render()
else:
    # Tarik data dari database HANYA jika bukan di halaman Upload
    # (agar halaman Upload tetap bisa diakses meskipun database kosong)
    try:
        df = load_all_data()
    except Exception as e:
        st.error(f"Gagal memuat data dari database: {e}")
        st.stop() 

    if menu == "Beranda":
        import screens.home as home
        home.render(df)

    elif menu == "Analisis Tren":
        import screens.trend_analysis as trend_analysis
        trend_analysis.render(df)