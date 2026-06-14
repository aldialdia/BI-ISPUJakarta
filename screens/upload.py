import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import io
from datetime import datetime

# ==========================================
# KONFIGURASI DATABASE (sama dengan ETL)
# ==========================================
DB_USER     = 'root'
DB_PASSWORD = ''
DB_HOST     = 'localhost'
DB_PORT     = '3306'
DB_NAME     = 'ispu2'

HARI_LIBUR_NASIONAL = {
    '01-01', '05-01', '06-01', '08-17', '12-25', '12-26',
}

KOLOM_WAJIB = ['tanggal', 'stasiun', 'pm25', 'pm10', 'so2', 'co', 'o3', 'no2', 'max', 'critical', 'categori']

KATEGORI_VALID = ['BAIK', 'SEDANG', 'TIDAK SEHAT', 'SANGAT TIDAK SEHAT', 'BERBAHAYA', 'TIDAK ADA DATA']

STASIUN_VALID = {
    'DKI1 (Bunderan HI)': ('DKI1', 'Bunderan HI', 'Jakarta Pusat', -6.195, 106.823),
    'DKI2 (Kelapa Gading)': ('DKI2', 'Kelapa Gading', 'Jakarta Utara', -6.160, 106.906),
    'DKI3 (Jagakarsa)': ('DKI3', 'Jagakarsa', 'Jakarta Selatan', -6.332, 106.833),
    'DKI4 (Lubang Buaya)': ('DKI4', 'Lubang Buaya', 'Jakarta Timur', -6.289, 106.910),
    'DKI5 (Kebon Jeruk)': ('DKI5', 'Kebon Jeruk', 'Jakarta Barat', -6.195, 106.768),
}


def is_holiday(tanggal: pd.Timestamp) -> bool:
    return tanggal.strftime('%m-%d') in HARI_LIBUR_NASIONAL


def generate_template_csv():
    """Generate a template CSV with sample data rows."""
    template_data = {
        'tanggal': ['2025-01-01', '2025-01-01', '2025-01-02'],
        'stasiun': ['DKI1 (Bunderan HI)', 'DKI2 (Kelapa Gading)', 'DKI1 (Bunderan HI)'],
        'pm25': [45.0, 60.0, 38.0],
        'pm10': [55.0, 72.0, 48.0],
        'so2': [12.0, 18.0, 10.0],
        'co': [25.0, 30.0, 20.0],
        'o3': [40.0, 55.0, 35.0],
        'no2': [15.0, 20.0, 12.0],
        'max': [55.0, 72.0, 48.0],
        'critical': ['PM10', 'PM10', 'PM10'],
        'categori': ['SEDANG', 'SEDANG', 'BAIK'],
    }
    df_template = pd.DataFrame(template_data)
    return df_template.to_csv(index=False).encode('utf-8')


def validate_dataframe(df):
    """Validate uploaded dataframe and return (is_valid, messages)."""
    errors = []
    warnings = []
    
    # 1. Check required columns
    missing_cols = [c for c in KOLOM_WAJIB if c not in df.columns]
    if missing_cols:
        errors.append(f"Kolom wajib tidak ditemukan: {', '.join(missing_cols)}")
        return False, errors, warnings
    
    # 2. Check date format
    try:
        df['tanggal'] = pd.to_datetime(df['tanggal'])
    except Exception:
        errors.append("Format kolom 'tanggal' tidak valid. Gunakan format YYYY-MM-DD.")
        return False, errors, warnings
    
    # 3. Check stasiun values
    stasiun_unik = df['stasiun'].unique()
    stasiun_invalid = [s for s in stasiun_unik if s not in STASIUN_VALID]
    if stasiun_invalid:
        valid_list = ', '.join(STASIUN_VALID.keys())
        errors.append(f"Nama stasiun tidak valid: {', '.join(stasiun_invalid)}. Stasiun yang dikenali: {valid_list}")
        return False, errors, warnings
    
    # 4. Check numeric columns
    numeric_cols = ['pm10', 'pm25', 'so2', 'co', 'o3', 'no2', 'max']
    for col in numeric_cols:
        non_numeric = pd.to_numeric(df[col], errors='coerce').isna().sum()
        original_na = df[col].isna().sum()
        bad_values = non_numeric - original_na
        if bad_values > 0:
            warnings.append(f"Kolom '{col}': {bad_values} nilai tidak valid (bukan angka), akan diisi dengan median.")
    
    # 5. Check kategori
    df['categori'] = df['categori'].astype(str).str.upper().str.strip()
    kategori_invalid = [k for k in df['categori'].unique() if k not in KATEGORI_VALID and k != 'NAN']
    if kategori_invalid:
        warnings.append(f"Kategori tidak standar ditemukan: {', '.join(kategori_invalid)}. Akan dipetakan ke 'TIDAK ADA DATA'.")
    
    # 6. Check for empty data
    if len(df) == 0:
        errors.append("File CSV tidak memiliki data (0 baris).")
        return False, errors, warnings
    
    # 7. Duplicate check
    dupes = df.duplicated().sum()
    if dupes > 0:
        warnings.append(f"Ditemukan {dupes} baris duplikat yang akan dihapus otomatis.")
    
    return len(errors) == 0, errors, warnings


def run_upload_etl(df_raw):
    """Run ETL process on uploaded data and APPEND to existing database."""
    engine = create_engine(
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
        echo=False
    )
    
    log_messages = []
    
    # --- STAGING ---
    log_messages.append(f"Menyimpan {len(df_raw)} baris ke staging area...")
    df_staging = df_raw.copy()
    df_staging.to_sql('staging_ispu_raw', con=engine, if_exists='replace', index=False)
    
    # --- CLEANING ---
    df = df_staging.copy()
    df['tanggal'] = pd.to_datetime(df['tanggal'])
    df['categori'] = df['categori'].astype(str).str.upper().str.strip()
    
    numeric_cols = ['pm10', 'pm25', 'so2', 'co', 'o3', 'no2', 'max']
    missing_total = 0
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        missing_count = df[col].isna().sum()
        missing_total += missing_count
        median_val = df[col].median()
        if pd.isna(median_val):
            median_val = 0
        df[col] = df[col].fillna(median_val)
    log_messages.append(f"Missing values diimputasi: {missing_total} sel")
    
    jumlah_sebelum = len(df)
    df = df.drop_duplicates()
    jumlah_duplikat = jumlah_sebelum - len(df)
    log_messages.append(f"Duplikat internal dihapus: {jumlah_duplikat} baris")
    
    # --- TRANSFORM ---
    # Dim Stasiun (referensi statis — selalu replace)
    stasiun_data = {
        'kode_stasiun': ['DKI1', 'DKI2', 'DKI3', 'DKI4', 'DKI5'],
        'nama_stasiun': ['Bunderan HI', 'Kelapa Gading', 'Jagakarsa', 'Lubang Buaya', 'Kebon Jeruk'],
        'wilayah':      ['Jakarta Pusat', 'Jakarta Utara', 'Jakarta Selatan', 'Jakarta Timur', 'Jakarta Barat'],
        'latitude':     [-6.195, -6.160, -6.332, -6.289, -6.195],
        'longitude':    [106.823, 106.906, 106.833, 106.910, 106.768]
    }
    dim_stasiun = pd.DataFrame(stasiun_data)
    dim_stasiun.insert(0, 'id_stasiun', range(1, len(dim_stasiun) + 1))
    
    # Dim Kategori (referensi statis — selalu replace)
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
    
    # Dim Waktu — buat untuk tanggal baru dari upload
    unique_dates_upload = df['tanggal'].drop_duplicates().sort_values().reset_index(drop=True)
    dim_waktu_new = pd.DataFrame({'tanggal': unique_dates_upload})
    dim_waktu_new['id_waktu']   = dim_waktu_new['tanggal'].dt.strftime('%Y%m%d').astype(int)
    dim_waktu_new['hari']       = dim_waktu_new['tanggal'].dt.day
    dim_waktu_new['nama_hari']  = dim_waktu_new['tanggal'].dt.day_name()
    dim_waktu_new['minggu']     = dim_waktu_new['tanggal'].dt.isocalendar().week.astype(int)
    dim_waktu_new['bulan']      = dim_waktu_new['tanggal'].dt.month
    dim_waktu_new['nama_bulan'] = dim_waktu_new['tanggal'].dt.month_name()
    dim_waktu_new['kuartal']    = dim_waktu_new['tanggal'].dt.quarter
    dim_waktu_new['tahun']      = dim_waktu_new['tanggal'].dt.year
    dim_waktu_new['is_weekend'] = dim_waktu_new['tanggal'].dt.dayofweek >= 5
    dim_waktu_new['is_holiday'] = dim_waktu_new['tanggal'].apply(is_holiday)
    
    # Fact table — transform dulu sebelum filter duplikat
    df['kode_stasiun'] = df['stasiun'].str.extract(r'(DKI[1-5])')
    fact_df = df.merge(dim_waktu_new[['tanggal', 'id_waktu']], on='tanggal', how='left')
    fact_df = fact_df.merge(dim_stasiun[['kode_stasiun', 'id_stasiun']], on='kode_stasiun', how='left')
    fact_df = fact_df.merge(
        dim_kategori[['nama_kategori', 'id_kategori']],
        left_on='categori', right_on='nama_kategori', how='left'
    )
    
    id_tdk_ada = dim_kategori.loc[dim_kategori['nama_kategori'] == 'TIDAK ADA DATA', 'id_kategori'].values[0]
    fact_df['id_kategori'] = fact_df['id_kategori'].fillna(id_tdk_ada).astype(int)
    
    fact_new = fact_df[[
        'id_waktu', 'id_stasiun', 'id_kategori',
        'pm10', 'pm25', 'so2', 'co', 'o3', 'no2',
        'max', 'critical'
    ]].copy()
    
    fact_new.rename(
        columns={'max': 'nilai_max_ispu', 'critical': 'polutan_kritis'},
        inplace=True
    )
    
    gagal_stasiun = fact_new['id_stasiun'].isnull().sum()
    if gagal_stasiun > 0:
        log_messages.append(f"PERINGATAN: {gagal_stasiun} baris gagal mapping ke stasiun")
        fact_new = fact_new.dropna(subset=['id_stasiun'])
    
    fact_new['id_stasiun'] = fact_new['id_stasiun'].astype(int)
    
    # --- LOAD (APPEND MODE) ---
    log_messages.append("Memulai proses load (mode APPEND)...")
    
    # 1. Load dimensi statis (replace — isinya selalu tetap)
    dim_stasiun.to_sql('dim_stasiun', con=engine, if_exists='replace', index=False)
    dim_kategori.to_sql('dim_kategori_ispu', con=engine, if_exists='replace', index=False)
    log_messages.append("Dimensi stasiun & kategori dimuat (referensi statis)")
    
    # 2. Append dim_waktu — hanya tanggal baru
    from sqlalchemy import inspect
    inspector = inspect(engine)
    
    if 'dim_waktu' in inspector.get_table_names():
        existing_waktu = pd.read_sql("SELECT id_waktu FROM dim_waktu", con=engine)
        existing_ids = set(existing_waktu['id_waktu'].tolist())
        dim_waktu_to_add = dim_waktu_new[~dim_waktu_new['id_waktu'].isin(existing_ids)]
        
        if len(dim_waktu_to_add) > 0:
            dim_waktu_to_add.to_sql('dim_waktu', con=engine, if_exists='append', index=False)
            log_messages.append(f"dim_waktu: +{len(dim_waktu_to_add)} tanggal baru ditambahkan")
        else:
            log_messages.append("dim_waktu: semua tanggal sudah ada, tidak ada penambahan")
    else:
        # Tabel belum ada, buat baru
        dim_waktu_new.to_sql('dim_waktu', con=engine, if_exists='replace', index=False)
        log_messages.append(f"dim_waktu: tabel baru dibuat dengan {len(dim_waktu_new)} baris")
    
    # 3. Append fact_ispu_harian — hanya record baru (cek duplikat via id_waktu + id_stasiun)
    if 'fact_ispu_harian' in inspector.get_table_names():
        try:
            existing_fact = pd.read_sql(
                "SELECT id_waktu, id_stasiun FROM fact_ispu_harian", con=engine
            )
            # Buang baris yang punya id_stasiun atau id_waktu NULL agar tidak error saat di-cast ke int
            existing_fact = existing_fact.dropna(subset=['id_waktu', 'id_stasiun'])
            
            # Buat set pasangan (id_waktu, id_stasiun) yang sudah ada
            existing_pairs = set(
                zip(existing_fact['id_waktu'].astype(int), existing_fact['id_stasiun'].astype(int))
            )
            
            # Filter: hanya simpan record yang belum ada
            fact_new['_pair'] = list(zip(fact_new['id_waktu'].astype(int), fact_new['id_stasiun'].astype(int)))
            fact_to_add = fact_new[~fact_new['_pair'].isin(existing_pairs)].drop(columns=['_pair'])
            fact_new = fact_new.drop(columns=['_pair'])
            
            jumlah_duplikat_db = len(fact_new) - len(fact_to_add)
            if jumlah_duplikat_db > 0:
                log_messages.append(f"fact_ispu_harian: {jumlah_duplikat_db} baris sudah ada di database (dilewati)")
            
            if len(fact_to_add) > 0:
                # Lanjutkan id_fakta dari max yang sudah ada
                max_id = pd.read_sql("SELECT COALESCE(MAX(id_fakta), 0) as max_id FROM fact_ispu_harian", con=engine)
                start_id = int(max_id['max_id'].iloc[0]) + 1
                fact_to_add = fact_to_add.copy()
                fact_to_add.insert(0, 'id_fakta', range(start_id, start_id + len(fact_to_add)))
                
                fact_to_add.to_sql('fact_ispu_harian', con=engine, if_exists='append', index=False)
                log_messages.append(f"fact_ispu_harian: +{len(fact_to_add)} baris baru ditambahkan")
            else:
                log_messages.append("fact_ispu_harian: tidak ada data baru untuk ditambahkan")
        except Exception as e:
            log_messages.append(f"ERROR saat append fakta: {str(e)}")
            raise e
    else:
        # Tabel belum ada, buat baru
        fact_new.insert(0, 'id_fakta', range(1, len(fact_new) + 1))
        fact_new.to_sql('fact_ispu_harian', con=engine, if_exists='replace', index=False)
        log_messages.append(f"fact_ispu_harian: tabel baru dibuat dengan {len(fact_new)} baris")
    
    # Hitung total di database setelah append
    with engine.connect() as conn:
        jumlah_fakta = conn.execute(text("SELECT COUNT(*) FROM fact_ispu_harian")).scalar()
        jumlah_waktu = conn.execute(text("SELECT COUNT(*) FROM dim_waktu")).scalar()
    
    baris_baru = len(fact_to_add) if 'fact_to_add' in dir() else len(fact_new)
    log_messages.append(f"Total di database: {jumlah_fakta} baris fakta, {jumlah_waktu} tanggal")
    
    return True, log_messages, len(df), jumlah_fakta, baris_baru


def render():
    st.title("Upload & Pembaruan Data")
    st.caption("Unggah file CSV data ISPU untuk memperbarui database dashboard")
    
    # ==========================================
    # 1. TEMPLATE DOWNLOAD
    # ==========================================
    st.subheader("Template Data")
    st.markdown("""
    <div class="premium-card">
        <h4>Format Standar File CSV</h4>
        <p>Unduh template di bawah sebagai acuan format file yang dapat diproses oleh sistem. 
        Pastikan file yang diunggah mengikuti struktur kolom yang sama.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Column info table
    col_info, col_download = st.columns([2, 1])
    
    with col_info:
        st.markdown("""
        <div class="legend-box">
            <div style="font-size: 0.8rem; color: #94A3B8; font-weight: 600; text-transform: uppercase; 
                letter-spacing: 0.8px; margin-bottom: 12px;">Spesifikasi Kolom</div>
        </div>
        """, unsafe_allow_html=True)
        
        spec_data = pd.DataFrame({
            'Kolom': ['tanggal', 'stasiun', 'pm25', 'pm10', 'so2', 'co', 'o3', 'no2', 'max', 'critical', 'categori'],
            'Tipe': ['Date', 'Text', 'Numeric', 'Numeric', 'Numeric', 'Numeric', 'Numeric', 'Numeric', 'Numeric', 'Text', 'Text'],
            'Keterangan': [
                'Format YYYY-MM-DD',
                'Contoh: DKI1 (Bunderan HI)',
                'Konsentrasi PM2.5 (µg/m³)',
                'Konsentrasi PM10 (µg/m³)',
                'Konsentrasi SO2 (µg/m³)',
                'Konsentrasi CO (µg/m³)',
                'Konsentrasi O3 (µg/m³)',
                'Konsentrasi NO2 (µg/m³)',
                'Nilai ISPU maksimum',
                'Polutan kritis (PM10/PM25/SO2/CO/O3/NO2)',
                'BAIK / SEDANG / TIDAK SEHAT / SANGAT TIDAK SEHAT / BERBAHAYA'
            ]
        })
        st.dataframe(spec_data, use_container_width=True, hide_index=True)
    
    with col_download:
        st.markdown("""
        <div class="insight-card" style="text-align: center;">
            <h4>Stasiun yang Dikenali</h4>
            <p style="font-size: 0.82rem; line-height: 2;">
                DKI1 (Bunderan HI)<br>
                DKI2 (Kelapa Gading)<br>
                DKI3 (Jagakarsa)<br>
                DKI4 (Lubang Buaya)<br>
                DKI5 (Kebon Jeruk)
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        template_csv = generate_template_csv()
        st.download_button(
            label="Download Template CSV",
            data=template_csv,
            file_name="template_ispu_dki.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    st.divider()
    
    # ==========================================
    # 2. FILE UPLOAD
    # ==========================================
    st.subheader("Unggah File Data")
    
    uploaded_file = st.file_uploader(
        "Pilih file CSV",
        type=['csv'],
        help="Upload file CSV dengan format yang sesuai template di atas"
    )
    
    if uploaded_file is not None:
        try:
            df_upload = pd.read_csv(uploaded_file)
        except Exception as e:
            st.markdown(f"""
            <div class="status-danger">
                <p>Gagal membaca file: <strong>{e}</strong></p>
            </div>
            """, unsafe_allow_html=True)
            return
        
        # ==========================================
        # 3. PREVIEW & VALIDATION
        # ==========================================
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Preview Data**")
        st.dataframe(df_upload.head(10), use_container_width=True, hide_index=True)
        
        st.markdown(f"""
        <div class="premium-card">
            <h4>Ringkasan File</h4>
            <p>Total baris: <strong>{len(df_upload)}</strong> &nbsp;|&nbsp; 
            Total kolom: <strong>{len(df_upload.columns)}</strong> &nbsp;|&nbsp;
            Kolom: <strong>{', '.join(df_upload.columns.tolist())}</strong></p>
        </div>
        """, unsafe_allow_html=True)
        
        # Validate
        is_valid, errors, warnings = validate_dataframe(df_upload.copy())
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if errors:
            for err in errors:
                st.markdown(f"""
                <div class="status-danger">
                    <p><strong>Error:</strong> {err}</p>
                </div>
                """, unsafe_allow_html=True)
        
        if warnings:
            for warn in warnings:
                st.markdown(f"""
                <div class="status-warning">
                    <p><strong>Peringatan:</strong> {warn}</p>
                </div>
                """, unsafe_allow_html=True)
        
        if is_valid:
            st.markdown("""
            <div class="status-safe">
                <p>Validasi berhasil — file siap diproses ke database.</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # ==========================================
            # 4. PROSES ETL
            # ==========================================
            col_btn, col_space = st.columns([1, 3])
            with col_btn:
                proses = st.button("Proses & Muat ke Database", type="primary", use_container_width=True)
            
            if proses:
                with st.spinner("Menjalankan proses ETL..."):
                    try:
                        success, log_msgs, baris_bersih, baris_fakta, baris_baru = run_upload_etl(df_upload)
                        
                        if success:
                            if baris_baru > 0:
                                st.markdown(f"""
                                <div class="status-safe">
                                    <p><strong>ETL Berhasil!</strong> Sebanyak <strong>{baris_baru} baris baru</strong> 
                                    telah ditambahkan ke database (mode append). 
                                    Silakan kembali ke halaman Ringkasan untuk melihat data terbaru.</p>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.markdown("""
                                <div class="status-warning">
                                    <p><strong>Proses selesai.</strong> Tidak ada data baru yang ditambahkan — 
                                    semua baris yang di-upload sudah ada di database.</p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Clear cached data so dashboard reloads
                            st.cache_data.clear()
                            
                            # Show log
                            st.markdown("<br>", unsafe_allow_html=True)
                            st.markdown("**Log Proses ETL**")
                            for msg in log_msgs:
                                st.markdown(f"""
                                <div style="padding: 6px 12px; margin: 4px 0; background: rgba(20, 24, 35, 0.6); 
                                    border-left: 3px solid rgba(108, 99, 255, 0.3); border-radius: 4px; 
                                    font-size: 0.82rem; color: #94A3B8; font-family: 'Courier New', monospace;">
                                    {msg}
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Summary stats
                            st.markdown("<br>", unsafe_allow_html=True)
                            cs1, cs2, cs3 = st.columns(3)
                            with cs1:
                                st.markdown(f"""
                                <div class="kpi-stat">
                                    <div class="kpi-value">{baris_bersih}</div>
                                    <div class="kpi-label">Baris Diproses</div>
                                </div>
                                """, unsafe_allow_html=True)
                            with cs2:
                                baru_color = "#10B981" if baris_baru > 0 else "#F59E0B"
                                st.markdown(f"""
                                <div class="kpi-stat">
                                    <div class="kpi-value" style="background: linear-gradient(135deg, {baru_color}, {baru_color}aa); 
                                        -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
                                        +{baris_baru}
                                    </div>
                                    <div class="kpi-label">Baris Baru Ditambahkan</div>
                                </div>
                                """, unsafe_allow_html=True)
                            with cs3:
                                st.markdown(f"""
                                <div class="kpi-stat">
                                    <div class="kpi-value">{baris_fakta}</div>
                                    <div class="kpi-label">Total di Database</div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                    except Exception as e:
                        st.markdown(f"""
                        <div class="status-danger">
                            <p><strong>ETL Gagal:</strong> {e}</p>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="premium-card" style="border-left: 4px solid #EF4444;">
                <h4 style="color: #FCA5A5;">Tidak Dapat Diproses</h4>
                <p>Perbaiki error di atas terlebih dahulu sebelum data dapat dimuat ke database.</p>
            </div>
            """, unsafe_allow_html=True)
