import streamlit as st
import pandas as pd

def render(df):
    st.title("⚠️ Sistem Peringatan Dini (Early Warning System)")
    st.write("Halaman ini secara otomatis mendeteksi stasiun dengan tingkat polusi yang membahayakan kesehatan (ISPU > 100) untuk tindakan mitigasi cepat.")
    
    st.divider()
    
    # ==========================================
    # 1. ANALISIS KONDISI HARI INI (TERKINI)
    # ==========================================
    latest_date = df['tanggal'].max()
    df_latest = df[df['tanggal'] == latest_date]
    
    st.subheader(f"Status Peringatan Terkini: {latest_date.strftime('%d %B %Y')}")
    
    # Memfilter data yang melebihi batas aman (ISPU > 100)
    df_kritis = df_latest[df_latest['nilai_max_ispu'] > 100].sort_values(by='nilai_max_ispu', ascending=False)
    
    # Jika ada stasiun yang kritis, munculkan Alert Merah/Kuning
    if not df_kritis.empty:
        st.error(f"🚨 PERHATIAN! Terdeteksi {len(df_kritis)} wilayah dengan kualitas udara TIDAK SEHAT atau lebih buruk pada pencatatan terakhir.")
        
        # Tampilkan kotak peringatan untuk masing-masing stasiun yang bermasalah
        for idx, row in df_kritis.iterrows():
            with st.container():
                st.warning(
                    f"📍 **{row['nama_stasiun']} ({row['wilayah']})** \n\n"
                    f"Kategori: **{row['nama_kategori']}** | Nilai ISPU: **{row['nilai_max_ispu']}** | Polutan Pemicu: **{row['polutan_kritis']}**"
                )
    else:
        # Jika semua aman (ISPU <= 100)
        st.success("✅ Seluruh stasiun pemantau melaporkan kualitas udara dalam batas AMAN (Kategori Baik/Sedang). Tidak ada peringatan yang perlu ditindaklanjuti.")
        
    st.divider()

    # ==========================================
    # 2. RIWAYAT PERINGATAN (30 HARI TERAKHIR)
    # ==========================================
    st.subheader("Riwayat Hari Kritis (30 Hari Terakhir)")
    st.write("Daftar stasiun yang pernah melewati batas aman dalam satu bulan terakhir untuk keperluan evaluasi efektivitas kebijakan.")
    
    # Menghitung batas tanggal 30 hari ke belakang dari tanggal terbaru
    date_30_days_ago = latest_date - pd.Timedelta(days=30)
    
    # Filter histori: dalam 30 hari terakhir DAN nilai ISPU > 100
    df_history = df[(df['tanggal'] >= date_30_days_ago) & (df['nilai_max_ispu'] > 100)]
    
    if not df_history.empty:
        # Merapikan tabel untuk ditampilkan
        df_history_show = df_history[['tanggal', 'nama_stasiun', 'wilayah', 'nama_kategori', 'nilai_max_ispu', 'polutan_kritis']].copy()
        df_history_show = df_history_show.sort_values(by=['tanggal', 'nilai_max_ispu'], ascending=[False, False])
        
        # Format kolom tanggal agar lebih mudah dibaca
        df_history_show['tanggal'] = df_history_show['tanggal'].dt.strftime('%d %B %Y')
        df_history_show.columns = ['Tanggal', 'Stasiun', 'Wilayah', 'Kategori', 'ISPU', 'Polutan Kritis']
        
        st.dataframe(df_history_show, use_container_width=True, hide_index=True)
    else:
        st.info("Tidak ada riwayat peringatan dalam 30 hari terakhir. Kualitas udara cenderung stabil dan aman.")