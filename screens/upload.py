import streamlit as st
import pandas as pd
import os
import html as html_lib
from etl.etl_core import (
    run_etl,
    validate_dataframe,
    STASIUN_VALID,
    KOLOM_WAJIB,
    KATEGORI_VALID,
    DEFAULT_LOG_DIR,
)


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


def render():
    st.title("Upload & Pembaruan Data")
    st.caption("Unggah file CSV data ISPU untuk memperbarui database dashboard")

    # ============================================================
    # SECTION: Template Data
    # ============================================================
    st.subheader("Template Data")
    st.markdown("""
    <div class="premium-card">
        <h4>Format Standar File CSV</h4>
        <p>Unduh template di bawah sebagai acuan format file yang dapat diproses oleh sistem.
        Pastikan file yang diunggah mengikuti struktur kolom yang sama.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

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
        # Daftar stasiun diambil dari etl_core (single source of truth)
        stasiun_html = "<br>".join(STASIUN_VALID.keys())
        st.markdown(f"""
        <div class="insight-card" style="text-align: center;">
            <h4>Stasiun yang Dikenali</h4>
            <p style="font-size: 0.82rem; line-height: 2;">
                {stasiun_html}
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

    # ============================================================
    # SECTION: Upload File
    # ============================================================
    st.divider()
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

        # --- Validasi (dari etl_core) ---
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

            col_btn, col_space = st.columns([1, 3])
            with col_btn:
                proses = st.button("Proses & Muat ke Database", type="primary", use_container_width=True)

            if proses:
                with st.spinner("Menjalankan proses ETL..."):
                    try:
                        # Panggil ETL dari etl_core (satu sumber kebenaran)
                        result = run_etl(df_upload)

                        if result['success']:
                            if result['baris_baru'] > 0:
                                st.markdown(f"""
                                <div class="status-safe">
                                    <p><strong>ETL Berhasil!</strong> Sebanyak <strong>{result['baris_baru']} baris baru</strong>
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

                            # Bersihkan cache agar dashboard memuat data terbaru
                            st.cache_data.clear()

                            # --- Statistik KPI ---
                            st.markdown("<br>", unsafe_allow_html=True)
                            cs1, cs2, cs3 = st.columns(3)
                            with cs1:
                                st.markdown(f"""
                                <div class="kpi-stat">
                                    <div class="kpi-value">{result['baris_diproses']}</div>
                                    <div class="kpi-label">Baris Diproses</div>
                                </div>
                                """, unsafe_allow_html=True)
                            with cs2:
                                baru_color = "#10B981" if result['baris_baru'] > 0 else "#F59E0B"
                                st.markdown(f"""
                                <div class="kpi-stat">
                                    <div class="kpi-value" style="background: linear-gradient(135deg, {baru_color}, {baru_color}aa);
                                        -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
                                        +{result['baris_baru']}
                                    </div>
                                    <div class="kpi-label">Baris Baru Ditambahkan</div>
                                </div>
                                """, unsafe_allow_html=True)
                            with cs3:
                                st.markdown(f"""
                                <div class="kpi-stat">
                                    <div class="kpi-value">{result['total_di_database']}</div>
                                    <div class="kpi-label">Total di Database</div>
                                </div>
                                """, unsafe_allow_html=True)

                            # --- Tampilkan log file yang baru dibuat ---
                            st.markdown("<br>", unsafe_allow_html=True)
                            st.markdown("**Log Proses ETL**")
                            _render_log_content(result['log_filepath'])

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

    # ============================================================
    # SECTION: Riwayat Log ETL
    # ============================================================
    st.divider()
    st.subheader("Riwayat Log ETL")
    st.caption("Catatan proses ETL yang tersimpan dari eksekusi terminal maupun web")

    if os.path.exists(DEFAULT_LOG_DIR):
        log_files = sorted(
            [f for f in os.listdir(DEFAULT_LOG_DIR) if f.endswith('.log')],
            reverse=True
        )
        if log_files:
            selected_log = st.selectbox("Pilih File Log", options=log_files)
            log_path = os.path.join(DEFAULT_LOG_DIR, selected_log)
            _render_log_content(log_path)

            # Download button
            with open(log_path, 'r', encoding='utf-8') as f:
                log_data = f.read()
            st.download_button(
                label="Download Log File",
                data=log_data,
                file_name=selected_log,
                mime="text/plain",
            )
        else:
            st.markdown("""
            <div class="premium-card">
                <p>Belum ada file log ETL yang tersimpan. Jalankan proses ETL terlebih dahulu
                melalui upload di atas atau via terminal.</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="premium-card">
            <p>Belum ada file log ETL yang tersimpan. Jalankan proses ETL terlebih dahulu
            melalui upload di atas atau via terminal.</p>
        </div>
        """, unsafe_allow_html=True)


def _render_log_content(log_filepath):
    """Render isi file log dalam container bergaya terminal."""
    try:
        with open(log_filepath, 'r', encoding='utf-8') as f:
            raw_content = f.read()
    except Exception:
        st.info("Tidak dapat membaca file log.")
        return

    # Escape HTML dan beri warna pada level log
    escaped = html_lib.escape(raw_content)
    escaped = escaped.replace(
        '[WARNING]',
        '<span style="color: #FCD34D; font-weight: 600;">[WARNING]</span>'
    )
    escaped = escaped.replace(
        '[ERROR]',
        '<span style="color: #FCA5A5; font-weight: 600;">[ERROR]</span>'
    )
    escaped = escaped.replace(
        '[INFO]',
        '<span style="color: #6EE7B7;">[INFO]</span>'
    )

    st.markdown(f"""
    <div style="
        background: rgba(13, 17, 23, 0.95);
        border: 1px solid rgba(108, 99, 255, 0.2);
        border-radius: 12px;
        padding: 20px;
        max-height: 420px;
        overflow-y: auto;
        font-family: 'Courier New', 'Consolas', monospace;
        font-size: 0.76rem;
        line-height: 1.7;
        color: #94A3B8;
        white-space: pre-wrap;
        word-break: break-all;
    ">{escaped}</div>
    """, unsafe_allow_html=True)
