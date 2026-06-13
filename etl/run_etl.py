import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import pymysql

# ==========================================
# 1. KONFIGURASI DATABASE MYSQL
# ==========================================
# Ganti 'root' dan 'password_kamu' sesuai dengan MySQL di laptopmu. 
# Jika tidak ada password, hapus tulisan password_kamu jadi: mysql+pymysql://root:@localhost:3306/ispu
DB_USER = 'root'
DB_PASSWORD = '' # Isi jika ada password
DB_HOST = 'localhost'
DB_PORT = '3306'
DB_NAME = 'ispu'

engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

def run_etl():
    print("Mulai proses ETL...")

    # ==========================================
    # 2. EXTRACT (Membaca Data Mentah)
    # ==========================================
    print("Membaca file CSV...")
    df = pd.read_csv('data/raw/ispu_dki_all (2).csv')

    # ==========================================
    # 3. TRANSFORM & CLEANING
    # ==========================================
    print("Membersihkan dan mentransformasi data...")
    # Ubah format tanggal
    df['tanggal'] = pd.to_datetime(df['tanggal'])
    
    # Standarisasi kolom kategori (Hapus spasi berlebih dan jadikan huruf kapital)
    df['categori'] = df['categori'].astype(str).str.upper().str.strip()
    
    # Penanganan Missing Values (Mengisi nilai kosong dengan median per kolom)
    numeric_cols = ['pm10', 'pm25', 'so2', 'co', 'o3', 'no2', 'max']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce') # Ubah ke numerik, error jadi NaN
        df[col] = df[col].fillna(df[col].median())

    # ==========================================
    # 4. MEMBUAT TABEL DIMENSI
    # ==========================================
    print("Membuat Tabel Dimensi...")
    
    # A. Dimensi Stasiun (Tambahan koordinat untuk visualisasi peta)
    stasiun_data = {
        'kode_stasiun': ['DKI1', 'DKI2', 'DKI3', 'DKI4', 'DKI5'],
        'nama_stasiun': ['Bunderan HI', 'Kelapa Gading', 'Jagakarsa', 'Lubang Buaya', 'Kebon Jeruk'],
        'wilayah': ['Jakarta Pusat', 'Jakarta Utara', 'Jakarta Selatan', 'Jakarta Timur', 'Jakarta Barat'],
        'latitude': [-6.195, -6.160, -6.332, -6.289, -6.195],
        'longitude': [106.823, 106.906, 106.833, 106.910, 106.768]
    }
    dim_stasiun = pd.DataFrame(stasiun_data)
    dim_stasiun.insert(0, 'id_stasiun', range(1, len(dim_stasiun) + 1)) # Bikin ID 1-5

    # Ekstrak kode stasiun dari data CSV (misal: "DKI1 (Bunderan HI)" -> "DKI1")
    df['kode_stasiun'] = df['stasiun'].str.extract(r'(DKI[1-5])')

    # B. Dimensi Kategori ISPU (Sesuai standar KLHK)
    kategori_data = {
        'nama_kategori': ['BAIK', 'SEDANG', 'TIDAK SEHAT', 'SANGAT TIDAK SEHAT', 'BERBAHAYA', 'TIDAK ADA DATA'],
        'nilai_min': [0, 51, 101, 200, 300, -1],
        'nilai_max': [50, 100, 199, 299, 999, -1],
        'deskripsi': ['Tingkat kualitas udara yang sangat baik', 'Kualitas udara masih dapat diterima', 'Merugikan pada manusia atau kelompok hewan yang sensitif', 'Kualitas udara yang dapat merugikan kesehatan', 'Berbahaya bagi seluruh populasi', 'Data sensor rusak/hilang'],
        'warna_indikator': ['#00B050', '#0070C0', '#FFFF00', '#FF0000', '#000000', '#808080']
    }
    dim_kategori = pd.DataFrame(kategori_data)
    dim_kategori.insert(0, 'id_kategori', range(1, len(dim_kategori) + 1))

    # C. Dimensi Waktu
    unique_dates = df['tanggal'].drop_duplicates().sort_values().reset_index(drop=True)
    dim_waktu = pd.DataFrame({'tanggal': unique_dates})
    dim_waktu['id_waktu'] = dim_waktu['tanggal'].dt.strftime('%Y%m%d').astype(int) # Format YYYYMMDD
    dim_waktu['hari'] = dim_waktu['tanggal'].dt.day
    dim_waktu['nama_hari'] = dim_waktu['tanggal'].dt.day_name()
    dim_waktu['bulan'] = dim_waktu['tanggal'].dt.month
    dim_waktu['nama_bulan'] = dim_waktu['tanggal'].dt.month_name()
    dim_waktu['tahun'] = dim_waktu['tanggal'].dt.year
    dim_waktu['is_weekend'] = dim_waktu['tanggal'].dt.dayofweek >= 5

    # ==========================================
    # 5. MEMBUAT TABEL FAKTA
    # ==========================================
    print("Membuat Tabel Fakta...")
    # Gabungkan (Merge) DataFrame mentah dengan Dimensi untuk mendapatkan ID
    fact_df = df.merge(dim_waktu[['tanggal', 'id_waktu']], on='tanggal', how='left')
    fact_df = fact_df.merge(dim_stasiun[['kode_stasiun', 'id_stasiun']], on='kode_stasiun', how='left')
    fact_df = fact_df.merge(dim_kategori[['nama_kategori', 'id_kategori']], left_on='categori', right_on='nama_kategori', how='left')

    # Isi id_kategori untuk 'TIDAK ADA DATA' jika ada yang tidak cocok
    id_tdk_ada = dim_kategori.loc[dim_kategori['nama_kategori'] == 'TIDAK ADA DATA', 'id_kategori'].values[0]
    fact_df['id_kategori'] = fact_df['id_kategori'].fillna(id_tdk_ada)

    # Pilih hanya kolom yang dibutuhkan untuk Fact Table
    fact_ispu_harian = fact_df[[
        'id_waktu', 'id_stasiun', 'id_kategori', 
        'pm10', 'pm25', 'so2', 'co', 'o3', 'no2', 
        'max', 'critical'
    ]].copy()
    
    # Rename 'max' ke 'nilai_max_ispu' dan 'critical' ke 'polutan_kritis' sesuai rancangan
    fact_ispu_harian.rename(columns={'max': 'nilai_max_ispu', 'critical': 'polutan_kritis'}, inplace=True)
    fact_ispu_harian.insert(0, 'id_fakta', range(1, len(fact_ispu_harian) + 1))

    # ==========================================
    # 6. LOAD (Memasukkan ke MySQL)
    # ==========================================
    print("Load data ke MySQL...")
    # Masukkan dimensi dulu (karena fakta butuh ID dimensi)
    dim_waktu.to_sql('dim_waktu', con=engine, if_exists='replace', index=False)
    dim_stasiun.to_sql('dim_stasiun', con=engine, if_exists='replace', index=False)
    dim_kategori.to_sql('dim_kategori_ispu', con=engine, if_exists='replace', index=False)
    
    # Masukkan tabel fakta
    fact_ispu_harian.to_sql('fact_ispu_harian', con=engine, if_exists='replace', index=False)

    print("✅ ETL Berhasil! Semua tabel sudah masuk ke database 'ispu'.")

if __name__ == "__main__":
    run_etl()