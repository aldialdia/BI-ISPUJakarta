import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

def render(df):
    st.title("🗺️ Pemetaan Spasial Wilayah Kritis Polusi")
    st.write("Visualisasi geografis lokasi stasiun SPKU di DKI Jakarta dengan indikator warna sesuai kualitas udara waktu nyata/historis.")
    
    st.subheader("Filter Tanggal Pemetaan")
    
    # 1. Membagi filter menjadi 3 kolom sejajar
    col_thn, col_bln, col_tgl = st.columns(3)
    
    with col_thn:
        # Tahun diurutkan menurun (terbaru di atas)
        daftar_tahun = sorted(df['tanggal'].dt.year.unique(), reverse=True)
        pilih_tahun = st.selectbox("Pilih Tahun:", options=daftar_tahun)
        
    df_tahun = df[df['tanggal'].dt.year == pilih_tahun]
    
    with col_bln:
        # TAMBAHAN: Bulan diurutkan menurun (terbaru di atas)
        daftar_bulan = sorted(df_tahun['tanggal'].dt.month.unique(), reverse=True)
        nama_bulan = {1:'Januari', 2:'Februari', 3:'Maret', 4:'April', 5:'Mei', 6:'Juni', 
                      7:'Juli', 8:'Agustus', 9:'September', 10:'Oktober', 11:'November', 12:'Desember'}
        pilih_bulan = st.selectbox("Pilih Bulan:", options=daftar_bulan, format_func=lambda x: nama_bulan[x])
        
    df_bulan = df_tahun[df_tahun['tanggal'].dt.month == pilih_bulan]
    
    with col_tgl:
        # TAMBAHAN: Tanggal diurutkan menurun (terbaru di atas)
        daftar_hari = sorted(df_bulan['tanggal'].dt.day.unique(), reverse=True)
        pilih_hari = st.selectbox("Pilih Tanggal:", options=daftar_hari)
        
    # 2. Menggabungkan pilihan menjadi format tanggal utuh
    tanggal_gabungan = pd.to_datetime(f"{pilih_tahun}-{pilih_bulan:02d}-{pilih_hari:02d}")
    
    df_map = df[df['tanggal'] == tanggal_gabungan]
    
    st.divider()
    
    col_peta, col_info = st.columns([2, 1])
    
    with col_peta:
        st.subheader("Peta Sebaran Kualitas Udara")
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
                
                if kategori == 'BAIK':
                    color = 'green'
                elif kategori == 'SEDANG':
                    color = 'blue'
                elif kategori == 'TIDAK SEHAT':
                    color = 'orange'
                elif kategori == 'SANGAT TIDAK SEHAT':
                    color = 'red'
                elif kategori == 'BERBAHAYA':
                    color = 'darkred'
                else:
                    color = 'lightgray'
            else:
                kategori = 'TIDAK ADA DATA'
                ispu_val = '-'
                polutan = '-'
                color = 'lightgray'
                
            popup_html = f"""
            <div style='font-family: Arial, sans-serif; width: 180px;'>
                <h4><b>{nama}</b></h4>
                <p><b>Wilayah:</b> {stasiun_row['wilayah']}</p>
                <p><b>Nilai ISPU:</b> {ispu_val}</p>
                <p><b>Status:</b> <span style='color:{color}; font-weight:bold;'>{kategori}</span></p>
                <p><b>Polutan Kritis:</b> {polutan}</p>
            </div>
            """
            
            folium.Marker(
                location=[stasiun_row['latitude'], stasiun_row['longitude']],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=nama,
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(m)
            
        st_folium(m, width=700, height=500, returned_objects=[])

    with col_info:
        st.subheader("Detail Parameter Stasiun")
        st.write("Klik salah satu stasiun di peta untuk melihat detail, atau lihat ringkasan tabel di bawah ini:")
        
        if not df_map.empty:
            df_ringkas = df_map[['nama_stasiun', 'wilayah', 'nilai_max_ispu', 'nama_kategori', 'polutan_kritis']]
            df_ringkas.columns = ['Stasiun', 'Wilayah', 'ISPU', 'Kategori', 'Polutan Kritis']
            st.dataframe(df_ringkas, use_container_width=True, hide_index=True)
        else:
            st.info("Tidak ada pencatatan data polusi pada tanggal ini.")
        
        st.markdown("""
        **Legenda Warna Pin:**
        * 🟢 **Hijau**: BAIK
        * 🔵 **Biru**: SEDANG
        * 🟡 **Orange**: TIDAK SEHAT
        * 🔴 **Merah**: SANGAT TIDAK SEHAT
        * 🟤 **Merah Gelap**: BERBAHAYA
        * ⚪ **Abu-abu**: TIDAK ADA DATA
        """)