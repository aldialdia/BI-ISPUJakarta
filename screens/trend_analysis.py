import streamlit as st
import pandas as pd
import plotly.express as px

def render(df):
    st.title("📈 Analisis Tren Historis Kualitas Udara")
    st.write("Evaluasi pergerakan nilai ISPU dan konsentrasi polutan spesifik dari waktu ke waktu untuk mendukung pengambilan keputusan.")
    
    st.subheader("Filter Analisis")
    col1, col2 = st.columns(2)
    
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
        
    if not pilihan_stasiun:
        st.warning("Silakan pilih minimal satu stasiun pemantau untuk menampilkan grafik.")
        return
        
    df_filtered = df[(df['nama_stasiun'].isin(pilihan_stasiun)) & (df['tahun'] == pilihan_tahun)]
    
    st.divider()
    
    st.subheader(f"Pergerakan Nilai ISPU Harian - Tahun {pilihan_tahun}")
    
    if df_filtered.empty:
        st.info("Data tidak tersedia untuk kombinasi filter yang dipilih.")
    else:
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
        
        fig_ispu.update_layout(xaxis_title="Bulan", yaxis_title="Indeks Standar Pencemar Udara")
        st.plotly_chart(fig_ispu, use_container_width=True)
        
        st.subheader("Drill-down: Analisis Parameter Polutan")
        st.write("Pilih parameter spesifik untuk melihat tren konsentrasinya secara detail.")
        
        polutan_pilihan = st.selectbox(
            "Pilihan Parameter:", 
            ['pm10', 'pm25', 'so2', 'co', 'o3', 'no2']
        )
        
        fig_polutan = px.line(
            df_filtered,
            x='tanggal',
            y=polutan_pilihan,
            color='nama_stasiun',
            labels={'tanggal': 'Tanggal', polutan_pilihan: f'Konsentrasi {polutan_pilihan.upper()} (µg/m³)'}
        )
        fig_polutan.update_layout(xaxis_title="Bulan", yaxis_title="Konsentrasi")
        st.plotly_chart(fig_polutan, use_container_width=True)