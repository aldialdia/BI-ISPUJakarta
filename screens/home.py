import streamlit as st
import pandas as pd
import plotly.express as px

def render(df):
    st.title("🏠 Ringkasan Kualitas Udara (Home)")
    
    # Mencari tanggal paling baru di dalam dataset
    latest_date = df['tanggal'].max()
    df_latest = df[df['tanggal'] == latest_date]
    
    st.subheader(f"Status Kualitas Udara Terkini: {latest_date.strftime('%d %B %Y')}")
    
    # 1. Menampilkan KPI (Key Performance Indicators)
    col1, col2, col3 = st.columns(3)
    
    avg_ispu = df_latest['nilai_max_ispu'].mean()
    dominant_pollutant = df_latest['polutan_kritis'].mode()[0] # Polutan yang paling sering muncul
    
    with col1:
        st.metric("Rata-rata ISPU Hari Ini", f"{avg_ispu:.1f}")
    with col2:
        st.metric("Polutan Paling Dominan", dominant_pollutant)
    with col3:
        st.metric("Stasiun SPKU Aktif", len(df_latest))
        
    st.divider()
    
    # 2. Visualisasi Rata-rata ISPU Keseluruhan per Stasiun
    st.subheader("Rata-rata ISPU Historis per Stasiun (Keseluruhan)")
    
    # Menghitung rata-rata ISPU setiap stasiun
    avg_per_station = df.groupby('nama_stasiun')['nilai_max_ispu'].mean().reset_index()
    avg_per_station = avg_per_station.sort_values(by='nilai_max_ispu', ascending=False)
    
    # Membuat Bar Chart Interaktif menggunakan Plotly
    fig = px.bar(
        avg_per_station, 
        x='nama_stasiun', 
        y='nilai_max_ispu',
        labels={'nama_stasiun': 'Stasiun Pemantau', 'nilai_max_ispu': 'Rata-rata Nilai ISPU'},
        color='nilai_max_ispu',
        color_continuous_scale='RdYlGn_r', # Gradasi Hijau (Baik) ke Merah (Buruk)
        text_auto='.1f' # Menampilkan angka di atas bar
    )
    
    fig.update_layout(xaxis_title="Stasiun", yaxis_title="Nilai ISPU")
    st.plotly_chart(fig, use_container_width=True)