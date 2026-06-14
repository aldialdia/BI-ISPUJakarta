import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
PLOTLY_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='Inter, sans-serif', color='#94A3B8', size=12),
    margin=dict(l=0, r=0, t=40, b=0),
    xaxis=dict(gridcolor='rgba(108,99,255,0.06)', zerolinecolor='rgba(108,99,255,0.08)'),
    yaxis=dict(gridcolor='rgba(108,99,255,0.06)', zerolinecolor='rgba(108,99,255,0.08)'),
)
LINE_COLORS = ['#6C63FF', '#34D399', '#F59E0B', '#F472B6', '#38BDF8', '#A78BFA']
def render(df):
    st.title("Analisis Tren Historis")
    st.caption("Evaluasi pergerakan nilai ISPU dan konsentrasi polutan spesifik untuk mendukung pengambilan keputusan")
    st.markdown("""
    <div style="margin-bottom: 4px;">
        <span style="font-size: 0.8rem; color: #64748B; text-transform: uppercase;
            letter-spacing: 0.8px; font-weight: 600;">Filter Analisis</span>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        daftar_stasiun = df['nama_stasiun'].unique()
        pilihan_stasiun = st.multiselect(
            "Stasiun Pemantau",
            options=daftar_stasiun,
            default=[daftar_stasiun[0]]
        )
    with col2:
        daftar_tahun = sorted(df['tahun'].unique(), reverse=True)
        pilihan_tahun = st.selectbox("Tahun", options=daftar_tahun)
    with col3:
        bulan_tersedia = sorted(df[df['tahun'] == pilihan_tahun]['tanggal'].dt.month.unique())
        nama_bulan = {1:'Januari', 2:'Februari', 3:'Maret', 4:'April', 5:'Mei', 6:'Juni',
                      7:'Juli', 8:'Agustus', 9:'September', 10:'Oktober', 11:'November', 12:'Desember'}
        opsi_bulan = ["Semua Bulan"] + [nama_bulan[b] for b in bulan_tersedia]
        pilihan_bulan = st.selectbox("Bulan (Opsional)", options=opsi_bulan)
    if not pilihan_stasiun:
        st.markdown("""
        <div class="status-warning">
            <p>Silakan pilih minimal satu stasiun pemantau untuk menampilkan grafik.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    if pilihan_bulan != "Semua Bulan":
        inv_nama_bulan = {v: k for k, v in nama_bulan.items()}
        bln_angka = inv_nama_bulan[pilihan_bulan]
        df_filtered = df[(df['nama_stasiun'].isin(pilihan_stasiun)) & (df['tahun'] == pilihan_tahun) & (df['tanggal'].dt.month == bln_angka)].copy()
        periode_teks = f"Bulan {pilihan_bulan} {pilihan_tahun}"
    else:
        df_filtered = df[(df['nama_stasiun'].isin(pilihan_stasiun)) & (df['tahun'] == pilihan_tahun)].copy()
        periode_teks = f"Tahun {pilihan_tahun}"
    st.divider()
    st.subheader(f"Pergerakan Nilai ISPU — {periode_teks}")
    if df_filtered.empty:
        st.info("Data tidak tersedia untuk kombinasi filter yang dipilih.")
        return
    df_filtered = df_filtered.sort_values(['nama_stasiun', 'tanggal']).reset_index(drop=True)
    fig_ispu = px.line(
        df_filtered,
        x='tanggal',
        y='nilai_max_ispu',
        color='nama_stasiun',
        labels={'tanggal': 'Tanggal', 'nilai_max_ispu': 'Nilai ISPU Max', 'nama_stasiun': 'Stasiun'},
        color_discrete_sequence=LINE_COLORS,
        markers=False
    )
    fig_ispu.add_hline(
        y=100,
        line_dash="dot",
        line_color="rgba(239, 68, 68, 0.5)",
        annotation_text="Ambang Batas Tidak Sehat (> 100)",
        annotation_position="top right",
        annotation_font=dict(color='#EF4444', size=11)
    )
    fig_ispu.update_layout(
        **PLOTLY_LAYOUT,
        xaxis_title="",
        yaxis_title="Indeks Standar Pencemar Udara",
        height=400,
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
    fig_ispu.update_traces(line=dict(width=2.5))
    st.plotly_chart(fig_ispu, use_container_width=True)
    curr_avg = df_filtered['nilai_max_ispu'].mean()
    if pilihan_bulan != "Semua Bulan":
        prev_m = bln_angka - 1 if bln_angka > 1 else 12
        prev_y = pilihan_tahun if bln_angka > 1 else pilihan_tahun - 1
        df_prev = df[(df['nama_stasiun'].isin(pilihan_stasiun)) & (df['tahun'] == prev_y) & (df['tanggal'].dt.month == prev_m)]
    else:
        df_prev = df[(df['nama_stasiun'].isin(pilihan_stasiun)) & (df['tahun'] == pilihan_tahun - 1)]
    if not df_prev.empty:
        prev_avg = df_prev['nilai_max_ispu'].mean()
        pct_change = ((curr_avg - prev_avg) / prev_avg) * 100
        if pct_change >= 0:
            status_tren = "naik"
            trend_icon = "&#9650;"
            trend_color = "#EF4444"
        else:
            status_tren = "turun"
            trend_icon = "&#9660;"
            trend_color = "#10B981"
        isi_card_1 = f'Rata-rata ISPU {periode_teks} <span style="color:{trend_color};">{trend_icon} {status_tren} {abs(pct_change):.1f}%</span> dibanding periode sebelumnya.'
    else:
        isi_card_1 = f"Rata-rata ISPU {periode_teks} adalah <strong>{curr_avg:.1f}</strong>. Data periode sebelumnya tidak tersedia."
    hari_melampaui = df_filtered[df_filtered['nilai_max_ispu'] > 100]['tanggal'].dt.date.nunique()
    idx_max = df_filtered['nilai_max_ispu'].idxmax()
    val_max = df_filtered.loc[idx_max, 'nilai_max_ispu']
    date_max = df_filtered.loc[idx_max, 'tanggal'].strftime('%d %b %Y')
    sta_max = df_filtered.loc[idx_max, 'nama_stasiun']
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="insight-card">
            <h4>Tren Keseluruhan</h4>
            <p>{isi_card_1}</p>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        danger_color = "#EF4444" if hari_melampaui > 0 else "#10B981"
        st.markdown(f"""
        <div class="premium-card" style="border-left: 4px solid {danger_color};">
            <h4 style="color: {danger_color};">Hari Melampaui Batas</h4>
            <p>Terdeteksi <strong>{hari_melampaui} hari</strong> dengan nilai ISPU > 100 (Tidak Sehat)
            pada periode dan stasiun terpilih.</p>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="premium-card" style="border-left: 4px solid #F59E0B;">
            <h4 style="color: #FCD34D;">Puncak Tertinggi</h4>
            <p>Terjadi pada <strong>{date_max}</strong> sebesar <strong>{val_max}</strong>
            di stasiun <strong>{sta_max}</strong>.</p>
        </div>
        """, unsafe_allow_html=True)
    st.divider()
    st.subheader("Analisis Detail Parameter Polutan")
    st.caption("Pilih parameter spesifik untuk melihat tren konsentrasinya secara detail")
    polutan_pilihan = st.selectbox(
        "Parameter Polutan",
        ['pm10', 'pm25', 'so2', 'co', 'o3', 'no2'],
        format_func=lambda x: x.upper()
    )
    fig_polutan = px.line(
        df_filtered,
        x='tanggal',
        y=polutan_pilihan,
        color='nama_stasiun',
        labels={'tanggal': 'Waktu', polutan_pilihan: f'Konsentrasi {polutan_pilihan.upper()} (µg/m³)'},
        color_discrete_sequence=LINE_COLORS
    )
    fig_polutan.update_layout(
        **PLOTLY_LAYOUT,
        xaxis_title="",
        yaxis_title=f"Konsentrasi {polutan_pilihan.upper()} (µg/m³)",
        height=380,
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
    fig_polutan.update_traces(line=dict(width=2.5))
    st.plotly_chart(fig_polutan, use_container_width=True)
    df_pol_grouped = df_filtered.groupby('tanggal')[polutan_pilihan].mean().reset_index().sort_values('tanggal')
    if len(df_pol_grouped) > 1:
        val_awal = df_pol_grouped.iloc[0][polutan_pilihan]
        val_akhir = df_pol_grouped.iloc[-1][polutan_pilihan]
        tgl_awal = df_pol_grouped.iloc[0]['tanggal'].strftime('%d %b')
        tgl_akhir = df_pol_grouped.iloc[-1]['tanggal'].strftime('%d %b')
        pct_change_pol = ((val_akhir - val_awal) / val_awal * 100) if val_awal > 0 else 0
        if pct_change_pol > 0:
            status_pol = "meningkat"
            pol_icon = "&#9650;"
            pol_color = "#EF4444"
        else:
            status_pol = "menurun"
            pol_icon = "&#9660;"
            pol_color = "#10B981"
        isi_card_pol_1 = f'Konsentrasi {polutan_pilihan.upper()} <span style="color:{pol_color};">{pol_icon} {status_pol} {abs(pct_change_pol):.1f}%</span> (dari {val_awal:.1f} pada {tgl_awal} menjadi {val_akhir:.1f} pada {tgl_akhir}).'
    else:
        isi_card_pol_1 = "Data tidak cukup untuk menghitung tren perubahan awal hingga akhir periode."
    konteks_dict = {
        "PM10": "Dominan dari debu jalanan, aktivitas konstruksi fisik, dan partikel kasar.",
        "PM25": "Partikel halus berbahaya, bersumber kuat dari emisi gas buang kendaraan dan proses pembakaran.",
        "SO2": "Berasal dari industri manufaktur atau pembakaran bahan bakar fosil tinggi belerang.",
        "CO": "Hasil emisi kendaraan bermotor akibat pembakaran tidak sempurna, beracun di ruang terbatas.",
        "O3": "Polutan sekunder yang terbentuk akibat reaksi kimia sinar matahari (UV) dengan gas polutan lain.",
        "NO2": "Sangat identik dengan kepadatan volume kendaraan bermotor dan aktivitas pembangkit listrik."
    }
    isi_card_pol_2 = konteks_dict.get(polutan_pilihan.upper(), "")
    cp1, cp2 = st.columns(2)
    with cp1:
        st.markdown(f"""
        <div class="insight-card">
            <h4>Tren Perubahan Polutan</h4>
            <p>{isi_card_pol_1}</p>
        </div>
        """, unsafe_allow_html=True)
    with cp2:
        st.markdown(f"""
        <div class="premium-card" style="border-left: 4px solid #6C63FF;">
            <h4>Konteks Polutan</h4>
            <p>{isi_card_pol_2}</p>
        </div>
        """, unsafe_allow_html=True)
    st.divider()
    st.subheader("Dampak Aktivitas Harian")
    st.caption("Perbandingan rata-rata ISPU berdasarkan tipe mobilitas harian pada periode terpilih")
    def tentukan_tipe_hari(row):
        if row['is_holiday'] == 1 or row['is_holiday'] == True:
            return 'Libur Nasional'
        elif row['is_weekend'] == 1 or row['is_weekend'] == True:
            return 'Akhir Pekan'
        else:
            return 'Hari Kerja'
    df_filtered['Tipe Hari'] = df_filtered.apply(tentukan_tipe_hari, axis=1)
    df_aktivitas = df_filtered.groupby('Tipe Hari', observed=False)['nilai_max_ispu'].mean().reset_index()
    urutan_hari = ['Hari Kerja', 'Akhir Pekan', 'Libur Nasional']
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
                'Hari Kerja': '#6C63FF',
                'Akhir Pekan': '#34D399',
                'Libur Nasional': '#F59E0B'
            },
            text_auto='.1f',
            labels={'nilai_max_ispu': 'Rata-rata ISPU'}
        )
        fig_bar.update_traces(
            textfont=dict(color='#E2E8F0', size=14, family='Inter'),
            textposition='outside',
            marker_line_width=0
        )
        fig_bar.update_layout(
            **PLOTLY_LAYOUT,
            showlegend=False,
            xaxis_title="",
            yaxis_title="Rata-rata ISPU",
            height=380
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    with col_desc:
        if not df_aktivitas.empty and not df_aktivitas['nilai_max_ispu'].isna().all():
            row_tertinggi = df_aktivitas.loc[df_aktivitas['nilai_max_ispu'].idxmax()]
            tipe_tertinggi = row_tertinggi['Tipe Hari']
            nilai_tertinggi = row_tertinggi['nilai_max_ispu']
            teks_insight = f"Pada klaster stasiun ini, rata-rata indeks polusi tertinggi tercatat pada <strong>{tipe_tertinggi}</strong> dengan nilai <strong>{nilai_tertinggi:.1f}</strong>."
            if tipe_tertinggi == 'Hari Kerja':
                teks_detail = "Mengonfirmasi bahwa aktivitas komuter harian dan volume kendaraan bermotor adalah pemicu utama polusi di wilayah ini."
            elif tipe_tertinggi == 'Akhir Pekan':
                teks_detail = "Mengindikasikan lonjakan mobilitas lokal untuk rekreasi atau pergerakan massa wisata di sekitar wilayah stasiun terpilih."
            elif tipe_tertinggi == 'Libur Nasional':
                teks_detail = "Dipengaruhi oleh aktivitas libur panjang atau penumpukan volume kendaraan pada event nasional tertentu."
            else:
                teks_detail = ""
            st.markdown(f"""
            <div class="insight-card">
                <h4>Insight Otomatis</h4>
                <p>{teks_insight}</p>
                <p style="margin-top: 12px; color: #94A3B8; font-size: 0.85rem;">{teks_detail}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="premium-card">
                <p>Data tidak mencukupi untuk menghasilkan insight.</p>
            </div>
            """, unsafe_allow_html=True)
