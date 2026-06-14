import streamlit as st
import pandas as pd
import plotly.express as px

def render(df):
    st.title("📈 Analisis Tren Historis Kualitas Udara")
    st.write("Evaluasi pergerakan nilai ISPU dan konsentrasi polutan spesifik dari waktu ke waktu untuk mendukung pengambilan keputusan.")
    
    # ==========================================
    # 1. KOTAK FILTER (STASIUN, TAHUN, BULAN)
    # ==========================================
    st.subheader("Filter Analisis")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        daftar_stasiun = df['nama_stasiun'].unique()
        pilihan_stasiun = st.multiselect(
            "Pilih Stasiun Pemantau:", 
            options=daftar_stasiun, 
            default=[daftar_stasiun[0]] 
        )
        
    with col2:
        daftar_tahun = sorted(df['tahun'].unique(), reverse=True)
        pilihan_tahun = st.selectbox("Pilih Tahun:", options=daftar_tahun)
        
    with col3:
        # Mencari bulan yang tersedia pada tahun terpilih
        bulan_tersedia = sorted(df[df['tahun'] == pilihan_tahun]['tanggal'].dt.month.unique())
        nama_bulan = {1:'Januari', 2:'Februari', 3:'Maret', 4:'April', 5:'Mei', 6:'Juni', 
                      7:'Juli', 8:'Agustus', 9:'September', 10:'Oktober', 11:'November', 12:'Desember'}
        
        opsi_bulan = ["Semua Bulan"] + [nama_bulan[b] for b in bulan_tersedia]
        pilihan_bulan = st.selectbox("Pilih Bulan (Opsional):", options=opsi_bulan)
        
    if not pilihan_stasiun:
        st.warning("Silakan pilih minimal satu stasiun pemantau untuk menampilkan grafik.")
        return
        
    # Menerapkan Filter ke DataFrame
    if pilihan_bulan != "Semua Bulan":
        inv_nama_bulan = {v: k for k, v in nama_bulan.items()}
        bln_angka = inv_nama_bulan[pilihan_bulan]
        df_filtered = df[(df['nama_stasiun'].isin(pilihan_stasiun)) & (df['tahun'] == pilihan_tahun) & (df['tanggal'].dt.month == bln_angka)].copy()
        periode_teks = f"Bulan {pilihan_bulan} {pilihan_tahun}"
    else:
        df_filtered = df[(df['nama_stasiun'].isin(pilihan_stasiun)) & (df['tahun'] == pilihan_tahun)].copy()
        periode_teks = f"Tahun {pilihan_tahun}"
    
    st.divider()
    
    # ==========================================
    # 2. TREN ISPU KESELURUHAN & INSIGHT CARDS
    # ==========================================
    st.subheader(f"Pergerakan Nilai ISPU Harian - {periode_teks}")
    
    if df_filtered.empty:
        st.info("Data tidak tersedia untuk kombinasi filter yang dipilih.")
        return
        
    fig_ispu = px.line(
        df_filtered, 
        x='tanggal', 
        y='nilai_max_ispu', 
        color='nama_stasiun',
        labels={'tanggal': 'Tanggal', 'nilai_max_ispu': 'Nilai ISPU Max', 'nama_stasiun': 'Stasiun'},
        markers=False
    )
    
    fig_ispu.add_hline(
        y=100, 
        line_dash="dash", 
        line_color="red", 
        annotation_text="Ambang Batas Tidak Sehat (>100)",
        annotation_position="top right"
    )
    fig_ispu.update_layout(xaxis_title="Waktu", yaxis_title="Indeks Standar Pencemar Udara")
    st.plotly_chart(fig_ispu, use_container_width=True)
    
    # --- SECTION 1: 3 INSIGHT CARDS ---
    curr_avg = df_filtered['nilai_max_ispu'].mean()
    
    # Logika dinamis untuk membandingkan dengan periode sebelumnya
    if pilihan_bulan != "Semua Bulan":
        prev_m = bln_angka - 1 if bln_angka > 1 else 12
        prev_y = pilihan_tahun if bln_angka > 1 else pilihan_tahun - 1
        df_prev = df[(df['nama_stasiun'].isin(pilihan_stasiun)) & (df['tahun'] == prev_y) & (df['tanggal'].dt.month == prev_m)]
    else:
        df_prev = df[(df['nama_stasiun'].isin(pilihan_stasiun)) & (df['tahun'] == pilihan_tahun - 1)]
    
    if not df_prev.empty:
        prev_avg = df_prev['nilai_max_ispu'].mean()
        pct_change = ((curr_avg - prev_avg) / prev_avg) * 100
        status_tren = "naik" if pct_change >= 0 else "turun"
        isi_card_1 = f"Rata-rata ISPU {periode_teks} **{status_tren} {abs(pct_change):.1f}%** dibanding periode sebelumnya."
    else:
        isi_card_1 = f"Rata-rata ISPU {periode_teks} adalah **{curr_avg:.1f}**. Data periode sebelumnya tidak tersedia."

    hari_melampaui = df_filtered[df_filtered['nilai_max_ispu'] > 100]['tanggal'].dt.date.nunique()
    isi_card_2 = f"Terdeteksi **{hari_melampaui} hari** dengan nilai ISPU > 100 (Tidak Sehat) pada periode dan stasiun terpilih."

    idx_max = df_filtered['nilai_max_ispu'].idxmax()
    val_max = df_filtered.loc[idx_max, 'nilai_max_ispu']
    date_max = df_filtered.loc[idx_max, 'tanggal'].strftime('%d %b %Y')
    sta_max = df_filtered.loc[idx_max, 'nama_stasiun']
    isi_card_3 = f"Puncak polusi tertinggi terjadi pada **{date_max}** sebesar **{val_max}** di stasiun **{sta_max}**."

    c1, c2, c3 = st.columns(3)
    with c1:
        st.info(f"**📈 Tren Keseluruhan**\n\n{isi_card_1}")
    with c2:
        st.error(f"**⚠️ Hari Melampaui Batas**\n\n{isi_card_2}")
    with c3:
        st.warning(f"**📅 Puncak Tertinggi**\n\n{isi_card_3}")

    st.divider()

    # ==========================================
    # 3. DRILL-DOWN PARAMETER & INSIGHT CARDS
    # ==========================================
    st.subheader("Drill-down: Analisis Parameter Polutan")
    st.write("Pilih parameter spesifik untuk melihat tren konsentrasinya secara detail.")
    
    polutan_pilihan = st.selectbox(
        "Pilihan Parameter:", 
        ['pm10', 'pm25', 'so2', 'co', 'o3', 'no2'],
        format_func=lambda x: x.upper()
    )
    
    fig_polutan = px.line(
        df_filtered,
        x='tanggal',
        y=polutan_pilihan,
        color='nama_stasiun',
        labels={'tanggal': 'Waktu', polutan_pilihan: f'Konsentrasi {polutan_pilihan.upper()} (µg/m³)'}
    )
    fig_polutan.update_layout(xaxis_title="Waktu", yaxis_title="Konsentrasi")
    st.plotly_chart(fig_polutan, use_container_width=True)
    
    # --- SECTION 2: 2 INSIGHT CARDS ---
    # Logika Kronologis: Membandingkan rata-rata hari pertama vs hari terakhir dari data yang difilter
    df_pol_grouped = df_filtered.groupby('tanggal')[polutan_pilihan].mean().reset_index().sort_values('tanggal')
    
    if len(df_pol_grouped) > 1:
        val_awal = df_pol_grouped.iloc[0][polutan_pilihan]
        val_akhir = df_pol_grouped.iloc[-1][polutan_pilihan]
        tgl_awal = df_pol_grouped.iloc[0]['tanggal'].strftime('%d %b')
        tgl_akhir = df_pol_grouped.iloc[-1]['tanggal'].strftime('%d %b')
        
        pct_change_pol = ((val_akhir - val_awal) / val_awal * 100) if val_awal > 0 else 0
        status_pol = "meningkat" if pct_change_pol > 0 else "menurun"
        isi_card_pol_1 = f"Secara garis waktu, rata-rata konsentrasi {polutan_pilihan.upper()} **{status_pol} sebesar {abs(pct_change_pol):.1f}%** (dari {val_awal:.1f} pada {tgl_awal} menjadi {val_akhir:.1f} pada {tgl_akhir})."
        judul_card_pol_1 = "📊 Tren Perubahan Polutan"
    else:
        isi_card_pol_1 = "Data tidak cukup untuk menghitung tren perubahan awal hingga akhir periode."
        judul_card_pol_1 = "📊 Tren Perubahan Polutan"

    konteks_dict = {
        "PM10": "Dominan dari debu jalanan, aktivitas konstruksi fisik, dan partikel kasar.",
        "PM25": "Partikel halus berbahaya, bersumber kuat dari emisi gas buang kendaraan & proses pembakaran.",
        "SO2": "Berasal dari industri manufaktur atau pembakaran bahan bakar fosil tinggi belerang.",
        "CO": "Hasil emisi kendaraan bermotor akibat pembakaran tidak sempurna, beracun di ruang terbatas.",
        "O3": "Polutan sekunder yang terbentuk akibat reaksi kimia sinar matahari (UV) dengan gas polutan lain.",
        "NO2": "Sangat identik dengan kepadatan volume kendaraan bermotor dan aktivitas pembangkit listrik."
    }
    isi_card_pol_2 = konteks_dict.get(polutan_pilihan.upper(), "")

    cp1, cp2 = st.columns(2)
    with cp1:
        st.warning(f"**{judul_card_pol_1}**\n\n{isi_card_pol_1}")
    with cp2:
        st.info(f"**💡 Konteks Polutan**\n\n{isi_card_pol_2}")

    st.divider()

    # ==========================================
    # 4. DAMPAK MOBILITAS (HARI KERJA VS LIBUR)
    # ==========================================
    st.subheader("Dampak Aktivitas Harian terhadap Kualitas Udara")
    st.write("Perbandingan rata-rata ISPU berdasarkan tipe mobilitas harian pada periode terpilih.")

    def tentukan_tipe_hari(row):
        if row['is_holiday'] == 1 or row['is_holiday'] == True:
            return 'Libur Nasional'
        elif row['is_weekend'] == 1 or row['is_weekend'] == True:
            return 'Akhir Pekan (Weekend)'
        else:
            return 'Hari Kerja (Weekday)'

    df_filtered['Tipe Hari'] = df_filtered.apply(tentukan_tipe_hari, axis=1)
    df_aktivitas = df_filtered.groupby('Tipe Hari', observed=False)['nilai_max_ispu'].mean().reset_index()
    
    urutan_hari = ['Hari Kerja (Weekday)', 'Akhir Pekan (Weekend)', 'Libur Nasional']
    df_aktivitas['Tipe Hari'] = pd.Categorical(df_aktivitas['Tipe Hari'], categories=urutan_hari, ordered=True)
    df_aktivitas = df_aktivitas.sort_values('Tipe Hari')

    col_chart, col_desc = st.columns([2, 1])
    
    with col_chart:
        fig_bar = px.bar(
            df_aktivitas, 
            x='Tipe Hari', 
            y='nilai_max_ispu',
            color='Tipe Hari',
            color_discrete_map={
                'Hari Kerja (Weekday)': '#378ADD',
                'Akhir Pekan (Weekend)': '#1D9E75',
                'Libur Nasional': '#BA7517'
            },
            text_auto='.1f',
            labels={'nilai_max_ispu': 'Rata-rata ISPU'}
        )
        fig_bar.update_layout(showlegend=False, xaxis_title="", yaxis_title="Rata-rata ISPU")
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with col_desc:
        st.info("**💡 Insight Otomatis:**")
        if not df_aktivitas.empty and not df_aktivitas['nilai_max_ispu'].isna().all():
            row_tertinggi = df_aktivitas.loc[df_aktivitas['nilai_max_ispu'].idxmax()]
            tipe_tertinggi = row_tertinggi['Tipe Hari']
            nilai_tertinggi = row_tertinggi['nilai_max_ispu']
            
            teks_insight = f"Pada klaster stasiun ini, rata-rata indeks polusi tertinggi tercatat pada **{tipe_tertinggi}** dengan nilai **{nilai_tertinggi:.1f}**. \n\n"
            
            if tipe_tertinggi == 'Hari Kerja (Weekday)':
                teks_insight += "Mengonfirmasi secara kuat bahwa aktivitas komuter bekerja harian dan volume kendaraan bermotor adalah pemicu utama polusi."
            elif tipe_tertinggi == 'Akhir Pekan (Weekend)':
                teks_insight += "Mengindikasikan adanya lonjakan mobilitas lokal untuk rekreasi atau pergerakan massa wisata di sekitar wilayah stasiun terpilih."
            elif tipe_tertinggi == 'Libur Nasional':
                teks_insight += "Dipengaruhi oleh aktivitas libur panjang atau penumpukan volume kendaraan pada event nasional tertentu."
                
            st.write(teks_insight)
        else:
            st.write("Data tidak mencukupi untuk menghasilkan insight.")