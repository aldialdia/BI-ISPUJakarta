"""
etl_core.py — Modul Inti ETL Kualitas Udara DKI Jakarta
========================================================
Satu sumber kebenaran untuk seluruh logika ETL.
Digunakan oleh:
  - etl/run_etl.py  (entry point terminal)
  - screens/upload.py (entry point web UI)
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text, inspect
import logging
import os
from datetime import datetime

# ============================================================
# CONSTANTS
# ============================================================

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HARI_LIBUR_NASIONAL = {
    '01-01', '05-01', '06-01', '08-17', '12-25', '12-26',
}

KOLOM_WAJIB = [
    'tanggal', 'stasiun', 'pm25', 'pm10', 'so2',
    'co', 'o3', 'no2', 'max', 'critical', 'categori'
]

KATEGORI_VALID = [
    'BAIK', 'SEDANG', 'TIDAK SEHAT',
    'SANGAT TIDAK SEHAT', 'BERBAHAYA', 'TIDAK ADA DATA'
]

STASIUN_VALID = {
    'DKI1 (Bunderan HI)':  ('DKI1', 'Bunderan HI',  'Jakarta Pusat',   -6.195, 106.823),
    'DKI2 (Kelapa Gading)': ('DKI2', 'Kelapa Gading', 'Jakarta Utara',   -6.160, 106.906),
    'DKI3 (Jagakarsa)':     ('DKI3', 'Jagakarsa',     'Jakarta Selatan', -6.332, 106.833),
    'DKI4 (Lubang Buaya)':  ('DKI4', 'Lubang Buaya',  'Jakarta Timur',   -6.289, 106.910),
    'DKI5 (Kebon Jeruk)':   ('DKI5', 'Kebon Jeruk',   'Jakarta Barat',   -6.195, 106.768),
}

NUMERIC_COLS = ['pm10', 'pm25', 'so2', 'co', 'o3', 'no2', 'max']

DEFAULT_LOG_DIR = os.path.join(PROJECT_ROOT, 'data', 'log_etl')


def is_holiday(tanggal: pd.Timestamp) -> bool:
    """Cek apakah tanggal merupakan hari libur nasional tetap."""
    return tanggal.strftime('%m-%d') in HARI_LIBUR_NASIONAL


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_engine():
    """
    Buat SQLAlchemy engine.
    Membaca konfigurasi dari .streamlit/secrets.toml jika tersedia,
    fallback ke nilai default jika file tidak ditemukan.
    """
    db_config = {
        'host': 'localhost',
        'port': 3306,
        'database': 'ispu2',
        'username': 'root',
        'password': '',
    }

    secrets_path = os.path.join(PROJECT_ROOT, '.streamlit', 'secrets.toml')
    try:
        # Python 3.11+
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # fallback package

        with open(secrets_path, 'rb') as f:
            secrets = tomllib.load(f)

        mysql_cfg = secrets.get('connections', {}).get('mysql', {})
        if mysql_cfg:
            db_config['host']     = mysql_cfg.get('host',     db_config['host'])
            db_config['port']     = mysql_cfg.get('port',     db_config['port'])
            db_config['database'] = mysql_cfg.get('database', db_config['database'])
            db_config['username'] = mysql_cfg.get('username', db_config['username'])
            db_config['password'] = mysql_cfg.get('password', db_config['password'])
    except Exception:
        pass  # Gunakan default

    url = (
        f"mysql+pymysql://{db_config['username']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    )
    return create_engine(url, echo=False)


# ============================================================
# VALIDATION
# ============================================================

def validate_dataframe(df):
    """
    Validasi DataFrame dari CSV.
    Returns: (is_valid: bool, errors: list[str], warnings: list[str])
    """
    errors = []
    warnings = []

    # Cek kolom wajib
    missing_cols = [c for c in KOLOM_WAJIB if c not in df.columns]
    if missing_cols:
        errors.append(f"Kolom wajib tidak ditemukan: {', '.join(missing_cols)}")
        return False, errors, warnings

    # Cek format tanggal
    try:
        df['tanggal'] = pd.to_datetime(df['tanggal'])
    except Exception:
        errors.append("Format kolom 'tanggal' tidak valid. Gunakan format YYYY-MM-DD.")
        return False, errors, warnings

    # Cek nama stasiun
    stasiun_unik = df['stasiun'].unique()
    stasiun_invalid = [s for s in stasiun_unik if s not in STASIUN_VALID]
    if stasiun_invalid:
        valid_list = ', '.join(STASIUN_VALID.keys())
        errors.append(
            f"Nama stasiun tidak valid: {', '.join(stasiun_invalid)}. "
            f"Stasiun yang dikenali: {valid_list}"
        )
        return False, errors, warnings

    # Cek nilai numerik
    for col in NUMERIC_COLS:
        non_numeric = pd.to_numeric(df[col], errors='coerce').isna().sum()
        original_na = df[col].isna().sum()
        bad_values = non_numeric - original_na
        if bad_values > 0:
            warnings.append(
                f"Kolom '{col}': {bad_values} nilai tidak valid (bukan angka), "
                f"akan diisi dengan median."
            )

    # Cek kategori
    df['categori'] = df['categori'].astype(str).str.upper().str.strip()
    kategori_invalid = [
        k for k in df['categori'].unique()
        if k not in KATEGORI_VALID and k != 'NAN'
    ]
    if kategori_invalid:
        warnings.append(
            f"Kategori tidak standar ditemukan: {', '.join(kategori_invalid)}. "
            f"Akan dipetakan ke 'TIDAK ADA DATA'."
        )

    # Cek data kosong
    if len(df) == 0:
        errors.append("File CSV tidak memiliki data (0 baris).")
        return False, errors, warnings

    # Cek duplikat
    dupes = df.duplicated().sum()
    if dupes > 0:
        warnings.append(f"Ditemukan {dupes} baris duplikat yang akan dihapus otomatis.")

    return len(errors) == 0, errors, warnings


# ============================================================
# TRANSFORM — Dimensi & Fakta
# ============================================================

def build_dim_stasiun():
    """Bangun tabel dimensi stasiun (referensi statis)."""
    data = {
        'kode_stasiun': ['DKI1', 'DKI2', 'DKI3', 'DKI4', 'DKI5'],
        'nama_stasiun': ['Bunderan HI', 'Kelapa Gading', 'Jagakarsa', 'Lubang Buaya', 'Kebon Jeruk'],
        'wilayah':      ['Jakarta Pusat', 'Jakarta Utara', 'Jakarta Selatan', 'Jakarta Timur', 'Jakarta Barat'],
        'latitude':     [-6.195, -6.160, -6.332, -6.289, -6.195],
        'longitude':    [106.823, 106.906, 106.833, 106.910, 106.768],
    }
    dim = pd.DataFrame(data)
    dim.insert(0, 'id_stasiun', range(1, len(dim) + 1))
    return dim


def build_dim_kategori():
    """Bangun tabel dimensi kategori ISPU (referensi statis)."""
    data = {
        'nama_kategori':  ['BAIK', 'SEDANG', 'TIDAK SEHAT', 'SANGAT TIDAK SEHAT', 'BERBAHAYA', 'TIDAK ADA DATA'],
        'nilai_min':      [0, 51, 101, 200, 300, -1],
        'nilai_max':      [50, 100, 199, 299, 999, -1],
        'deskripsi': [
            'Tingkat kualitas udara yang sangat baik',
            'Kualitas udara masih dapat diterima',
            'Merugikan pada manusia atau kelompok hewan yang sensitif',
            'Kualitas udara yang dapat merugikan kesehatan',
            'Berbahaya bagi seluruh populasi',
            'Data sensor rusak/hilang',
        ],
        'warna_indikator': ['#00B050', '#0070C0', '#FFFF00', '#FF0000', '#000000', '#808080'],
    }
    dim = pd.DataFrame(data)
    dim.insert(0, 'id_kategori', range(1, len(dim) + 1))
    return dim


def build_dim_waktu(df):
    """Bangun tabel dimensi waktu dari tanggal unik di data."""
    unique_dates = df['tanggal'].drop_duplicates().sort_values().reset_index(drop=True)
    dim = pd.DataFrame({'tanggal': unique_dates})
    dim['id_waktu']   = dim['tanggal'].dt.strftime('%Y%m%d').astype(int)
    dim['hari']       = dim['tanggal'].dt.day
    dim['nama_hari']  = dim['tanggal'].dt.day_name()
    dim['minggu']     = dim['tanggal'].dt.isocalendar().week.astype(int)
    dim['bulan']      = dim['tanggal'].dt.month
    dim['nama_bulan'] = dim['tanggal'].dt.month_name()
    dim['kuartal']    = dim['tanggal'].dt.quarter
    dim['tahun']      = dim['tanggal'].dt.year
    dim['is_weekend'] = dim['tanggal'].dt.dayofweek >= 5
    dim['is_holiday'] = dim['tanggal'].apply(is_holiday)
    return dim


def build_fact_table(df, dim_waktu, dim_stasiun, dim_kategori):
    """
    Bangun tabel fakta ISPU harian.
    Returns: (fact_df, gagal_stasiun_count, gagal_waktu_count)
    """
    df = df.copy()
    df['kode_stasiun'] = df['stasiun'].str.extract(r'(DKI[1-5])')

    fact_df = df.merge(dim_waktu[['tanggal', 'id_waktu']], on='tanggal', how='left')
    fact_df = fact_df.merge(dim_stasiun[['kode_stasiun', 'id_stasiun']], on='kode_stasiun', how='left')
    fact_df = fact_df.merge(
        dim_kategori[['nama_kategori', 'id_kategori']],
        left_on='categori', right_on='nama_kategori', how='left'
    )

    id_tdk_ada = dim_kategori.loc[
        dim_kategori['nama_kategori'] == 'TIDAK ADA DATA', 'id_kategori'
    ].values[0]
    fact_df['id_kategori'] = fact_df['id_kategori'].fillna(id_tdk_ada).astype(int)

    gagal_stasiun = fact_df['id_stasiun'].isnull().sum()
    gagal_waktu   = fact_df['id_waktu'].isnull().sum()

    fact = fact_df[[
        'id_waktu', 'id_stasiun', 'id_kategori',
        'pm10', 'pm25', 'so2', 'co', 'o3', 'no2',
        'max', 'critical'
    ]].copy()
    fact.rename(columns={'max': 'nilai_max_ispu', 'critical': 'polutan_kritis'}, inplace=True)

    return fact, gagal_stasiun, gagal_waktu


# ============================================================
# LOAD — Mode APPEND
# ============================================================

def load_to_database(engine, dim_waktu, dim_stasiun, dim_kategori, fact, logger):
    """
    Muat data ke database MySQL dalam mode APPEND.
    - dim_stasiun & dim_kategori: REPLACE (referensi statis, selalu sama)
    - dim_waktu: hanya tambahkan tanggal yang belum ada
    - fact_ispu_harian: hanya tambahkan baris yang belum ada (cek id_waktu + id_stasiun)
    """
    # --- Dimensi statis (replace) ---
    dim_stasiun.to_sql('dim_stasiun', con=engine, if_exists='replace', index=False)
    dim_kategori.to_sql('dim_kategori_ispu', con=engine, if_exists='replace', index=False)
    logger.info("[LOAD] Dimensi stasiun & kategori dimuat (referensi statis).")

    inspector = inspect(engine)

    # --- dim_waktu: append tanggal baru ---
    if 'dim_waktu' in inspector.get_table_names():
        existing_waktu = pd.read_sql("SELECT id_waktu FROM dim_waktu", con=engine)
        existing_ids = set(existing_waktu['id_waktu'].tolist())
        dim_waktu_to_add = dim_waktu[~dim_waktu['id_waktu'].isin(existing_ids)]
        if len(dim_waktu_to_add) > 0:
            dim_waktu_to_add.to_sql('dim_waktu', con=engine, if_exists='append', index=False)
            logger.info(f"[LOAD] dim_waktu: +{len(dim_waktu_to_add)} tanggal baru ditambahkan.")
        else:
            logger.info("[LOAD] dim_waktu: semua tanggal sudah ada, tidak ada penambahan.")
    else:
        dim_waktu.to_sql('dim_waktu', con=engine, if_exists='replace', index=False)
        logger.info(f"[LOAD] dim_waktu: tabel baru dibuat dengan {len(dim_waktu)} baris.")

    # --- fact_ispu_harian: append baris baru (deduplikasi) ---
    baris_baru = 0
    fact_work = fact.copy()

    if 'fact_ispu_harian' in inspector.get_table_names():
        existing_fact = pd.read_sql(
            "SELECT id_waktu, id_stasiun FROM fact_ispu_harian", con=engine
        )
        existing_fact = existing_fact.dropna(subset=['id_waktu', 'id_stasiun'])
        existing_pairs = set(
            zip(existing_fact['id_waktu'].astype(int), existing_fact['id_stasiun'].astype(int))
        )

        fact_work['_pair'] = list(
            zip(fact_work['id_waktu'].astype(int), fact_work['id_stasiun'].astype(int))
        )
        fact_to_add = fact_work[~fact_work['_pair'].isin(existing_pairs)].drop(columns=['_pair'])

        jumlah_duplikat_db = len(fact_work) - len(fact_to_add)
        if jumlah_duplikat_db > 0:
            logger.info(
                f"[LOAD] fact_ispu_harian: {jumlah_duplikat_db} baris sudah ada di database (dilewati)."
            )

        if len(fact_to_add) > 0:
            max_id = pd.read_sql(
                "SELECT COALESCE(MAX(id_fakta), 0) as max_id FROM fact_ispu_harian", con=engine
            )
            start_id = int(max_id['max_id'].iloc[0]) + 1
            fact_to_add = fact_to_add.copy()
            fact_to_add.insert(0, 'id_fakta', range(start_id, start_id + len(fact_to_add)))
            fact_to_add.to_sql('fact_ispu_harian', con=engine, if_exists='append', index=False)
            baris_baru = len(fact_to_add)
            logger.info(f"[LOAD] fact_ispu_harian: +{baris_baru} baris baru ditambahkan.")
        else:
            logger.info("[LOAD] fact_ispu_harian: tidak ada data baru untuk ditambahkan.")
    else:
        fact_work.insert(0, 'id_fakta', range(1, len(fact_work) + 1))
        fact_work.to_sql('fact_ispu_harian', con=engine, if_exists='replace', index=False)
        baris_baru = len(fact_work)
        logger.info(f"[LOAD] fact_ispu_harian: tabel baru dibuat dengan {baris_baru} baris.")

    # --- Total di database ---
    with engine.connect() as conn:
        jumlah_fakta = conn.execute(text("SELECT COUNT(*) FROM fact_ispu_harian")).scalar()
        jumlah_waktu = conn.execute(text("SELECT COUNT(*) FROM dim_waktu")).scalar()
    logger.info(f"[LOAD] Total di database: {jumlah_fakta} baris fakta, {jumlah_waktu} tanggal.")

    return baris_baru, jumlah_fakta


# ============================================================
# LOGGING SETUP
# ============================================================

def setup_logger(log_dir=None):
    """
    Setup logger yang menulis ke file dan terminal secara bersamaan.
    Returns: (logger, log_filepath)
    """
    if log_dir is None:
        log_dir = DEFAULT_LOG_DIR

    os.makedirs(log_dir, exist_ok=True)

    log_filename = f"etl_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_filepath = os.path.join(log_dir, log_filename)

    # Logger unik per eksekusi (hindari duplikasi handler)
    logger_name = f"etl_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

    # File handler
    fh = logging.FileHandler(log_filepath, encoding='utf-8')
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Stream handler (terminal)
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    return logger, log_filepath


# ============================================================
# ORCHESTRATOR — Fungsi Utama
# ============================================================

def run_etl(df_raw, log_dir=None):
    """
    Orkestrasi proses ETL lengkap (selalu mode APPEND).

    Args:
        df_raw:   DataFrame mentah dari CSV.
        log_dir:  Direktori untuk menyimpan file log.
                  Default: data/log_etl/

    Returns:
        dict dengan kunci:
            success          : bool
            log_filepath     : str  — path file log yang dihasilkan
            baris_diproses   : int  — jumlah baris setelah cleaning
            baris_baru       : int  — jumlah baris baru yang masuk database
            total_di_database: int  — total baris di fact_ispu_harian
    """
    logger, log_filepath = setup_logger(log_dir)

    result = {
        'success': False,
        'log_filepath': log_filepath,
        'baris_diproses': 0,
        'baris_baru': 0,
        'total_di_database': 0,
    }

    try:
        logger.info("=" * 60)
        logger.info("MULAI PROSES ETL - Sistem BI Kualitas Udara DKI Jakarta")
        logger.info("=" * 60)

        baris_awal = len(df_raw)
        logger.info(f"[EXTRACT] Data diterima: {baris_awal} baris.")

        # ---- STAGING ----
        engine = get_db_engine()
        logger.info("[STAGING] Menyimpan data mentah ke staging area...")
        df_staging = df_raw.copy()
        df_staging.to_sql('staging_ispu_raw', con=engine, if_exists='replace', index=False)
        logger.info(f"[STAGING] {len(df_staging)} baris berhasil disimpan ke staging_ispu_raw.")

        # ---- CLEANING ----
        logger.info("[CLEANING] Memulai proses pembersihan data...")
        df = df_staging.copy()

        df['tanggal'] = pd.to_datetime(df['tanggal'])
        logger.info("[CLEANING] Format tanggal distandarisasi ke datetime.")

        df['categori'] = df['categori'].astype(str).str.upper().str.strip()
        logger.info("[CLEANING] Kapitalisasi kolom 'categori' distandarisasi.")

        missing_total = 0
        for col in NUMERIC_COLS:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            missing_count = df[col].isna().sum()
            missing_total += missing_count
            median_val = df[col].median()
            if pd.isna(median_val):
                median_val = 0
            df[col] = df[col].fillna(median_val)
            logger.info(f"[CLEANING] Kolom '{col}': missing values diisi dengan median ({median_val:.2f}).")

        logger.info(f"[CLEANING] Total missing values diimputasi: {missing_total} sel.")

        jumlah_sebelum = len(df)
        df = df.drop_duplicates()
        jumlah_duplikat = jumlah_sebelum - len(df)
        logger.info(f"[CLEANING] Duplicate removal: {jumlah_duplikat} baris duplikat dihapus.")

        jumlah_tdk_ada = (df['categori'] == 'TIDAK ADA DATA').sum()
        logger.info(f"[CLEANING] Ditemukan {jumlah_tdk_ada} baris dengan kategori 'TIDAK ADA DATA'.")

        baris_bersih = len(df)
        logger.info(f"[CLEANING] Selesai. Data bersih: {baris_bersih} baris (dari {baris_awal} awal).")

        # ---- TRANSFORM ----
        logger.info("[TRANSFORM] Memulai transformasi data...")

        dim_stasiun = build_dim_stasiun()
        logger.info(f"[TRANSFORM] Dim_Stasiun dibuat: {len(dim_stasiun)} baris.")

        dim_kategori = build_dim_kategori()
        logger.info(f"[TRANSFORM] Dim_Kategori_ISPU dibuat: {len(dim_kategori)} baris.")

        dim_waktu = build_dim_waktu(df)
        logger.info(f"[TRANSFORM] Dim_Waktu dibuat: {len(dim_waktu)} baris.")
        logger.info(f"[TRANSFORM] Jumlah hari libur nasional terdeteksi: {dim_waktu['is_holiday'].sum()}")

        fact, gagal_stasiun, gagal_waktu = build_fact_table(df, dim_waktu, dim_stasiun, dim_kategori)

        if gagal_stasiun > 0:
            logger.warning(f"[TRANSFORM] {gagal_stasiun} baris gagal mapping ke Dim_Stasiun!")
            fact = fact.dropna(subset=['id_stasiun'])
        if gagal_waktu > 0:
            logger.warning(f"[TRANSFORM] {gagal_waktu} baris gagal mapping ke Dim_Waktu!")

        fact['id_stasiun'] = fact['id_stasiun'].astype(int)
        logger.info(f"[TRANSFORM] Fact_ISPU_Harian dibuat: {len(fact)} baris.")

        # ---- LOAD (APPEND) ----
        logger.info("[LOAD] Memulai pemuatan data ke database (mode APPEND)...")
        baris_baru, jumlah_fakta = load_to_database(
            engine, dim_waktu, dim_stasiun, dim_kategori, fact, logger
        )

        # ---- RINGKASAN ----
        logger.info("=" * 60)
        logger.info("RINGKASAN PROSES ETL")
        logger.info(f"  Baris diekstrak            : {baris_awal}")
        logger.info(f"  Baris duplikat dihapus     : {jumlah_duplikat}")
        logger.info(f"  Missing values diimputasi  : {missing_total}")
        logger.info(f"  Baris data bersih          : {baris_bersih}")
        logger.info(f"  Baris baru ditambahkan     : {baris_baru}")
        logger.info(f"  Total di database          : {jumlah_fakta}")
        logger.info(f"  Log disimpan ke            : {log_filepath}")
        logger.info("ETL SELESAI.")
        logger.info("=" * 60)

        result['success'] = True
        result['baris_diproses'] = baris_bersih
        result['baris_baru'] = baris_baru
        result['total_di_database'] = jumlah_fakta

    except Exception as e:
        logger.error(f"ETL GAGAL: {str(e)}")
        raise
    finally:
        # Bersihkan handler agar tidak bocor
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

    return result
