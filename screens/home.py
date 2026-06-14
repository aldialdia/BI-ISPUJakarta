import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# PLOTLY THEME DEFAULTS
# ==========================================
PLOTLY_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='Inter, sans-serif', color='#94A3B8', size=12),
    margin=dict(l=0, r=0, t=40, b=0),
    xaxis=dict(gridcolor='rgba(108,99,255,0.06)', zerolinecolor='rgba(108,99,255,0.08)'),
    yaxis=dict(gridcolor='rgba(108,99,255,0.06)', zerolinecolor='rgba(108,99,255,0.08)'),
    coloraxis_colorbar=dict(
        tickfont=dict(color='#94A3B8'),
        title_font=dict(color='#94A3B8')
    ),
)

# Premium color palette
POLLUTANT_COLORS = ['#6C63FF', '#A78BFA', '#34D399', '#F59E0B', '#F472B6', '#38BDF8']

KATEGORI_COLORS = {
    'BAIK': '#10B981',
    'SEDANG': '#3B82F6',
    'TIDAK SEHAT': '#F59E0B',
    'SANGAT TIDAK SEHAT': '#EF4444',
    'BERBAHAYA': '#7F1D1D',
    'TIDAK ADA DATA': '#475569'
}


def render(df):
    st.title("Ringkasan Kualitas Udara")
    
    # Mencari tanggal paling baru
    latest_date = df['tanggal'].max()
    df_latest = df[df['tanggal'] == latest_date]
    tanggal_str = latest_date.strftime('%d %B %Y')
    
    # ==========================================
    # 1. KPI CARDS
    # ==========================================
    st.markdown(f"""
    <div style="font-size: 0.85rem; color: #64748B; margin-bottom: 20px; font-weight: 400;">
        Data terbaru: <span style="color: #A5B4FC; font-weight: 500;">{tanggal_str}</span>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    avg_ispu = df_latest['nilai_max_ispu'].mean() if not df_latest.empty else 0
    dom_pol = df_latest['polutan_kritis'].mode()[0] if not df_latest.empty else "-"
    total_stasiun = df_latest['nama_stasiun'].nunique() if not df_latest.empty else 0
    stasiun_kritis = len(df_latest[df_latest['nilai_max_ispu'] > 100]) if not df_latest.empty else 0

    # Determine ISPU category color
    if avg_ispu <= 50:
        ispu_color = "#10B981"
    elif avg_ispu <= 100:
        ispu_color = "#3B82F6"
    elif avg_ispu <= 199:
        ispu_color = "#F59E0B"
    else:
        ispu_color = "#EF4444"
    
    with col1:
        st.markdown(f"""
        <div class="kpi-stat">
            <div class="kpi-value" style="background: linear-gradient(135deg, {ispu_color}, {ispu_color}aa); 
                -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
                {avg_ispu:.1f}
            </div>
            <div class="kpi-label">Rata-rata ISPU Hari Ini</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="kpi-stat">
            <div class="kpi-value">{dom_pol}</div>
            <div class="kpi-label">Polutan Dominan</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="kpi-stat">
            <div class="kpi-value">{total_stasiun}</div>
            <div class="kpi-label">Stasiun Aktif</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        kritis_color = "#EF4444" if stasiun_kritis > 0 else "#10B981"
        st.markdown(f"""
        <div class="kpi-stat">
            <div class="kpi-value" style="background: linear-gradient(135deg, {kritis_color}, {kritis_color}aa); 
                -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
                {stasiun_kritis}
            </div>
            <div class="kpi-label">Wilayah Kritis</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ==========================================
    # 2. STATUS PERINGATAN TERKINI
    # ==========================================
    df_kritis = df_latest[df_latest['nilai_max_ispu'] > 100].sort_values(by='nilai_max_ispu', ascending=False)
    
    if not df_kritis.empty:
        st.markdown(f"""
        <div class="status-danger">
            <p>PERHATIAN — Terdeteksi <strong>{len(df_kritis)} wilayah</strong> dengan kualitas udara 
            <strong>Tidak Sehat</strong> atau lebih buruk pada {tanggal_str}.</p>
        </div>
        """, unsafe_allow_html=True)
        
        for idx, row in df_kritis.iterrows():
            kat_color = KATEGORI_COLORS.get(row['nama_kategori'], '#94A3B8')
            st.markdown(f"""
            <div class="status-warning">
                <p><strong>{row['nama_stasiun']}</strong> &nbsp;|&nbsp; 
                ISPU: <strong>{row['nilai_max_ispu']}</strong> 
                (<span style="color: {kat_color};">{row['nama_kategori']}</span>) &nbsp;|&nbsp; 
                Polutan: <strong>{row['polutan_kritis']}</strong></p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="status-safe">
            <p>Seluruh stasiun pemantau melaporkan kualitas udara dalam batas <strong>aman</strong> 
            (Kategori Baik / Sedang). Tidak ada peringatan yang perlu ditindaklanjuti.</p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ==========================================
    # 3. GRAFIK POLUTAN (TERKINI)
    # ==========================================
    st.subheader("Konsentrasi Polutan per Stasiun")
    st.caption("Rincian parameter polutan di seluruh stasiun pemantauan pada hari ini")
    
    if not df_latest.empty:
        df_pollutants = df_latest[['nama_stasiun', 'pm10', 'pm25', 'so2', 'co', 'o3', 'no2']]
        df_melted = df_pollutants.melt(id_vars='nama_stasiun', var_name='Jenis Polutan', value_name='Konsentrasi')
        df_melted['Jenis Polutan'] = df_melted['Jenis Polutan'].str.upper()
        
        fig_bar = px.bar(
            df_melted, 
            y='nama_stasiun', 
            x='Konsentrasi', 
            color='Jenis Polutan', 
            orientation='h',
            barmode='group',
            color_discrete_sequence=POLLUTANT_COLORS
        )
        fig_bar.update_layout(
            **PLOTLY_LAYOUT,
            yaxis_title="",
            xaxis_title="Konsentrasi (µg/m³)",
            height=350,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor='rgba(0,0,0,0)',
                font=dict(color='#94A3B8', size=11)
            )
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # ==========================================
    # 4. PETA SPASIAL
    # ==========================================
    st.subheader("Pemetaan Spasial Polusi Udara")
    st.caption("Visualisasi geografis stasiun SPKU di DKI Jakarta — gunakan filter untuk menelusuri data historis")
    
    # Filter Tanggal
    col_thn, col_bln, col_tgl = st.columns(3)
    
    with col_thn:
        daftar_tahun = sorted(df['tanggal'].dt.year.unique(), reverse=True)
        pilih_tahun = st.selectbox("Tahun", options=daftar_tahun)
    df_tahun = df[df['tanggal'].dt.year == pilih_tahun]
    
    with col_bln:
        daftar_bulan = sorted(df_tahun['tanggal'].dt.month.unique(), reverse=True)
        nama_bulan = {1:'Januari', 2:'Februari', 3:'Maret', 4:'April', 5:'Mei', 6:'Juni', 
                      7:'Juli', 8:'Agustus', 9:'September', 10:'Oktober', 11:'November', 12:'Desember'}
        pilih_bulan = st.selectbox("Bulan", options=daftar_bulan, format_func=lambda x: nama_bulan[x])
    df_bulan = df_tahun[df_tahun['tanggal'].dt.month == pilih_bulan]
    
    with col_tgl:
        daftar_hari = sorted(df_bulan['tanggal'].dt.day.unique(), reverse=True)
        pilih_hari = st.selectbox("Tanggal", options=daftar_hari)
        
    tanggal_gabungan = pd.to_datetime(f"{pilih_tahun}-{pilih_bulan:02d}-{pilih_hari:02d}")
    df_map = df[df['tanggal'] == tanggal_gabungan]
    
    col_peta, col_info = st.columns([2, 1])
    
    with col_peta:
        # Dark-themed map tiles
        m = folium.Map(
            location=[-6.2088, 106.8456], 
            zoom_start=11, 
            tiles="CartoDB dark_matter"
        )
        df_stasiun = df[['nama_stasiun', 'wilayah', 'latitude', 'longitude']].drop_duplicates()
        
        folium_colors = {
            'BAIK': 'green',
            'SEDANG': 'blue',
            'TIDAK SEHAT': 'orange',
            'SANGAT TIDAK SEHAT': 'red',
            'BERBAHAYA': 'darkred'
        }
        
        for idx, stasiun_row in df_stasiun.iterrows():
            nama = stasiun_row['nama_stasiun']
            data_hari_ini = df_map[df_map['nama_stasiun'] == nama]
            
            if not data_hari_ini.empty:
                row = data_hari_ini.iloc[0]
                kategori = row['nama_kategori']
                ispu_val = row['nilai_max_ispu']
                polutan = row['polutan_kritis']
                color = folium_colors.get(kategori, 'lightgray')
            else:
                kategori = 'TIDAK ADA DATA'
                ispu_val = '-'
                polutan = '-'
                color = 'lightgray'
                
            popup_html = f"""
            <div style='font-family: Inter, Arial, sans-serif; width: 200px; padding: 4px;'>
                <h4 style='margin: 0 0 8px 0; color: #1e293b; font-size: 14px;'>{nama}</h4>
                <table style='font-size: 12px; color: #334155; width: 100%;'>
                    <tr><td style='padding: 3px 0; color: #64748b;'>Wilayah</td>
                        <td style='padding: 3px 0; text-align: right; font-weight: 600;'>{stasiun_row['wilayah']}</td></tr>
                    <tr><td style='padding: 3px 0; color: #64748b;'>ISPU</td>
                        <td style='padding: 3px 0; text-align: right; font-weight: 600;'>{ispu_val}</td></tr>
                    <tr><td style='padding: 3px 0; color: #64748b;'>Status</td>
                        <td style='padding: 3px 0; text-align: right; font-weight: 600;'>{kategori}</td></tr>
                    <tr><td style='padding: 3px 0; color: #64748b;'>Polutan</td>
                        <td style='padding: 3px 0; text-align: right; font-weight: 600;'>{polutan}</td></tr>
                </table>
            </div>
            """
            folium.Marker(
                location=[stasiun_row['latitude'], stasiun_row['longitude']], 
                popup=folium.Popup(popup_html, max_width=250), 
                tooltip=nama, 
                icon=folium.Icon(color=color, icon='cloud', prefix='fa')
            ).add_to(m)
            
        st_folium(m, width=700, height=480, returned_objects=[])

    with col_info:
        st.markdown("**Detail Stasiun**")
        if not df_map.empty:
            df_ringkas = df_map[['nama_stasiun', 'wilayah', 'nilai_max_ispu', 'nama_kategori', 'polutan_kritis']].copy()
            df_ringkas.columns = ['Stasiun', 'Wilayah', 'ISPU', 'Kategori', 'Polutan Kritis']
            st.dataframe(df_ringkas, use_container_width=True, hide_index=True)
        else:
            st.info("Tidak ada pencatatan data polusi pada tanggal ini.")
        
        # Clean legend without emojis
        st.markdown("""
        <div class="legend-box">
            <div style="font-size: 0.8rem; color: #94A3B8; font-weight: 600; text-transform: uppercase; 
                letter-spacing: 0.8px; margin-bottom: 10px;">Legenda Status</div>
            <div class="legend-item"><span class="legend-dot" style="background: #10B981;"></span> Baik</div>
            <div class="legend-item"><span class="legend-dot" style="background: #3B82F6;"></span> Sedang</div>
            <div class="legend-item"><span class="legend-dot" style="background: #F59E0B;"></span> Tidak Sehat</div>
            <div class="legend-item"><span class="legend-dot" style="background: #EF4444;"></span> Sangat Tidak Sehat</div>
            <div class="legend-item"><span class="legend-dot" style="background: #7F1D1D;"></span> Berbahaya</div>
            <div class="legend-item"><span class="legend-dot" style="background: #475569;"></span> Tidak Ada Data</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ==========================================
    # 5. RATA-RATA ISPU HISTORIS
    # ==========================================
    st.subheader("Rata-rata ISPU Historis per Stasiun")
    st.caption("Perbandingan keseluruhan rata-rata indeks polusi di setiap stasiun pemantauan")
    
    avg_per_station = df.groupby('nama_stasiun')['nilai_max_ispu'].mean().reset_index()
    avg_per_station = avg_per_station.sort_values(by='nilai_max_ispu', ascending=False)
    
    # Custom color scale matching our theme
    fig_avg = px.bar(
        avg_per_station, 
        x='nama_stasiun', 
        y='nilai_max_ispu',
        labels={'nama_stasiun': 'Stasiun Pemantau', 'nilai_max_ispu': 'Rata-rata ISPU'},
        color='nilai_max_ispu',
        color_continuous_scale=[
            [0, '#10B981'],     # green for low
            [0.35, '#3B82F6'],  # blue for medium-low
            [0.55, '#F59E0B'],  # amber for medium
            [0.75, '#EF4444'],  # red for high
            [1, '#7F1D1D']      # dark-red for very high
        ],
        text_auto='.1f'
    )
    fig_avg.update_traces(
        textfont=dict(color='#E2E8F0', size=13, family='Inter'),
        textposition='outside'
    )
    fig_avg.update_layout(
        **PLOTLY_LAYOUT,
        xaxis_title="",
        yaxis_title="Nilai ISPU",
        height=400,
        coloraxis_showscale=False
    )
    st.plotly_chart(fig_avg, use_container_width=True)

    st.divider()

    # ==========================================
    # 6. RIWAYAT HARI KRITIS (30 HARI TERAKHIR)
    # ==========================================
    st.subheader("Riwayat Hari Kritis")
    st.caption("Stasiun yang melewati ambang batas aman (ISPU > 100) dalam 30 hari terakhir")
    
    date_30_days_ago = latest_date - pd.Timedelta(days=30)
    df_history = df[(df['tanggal'] >= date_30_days_ago) & (df['nilai_max_ispu'] > 100)]
    
    if not df_history.empty:
        df_history_show = df_history[['tanggal', 'nama_stasiun', 'wilayah', 'nama_kategori', 'nilai_max_ispu', 'polutan_kritis']].copy()
        df_history_show = df_history_show.sort_values(by=['tanggal', 'nilai_max_ispu'], ascending=[False, False])
        df_history_show['tanggal'] = df_history_show['tanggal'].dt.strftime('%d %B %Y')
        df_history_show.columns = ['Tanggal', 'Stasiun', 'Wilayah', 'Kategori', 'ISPU', 'Polutan Kritis']
        
        st.dataframe(df_history_show, use_container_width=True, hide_index=True)
    else:
        st.markdown("""
        <div class="status-safe">
            <p>Tidak ada riwayat peringatan dalam 30 hari terakhir. Kualitas udara cenderung stabil dan aman.</p>
        </div>
        """, unsafe_allow_html=True)