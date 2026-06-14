import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px

def render(df):
    st.title("🏠 Ringkasan Kualitas Udara")
    
    # Mencari tanggal paling baru
    latest_date = df['tanggal'].max()
    df_latest = df[df['tanggal'] == latest_date]
    tanggal_str = latest_date.strftime('%d %B %Y')
    
    # ==========================================
    # 1. KPI & STATUS TERKINI
    # ==========================================
    st.subheader(f"Status Kualitas Udara Terkini: {tanggal_str}")
    
    col1, col2 = st.columns(2)
    avg_ispu = df_latest['nilai_max_ispu'].mean() if not df_latest.empty else 0
    dom_pol = df_latest['polutan_kritis'].mode()[0] if not df_latest.empty else "-"
    
    with col1:
        st.metric("Rata-rata ISPU Hari Ini", f"{avg_ispu:.1f}")
    with col2:
        st.metric("Polutan Paling Dominan", dom_pol)

    # ==========================================
    # 2. STATUS PERINGATAN TERKINI
    # ==========================================
    st.write(f"**Status Peringatan Terkini: {tanggal_str}**")
    df_kritis = df_latest[df_latest['nilai_max_ispu'] > 100].sort_values(by='nilai_max_ispu', ascending=False)
    
    if not df_kritis.empty:
        st.error(f"🚨 PERHATIAN! Terdeteksi {len(df_kritis)} wilayah dengan kualitas udara TIDAK SEHAT atau lebih buruk.")
        for idx, row in df_kritis.iterrows():
            st.warning(f"📍 **{row['nama_stasiun']}** | ISPU: **{row['nilai_max_ispu']}** ({row['nama_kategori']}) | Polutan: **{row['polutan_kritis']}**")
    else:
        st.success("✅ Seluruh stasiun pemantau melaporkan kualitas udara dalam batas AMAN (Kategori Baik/Sedang). Tidak ada peringatan yang perlu ditindaklanjuti.")

    # ==========================================
    # 3. GRAFIK HORIZONTAL POLUTAN (TERKINI)
    # ==========================================
    st.write("**Rincian Konsentrasi Polutan per Stasiun (Hari Ini)**")
    if not df_latest.empty:
        # Menyiapkan data untuk grafik grouped bar chart
        df_pollutants = df_latest[['nama_stasiun', 'pm10', 'pm25', 'so2', 'co', 'o3', 'no2']]
        df_melted = df_pollutants.melt(id_vars='nama_stasiun', var_name='Jenis Polutan', value_name='Konsentrasi')
        df_melted['Jenis Polutan'] = df_melted['Jenis Polutan'].str.upper()
        
        fig_bar = px.bar(
            df_melted, 
            y='nama_stasiun', 
            x='Konsentrasi', 
            color='Jenis Polutan', 
            orientation='h',
            barmode='group', # Menampilkan bar secara bersebelahan, bukan ditumpuk
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_bar.update_layout(yaxis_title="Stasiun Pemantau", xaxis_title="Konsentrasi (µg/m³)", margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # ==========================================
    # 4. PETA SPASIAL (EKSPLORASI HISTORIS)
    # ==========================================
    st.subheader("🗺️ Pemetaan Spasial Wilayah Kritis Polusi")
    st.write("Visualisasi geografis lokasi stasiun SPKU di DKI Jakarta. Gunakan filter di bawah untuk melihat kondisi historis.")
    
    # Filter Tanggal (Sesuai kode peta sebelumnya)
    col_thn, col_bln, col_tgl = st.columns(3)
    
    with col_thn:
        daftar_tahun = sorted(df['tanggal'].dt.year.unique(), reverse=True)
        pilih_tahun = st.selectbox("Pilih Tahun:", options=daftar_tahun)
    df_tahun = df[df['tanggal'].dt.year == pilih_tahun]
    
    with col_bln:
        daftar_bulan = sorted(df_tahun['tanggal'].dt.month.unique(), reverse=True)
        nama_bulan = {1:'Januari', 2:'Februari', 3:'Maret', 4:'April', 5:'Mei', 6:'Juni', 
                      7:'Juli', 8:'Agustus', 9:'September', 10:'Oktober', 11:'November', 12:'Desember'}
        pilih_bulan = st.selectbox("Pilih Bulan:", options=daftar_bulan, format_func=lambda x: nama_bulan[x])
    df_bulan = df_tahun[df_tahun['tanggal'].dt.month == pilih_bulan]
    
    with col_tgl:
        daftar_hari = sorted(df_bulan['tanggal'].dt.day.unique(), reverse=True)
        pilih_hari = st.selectbox("Pilih Tanggal:", options=daftar_hari)
        
    tanggal_gabungan = pd.to_datetime(f"{pilih_tahun}-{pilih_bulan:02d}-{pilih_hari:02d}")
    df_map = df[df['tanggal'] == tanggal_gabungan]
    
    col_peta, col_info = st.columns([2, 1])
    
    with col_peta:
        m = folium.Map(location=[-6.2088, 106.8456], zoom_start=11, tiles="OpenStreetMap")
        df_stasiun = df[['nama_stasiun', 'wilayah', 'latitude', 'longitude']].drop_duplicates()
        
        for idx, stasiun_row in df_stasiun.iterrows():
            nama = stasiun_row['nama_stasiun']
            data_hari_ini = df_map[df_map['nama_stasiun'] == nama]
            
            if not data_hari_ini.empty:
                row = data_hari_ini.iloc[0]
                kategori = row['nama_kategori']
                ispu_val = row['nilai_max_ispu']
                polutan = row['polutan_kritis']
                
                if kategori == 'BAIK': color = 'green'
                elif kategori == 'SEDANG': color = 'blue'
                elif kategori == 'TIDAK SEHAT': color = 'orange'
                elif kategori == 'SANGAT TIDAK SEHAT': color = 'red'
                elif kategori == 'BERBAHAYA': color = 'darkred'
                else: color = 'lightgray'
            else:
                kategori = 'TIDAK ADA DATA'
                ispu_val = '-'
                polutan = '-'
                color = 'lightgray'
                
            popup_html = f"<div style='font-family: Arial; width: 180px;'><h4><b>{nama}</b></h4><p><b>Wilayah:</b> {stasiun_row['wilayah']}</p><p><b>ISPU:</b> {ispu_val}</p><p><b>Status:</b> <span style='color:{color}; font-weight:bold;'>{kategori}</span></p><p><b>Polutan Kritis:</b> {polutan}</p></div>"
            folium.Marker(location=[stasiun_row['latitude'], stasiun_row['longitude']], popup=folium.Popup(popup_html, max_width=250), tooltip=nama, icon=folium.Icon(color=color, icon='info-sign')).add_to(m)
            
        st_folium(m, width=700, height=500, returned_objects=[])

    with col_info:
        st.write("**Detail Parameter Stasiun**")
        if not df_map.empty:
            df_ringkas = df_map[['nama_stasiun', 'wilayah', 'nilai_max_ispu', 'nama_kategori', 'polutan_kritis']]
            df_ringkas.columns = ['Stasiun', 'Wilayah', 'ISPU', 'Kategori', 'Polutan Kritis']
            st.dataframe(df_ringkas, use_container_width=True, hide_index=True)
        else:
            st.info("Tidak ada pencatatan data polusi pada tanggal ini.")
        
        st.markdown("""
        **Legenda Warna Pin:**
        * 🟢 Hijau: BAIK
        * 🔵 Biru: SEDANG
        * 🟡 Orange: TIDAK SEHAT
        * 🔴 Merah: SANGAT TIDAK SEHAT
        * 🟤 Merah Gelap: BERBAHAYA
        * ⚪ Abu-abu: TIDAK ADA DATA
        """)

    st.divider()

    # ==========================================
    # 5. RATA-RATA ISPU HISTORIS (KESELURUHAN)
    # ==========================================
    st.subheader("Rata-rata ISPU Historis per Stasiun (Keseluruhan)")
    avg_per_station = df.groupby('nama_stasiun')['nilai_max_ispu'].mean().reset_index()
    avg_per_station = avg_per_station.sort_values(by='nilai_max_ispu', ascending=False)
    
    fig_avg = px.bar(
        avg_per_station, 
        x='nama_stasiun', 
        y='nilai_max_ispu',
        labels={'nama_stasiun': 'Stasiun Pemantau', 'nilai_max_ispu': 'Rata-rata Nilai ISPU'},
        color='nilai_max_ispu',
        color_continuous_scale='RdYlGn_r',
        text_auto='.1f'
    )
    fig_avg.update_layout(xaxis_title="Stasiun", yaxis_title="Nilai ISPU Keseluruhan")
    st.plotly_chart(fig_avg, use_container_width=True)

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