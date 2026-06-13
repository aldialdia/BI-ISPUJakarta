import streamlit as st
import pandas as pd

# Inisialisasi koneksi mengambil dari .streamlit/secrets.toml
conn = st.connection("mysql", type="sql")

@st.cache_data(ttl="1d") # Cache disimpan agar query tidak berulang
def load_all_data():
    query = """
        SELECT 
            w.tanggal, w.nama_hari, w.nama_bulan, w.tahun,
            s.nama_stasiun, s.wilayah, s.latitude, s.longitude,
            k.nama_kategori, k.warna_indikator,
            f.pm10, f.pm25, f.so2, f.co, f.o3, f.no2, 
            f.nilai_max_ispu, f.polutan_kritis
        FROM fact_ispu_harian f
        JOIN dim_waktu w ON f.id_waktu = w.id_waktu
        JOIN dim_stasiun s ON f.id_stasiun = s.id_stasiun
        JOIN dim_kategori_ispu k ON f.id_kategori = k.id_kategori
    """
    df = conn.query(query)
    # Pastikan tipe data tanggal terbaca dengan benar di Pandas
    df['tanggal'] = pd.to_datetime(df['tanggal'])
    return df