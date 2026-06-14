import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import pymysql
import logging
import os
from datetime import datetime
log_filename = f"etl_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
DB_USER     = 'root'
DB_PASSWORD = ''
DB_HOST     = 'localhost'
DB_PORT     = '3306'
DB_NAME     = 'ispu2'
engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    echo=False
)
HARI_LIBUR_NASIONAL = {
    '01-01',
    '05-01',
    '06-01',
    '08-17',
    '12-25',
    '12-26',
}
def is_holiday(tanggal: pd.Timestamp) -> bool:
    """Cek apakah tanggal merupakan hari libur nasional tetap."""
    return tanggal.strftime('%m-%d') in HARI_LIBUR_NASIONAL
def run_etl():
    logger.info("=" * 60)
    logger.info("MULAI PROSES ETL - Sistem BI Kualitas Udara DKI Jakarta")
    logger.info("=" * 60)
    logger.info("[EXTRACT] Membaca file CSV sumber data...")
    try:
        df_raw = pd.read_csv('data/raw/ispu_dki_all (2).csv')
        baris_awal = len(df_raw)
        logger.info(f"[EXTRACT] Berhasil membaca {baris_awal} baris dari CSV.")
    except FileNotFoundError:
        logger.error("[EXTRACT] File CSV tidak ditemukan! Proses ETL dihentikan.")
        raise
    logger.info("[STAGING] Menyimpan data mentah ke staging area (tabel staging_ispu_raw)...")
    df_staging = df_raw.copy()
    df_staging.to_sql(
        'staging_ispu_raw',
        con=engine,
        if_exists='replace',
        index=False
    )
    logger.info(f"[STAGING] {len(df_staging)} baris berhasil disimpan ke staging_ispu_raw.")
    logger.info("[CLEANING] Memulai proses pembersihan data...")
    df = df_staging.copy()
    df['tanggal'] = pd.to_datetime(df['tanggal'])
    logger.info("[CLEANING] Format tanggal distandarisasi ke datetime.")
    df['categori'] = df['categori'].astype(str).str.upper().str.strip()
    logger.info("[CLEANING] Kapitalisasi kolom 'categori' distandarisasi.")
    numeric_cols = ['pm10', 'pm25', 'so2', 'co', 'o3', 'no2', 'max']
    jumlah_missing_before = df[numeric_cols].isnull().sum().sum()
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        median_val = df[col].median()
        df[col] = df[col].fillna(median_val)
        logger.info(f"[CLEANING] Kolom '{col}': missing values diisi dengan median ({median_val:.2f}).")
    logger.info(f"[CLEANING] Total missing values sebelum imputasi: {jumlah_missing_before}")
    jumlah_sebelum = len(df)
    df = df.drop_duplicates()
    jumlah_duplikat = jumlah_sebelum - len(df)
    logger.info(f"[CLEANING] Duplicate removal: {jumlah_duplikat} baris duplikat dihapus.")
    jumlah_tdk_ada = (df['categori'] == 'TIDAK ADA DATA').sum()
    logger.info(f"[CLEANING] Ditemukan {jumlah_tdk_ada} baris dengan kategori 'TIDAK ADA DATA'.")
    baris_bersih = len(df)
    logger.info(f"[CLEANING] Selesai. Data bersih: {baris_bersih} baris (dari {baris_awal} awal).")
    logger.info("[TRANSFORM] Memulai transformasi data...")
    stasiun_data = {
        'kode_stasiun': ['DKI1', 'DKI2', 'DKI3', 'DKI4', 'DKI5'],
        'nama_stasiun': ['Bunderan HI', 'Kelapa Gading', 'Jagakarsa', 'Lubang Buaya', 'Kebon Jeruk'],
        'wilayah':      ['Jakarta Pusat', 'Jakarta Utara', 'Jakarta Selatan', 'Jakarta Timur', 'Jakarta Barat'],
        'latitude':     [-6.195, -6.160, -6.332, -6.289, -6.195],
        'longitude':    [106.823, 106.906, 106.833, 106.910, 106.768]
    }
    dim_stasiun = pd.DataFrame(stasiun_data)
    dim_stasiun.insert(0, 'id_stasiun', range(1, len(dim_stasiun) + 1))
    logger.info(f"[TRANSFORM] Dim_Stasiun dibuat: {len(dim_stasiun)} baris.")
    kategori_data = {
        'nama_kategori':  ['BAIK', 'SEDANG', 'TIDAK SEHAT', 'SANGAT TIDAK SEHAT', 'BERBAHAYA', 'TIDAK ADA DATA'],
        'nilai_min':      [0, 51, 101, 200, 300, -1],
        'nilai_max':      [50, 100, 199, 299, 999, -1],
        'deskripsi':      [
            'Tingkat kualitas udara yang sangat baik',
            'Kualitas udara masih dapat diterima',
            'Merugikan pada manusia atau kelompok hewan yang sensitif',
            'Kualitas udara yang dapat merugikan kesehatan',
            'Berbahaya bagi seluruh populasi',
            'Data sensor rusak/hilang'
        ],
        'warna_indikator': ['#00B050', '#0070C0', '#FFFF00', '#FF0000', '#000000', '#808080']
    }
    dim_kategori = pd.DataFrame(kategori_data)
    dim_kategori.insert(0, 'id_kategori', range(1, len(dim_kategori) + 1))
    logger.info(f"[TRANSFORM] Dim_Kategori_ISPU dibuat: {len(dim_kategori)} baris.")
    unique_dates = df['tanggal'].drop_duplicates().sort_values().reset_index(drop=True)
    dim_waktu = pd.DataFrame({'tanggal': unique_dates})
    dim_waktu['id_waktu']   = dim_waktu['tanggal'].dt.strftime('%Y%m%d').astype(int)
    dim_waktu['hari']       = dim_waktu['tanggal'].dt.day
    dim_waktu['nama_hari']  = dim_waktu['tanggal'].dt.day_name()
    dim_waktu['minggu']     = dim_waktu['tanggal'].dt.isocalendar().week.astype(int)
    dim_waktu['bulan']      = dim_waktu['tanggal'].dt.month
    dim_waktu['nama_bulan'] = dim_waktu['tanggal'].dt.month_name()
    dim_waktu['kuartal']    = dim_waktu['tanggal'].dt.quarter
    dim_waktu['tahun']      = dim_waktu['tanggal'].dt.year
    dim_waktu['is_weekend'] = dim_waktu['tanggal'].dt.dayofweek >= 5
    dim_waktu['is_holiday'] = dim_waktu['tanggal'].apply(is_holiday)
    logger.info(f"[TRANSFORM] Dim_Waktu dibuat: {len(dim_waktu)} baris.")
    logger.info(f"[TRANSFORM] Jumlah hari libur nasional terdeteksi: {dim_waktu['is_holiday'].sum()}")
    df['kode_stasiun'] = df['stasiun'].str.extract(r'(DKI[1-5])')
    fact_df = df.merge(dim_waktu[['tanggal', 'id_waktu']], on='tanggal', how='left')
    fact_df = fact_df.merge(dim_stasiun[['kode_stasiun', 'id_stasiun']], on='kode_stasiun', how='left')
    fact_df = fact_df.merge(
        dim_kategori[['nama_kategori', 'id_kategori']],
        left_on='categori', right_on='nama_kategori', how='left'
    )
    id_tdk_ada = dim_kategori.loc[dim_kategori['nama_kategori'] == 'TIDAK ADA DATA', 'id_kategori'].values[0]
    fact_df['id_kategori'] = fact_df['id_kategori'].fillna(id_tdk_ada).astype(int)
    gagal_stasiun = fact_df['id_stasiun'].isnull().sum()
    gagal_waktu   = fact_df['id_waktu'].isnull().sum()
    if gagal_stasiun > 0:
        logger.warning(f"[TRANSFORM] {gagal_stasiun} baris gagal mapping ke Dim_Stasiun!")
    if gagal_waktu > 0:
        logger.warning(f"[TRANSFORM] {gagal_waktu} baris gagal mapping ke Dim_Waktu!")
    fact_ispu_harian = fact_df[[
        'id_waktu', 'id_stasiun', 'id_kategori',
        'pm10', 'pm25', 'so2', 'co', 'o3', 'no2',
        'max', 'critical'
    ]].copy()
    fact_ispu_harian.rename(
        columns={'max': 'nilai_max_ispu', 'critical': 'polutan_kritis'},
        inplace=True
    )
    fact_ispu_harian.insert(0, 'id_fakta', range(1, len(fact_ispu_harian) + 1))
    logger.info(f"[TRANSFORM] Fact_ISPU_Harian dibuat: {len(fact_ispu_harian)} baris.")
    logger.info("[LOAD] Memulai pemuatan data ke database MySQL...")
    tabel_dimensi = [
        (dim_waktu,    'dim_waktu',          'Dim_Waktu'),
        (dim_stasiun,  'dim_stasiun',         'Dim_Stasiun'),
        (dim_kategori, 'dim_kategori_ispu',   'Dim_Kategori_ISPU'),
    ]
    for df_tabel, nama_tabel, label in tabel_dimensi:
        df_tabel.to_sql(nama_tabel, con=engine, if_exists='replace', index=False)
        with engine.connect() as conn:
            jumlah = conn.execute(text(f"SELECT COUNT(*) FROM `{nama_tabel}`")).scalar()
        logger.info(f"[LOAD] {label}: {jumlah} baris berhasil dimuat ke '{nama_tabel}'.")
    try:
        fact_ispu_harian.to_sql('fact_ispu_harian', con=engine, if_exists='replace', index=False)
        logger.info(f"[LOAD] Fact_ISPU_Harian: {len(fact_ispu_harian)} baris berhasil dimuat ke 'fact_ispu_harian'.")
    except Exception as e:
        logger.error(f"[LOAD] Gagal memuat ke 'fact_ispu_harian': {e}")
        raise
    jumlah_fakta = len(fact_ispu_harian)
    logger.info("=" * 60)
    logger.info("RINGKASAN PROSES ETL")
    logger.info(f"  Baris diekstrak (CSV)       : {baris_awal}")
    logger.info(f"  Baris duplikat dihapus      : {jumlah_duplikat}")
    logger.info(f"  Missing values diimputasi   : {jumlah_missing_before}")
    logger.info(f"  Baris data bersih           : {baris_bersih}")
    logger.info(f"  Baris dimuat ke fakta       : {jumlah_fakta}")
    logger.info(f"  Log disimpan ke             : {log_filename}")
    logger.info("ETL SELESAI.")
    logger.info("=" * 60)
    print(f"\n✅ ETL Berhasil! Semua tabel sudah masuk ke database '{DB_NAME}'.")
    print(f"📋 Log proses disimpan di: {log_filename}")
if __name__ == "__main__":
    run_etl()
