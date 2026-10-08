import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import io

# Page layout configuration
st.set_page_config(
    page_title="냉동연육 & 명태 시세/환율 대시보드",
    page_icon="🐟",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern UI design
st.markdown("""
<style>
    /* Main Background & Font setup */
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
    }
    
    /* Hide top header padding */
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2rem;
    }
    
    /* Metric Card Styling */
    .kpi-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
    }
    .kpi-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #64748b;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .kpi-value {
        font-size: 1.65rem;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.5px;
    }
    .kpi-sub {
        font-size: 0.78rem;
        color: #10b981;
        margin-top: 4px;
        font-weight: 500;
    }
    .badge-api {
        background-color: #e0f2fe;
        color: #0369a1;
        font-size: 0.7rem;
        padding: 2px 8px;
        border-radius: 12px;
        font-weight: 600;
        display: inline-block;
    }

    /* Tab Styling Customization */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 2px solid #e2e8f0;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        white-space: pre-wrap;
        background-color: #f1f5f9;
        border-radius: 8px 8px 0px 0px;
        gap: 6px;
        padding: 0px 18px;
        font-weight: 600;
        color: #475569;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }

    /* Custom news card style */
    .news-card {
        border-left: 4px solid #2563eb;
        background-color: #f8fafc;
        padding: 14px 18px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .news-title {
        font-weight: 700;
        color: #1e293b;
        text-decoration: none;
        font-size: 1.05rem;
    }
    .news-title:hover {
        color: #2563eb;
    }
    .news-desc {
        font-size: 0.88rem;
        color: #64748b;
        margin-top: 4px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def fetch_koreaexim_usd_rate(authkey="kNAyoIJr8gKvf9nL9UaQLr2T97iRzuYP"):
    """
    한국수출입은행 환율 API를 통해 최신 영업일의 USD 매매기준율(deal_bas_r)을 가져옴.
    주말/공휴일로 인해 데이터가 없는 경우 최대 10일까지 역추적(Backtracking) 수행.
    """
    api_url = "https://www.koreaexim.go.kr/site/program/financial/exchangeJSON"
    today = datetime.now()
    
    # 최근 10일간 역추적
    for day_offset in range(10):
        target_date = today - timedelta(days=day_offset)
        formatted_date = target_date.strftime("%Y%m%d")
        
        params = {
            "authkey": authkey,
            "searchdate": formatted_date,
            "data": "AP01"
        }
        
        try:
            response = requests.get(api_url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    for item in data:
                        if item.get("cur_unit") == "USD":
                            # 매매기준율 추출 및 콤마 제거 후 float 변환
                            raw_rate = item.get("deal_bas_r", "0").replace(",", "")
                            rate = float(raw_rate)
                            if rate > 0:
                                return rate, formatted_date, "한국수출입은행 API (정상 연동)"
        except Exception:
            pass # API 통신 장애 시 다음 일자로 넘어가거나 Fallback 처리

    # API 응답 실패 시 사용되는 Fallback 기준 환율
    return 1385.50, today.strftime("%Y%m%d"), "Fallback 환율 (API 미응답)"


@st.cache_data
def generate_demo_data():
    """
    엑셀 파일이 업로드되지 않았을 때 시각화를 보여주기 위한 2024~2026 샘플 데이터 생성
    """
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", end="2026-09-01", freq="MS").strftime("%Y-%m").tolist()
    
    species_list = [
        ("갈치", "①연육(갈치,실꼬리돔)", ["베트남", "인도네시아", "중국", "인도"], ["Supplier A", "Supplier B", "Supplier C"], ["수입사 A", "수입사 B", "수입사 C"]),
        ("실꼬리돔", "①연육(갈치,실꼬리돔)", ["베트남", "태국", "인도네시아", "말레이시아"], ["Supplier D", "Supplier E", "Supplier F"], ["수입사 B", "수입사 D", "수입사 E"]),
        ("명태 Grade A", "②명태(Grade A)", ["미국", "러시아"], ["Trident Seafoods", "Ocean Beauty", "Gidrostroy"], ["수입사 A", "수입사 C", "수입사 F"])
    ]
    
    data_rows = []
    
    for dt in dates:
        for item, sheet_name, origins, suppliers, importers in species_list:
            # 원산지별로 샘플 행 생성
            for orig in origins:
                base_price = 2.8 if item == "갈치" else (2.4 if item == "실꼬리돔" else 3.8)
                usd_price = round(base_price + np.random.normal(0, 0.25), 2)
                volume_kg = int(np.random.uniform(15000, 85000))
                amount_usd = round(usd_price * volume_kg, 2)
                
                data_rows.append({
                    "시트명": sheet_name,
                    "기준연월": dt,
                    "어종": item,
                    "주요원산지": orig,
                    "해외공급사": np.random.choice(suppliers),
                    "국내수입사": np.random.choice(importers),
                    "외화단가": max(1.0, usd_price),
                    "수입물량": volume_kg,
                    "수입금액": amount_usd
                })
                
    return pd.DataFrame(data_rows)


def load_data_from_excel(uploaded_file):
    """
    업로드된 엑셀 파일에서 ①연육(갈치,실꼬리돔), ②명태(Grade A) 시트를 표준 칼럼으로 정제하여 로드
    """
    try:
        excel_file = pd.ExcelFile(uploaded_file)
        all_dfs = []
        
        # 통합 대상 칼럼 매핑 정의
        col_mapping = {
            '년월': '기준연월', '기준년월': '기준연월',
            '제품명': '어종', '품목': '어종',
            '수출국': '주요원산지', '원산지': '주요원산지',
            '수출사': '해외공급사', '공급사': '해외공급사',
            '수입사': '국내수입사',
            '단가(USD/kg)': '외화단가', '단가': '외화단가', '외화단가($/kg)': '외화단가',
            '수입량(kg)': '수입물량', '수입량': '수입물량', '물량(kg)': '수입물량',
            '수입액(USD)': '수입금액', '수입액': '수입금액', '금액(USD)': '수입금액'
        }
        
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(uploaded_file, sheet_name=sheet_name)
            df.rename(columns=col_mapping, inplace=True)
            df['시트명'] = sheet_name
            
            # 필드 수치 데이터 처리
            required_cols = ['기준연월', '어종', '주요원산지', '해외공급사', '국내수입사', '외화단가', '수입물량', '수입금액']
            
            # 수치형 필드 정제
            for col in ['외화단가', '수입물량', '수입금액']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
            # 존재하는 필수 칼럼이 있으면 결과에 추가
            if '어종' in df.columns and '외화단가' in df.columns:
                all_dfs.append(df)
                
        if all_dfs:
            combined_df = pd.concat(all_dfs, ignore_index=True)
            return combined_df
        else:
            st.error("엑셀 파일에서 필요한 형식의 데이터를 찾지 못했습니다. 데모 데이터로 대체합니다.")
            return generate_demo_data()
    except Exception as e:
        st.warning(f"파일 파싱 중 오류가 발생했습니다: {e}. 데모 데이터를 사용합니다.")
        return generate_demo_data()


# 1. 환율 가져오기
usd_rate, rate_date, rate_source = fetch_koreaexim_usd_rate()

# 2. 사이드바 구성 (Sidebar Control)
st.sidebar.image("https://img.icons8.com/color/96/fish.png", width=64)
st.sidebar.title("🎛️ 대시보드 필터")
st.sidebar.markdown("---")

# 엑셀 파일 업로드
uploaded_file = st.sidebar.file_uploader(
    "📂 트릿지 시세 엑셀 업로드 (.xlsx)",
    type=["xlsx"],
    help="'냉동연육 시세 트릿지 (~26년 9월).xlsx' 파일 업로드 가능"
)

if uploaded_file is not None:
    raw_df = load_data_from_excel(uploaded_file)
    st.sidebar.success("✅ 파일 업로드 완료!")
else:
    raw_df = generate_demo_data()
    st.sidebar.info("💡 기본 제공 [데모 데이터] 사용 중")

# 어종 선택 멀티 선택박스
available_species = raw_df['어종'].dropna().unique().tolist()
selected_species = st.sidebar.multiselect(
    "🐟 분석 어종 선택",
    options=available_species,
    default=available_species
)

# 기준연월 필터링 (범위 슬라이더)
if not raw_df.empty and '기준연월' in raw_df.columns:
    sorted_dates = sorted(raw_df['기준연월'].astype(str).unique().tolist())
    if len(sorted_dates) > 1:
        start_date, end_date = st.sidebar.select_slider(
            "📅 분석 기간 선택",
            options=sorted_dates,
            value=(sorted_dates[0], sorted_dates[-1])
        )
    else:
        start_date, end_date = sorted_dates[0], sorted_dates[0]
else:
    start_date, end_date = "2024-01", "2026-09"

# 데이터 필터링 적용
filtered_df = raw_df[
    (raw_df['어종'].isin(selected_species)) &
    (raw_df['기준연월'].astype(str) >= start_date) &
    (raw_df['기준연월'].astype(str) <= end_date)
].copy()

# 원화 단가 산출
filtered_df['원화단가'] = filtered_df['외화단가'] * usd_rate


# Header Title
st.title("🐟 냉동연육 및 명태 시세 / 환율 분석 대시보드")
st.caption("한국수출입은행 실시간 USD 환율 API 및 트릿지(Tridge) 수입 데이터 기반 BI 분석 시스템")

st.markdown("<br>", unsafe_allow_html=True)

# 핵심 KPI 계산
if not filtered_df.empty:
    total_volume_kg = filtered_df['수입물량'].sum()
    total_volume_ton = total_volume_kg / 1000.0
    total_amount_usd = filtered_df['수입금액'].sum()
    
    # 가중 평균 외화 단가
    avg_usd_price = total_amount_usd / total_volume_kg if total_volume_kg > 0 else filtered_df['외화단가'].mean()
    avg_krw_price = avg_usd_price * usd_rate
else:
    total_volume_ton = 0
    avg_usd_price = 0
    avg_krw_price = 0

# KPI 4열 카드 배치
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">💵 평균 외화단가</div>
        <div class="kpi-value">${avg_usd_price:,.2f} <span style="font-size:1rem; font-weight:normal;">/ kg</span></div>
        <div class="kpi-sub">선택 어종 전체 평균</div>
    </div>
    """, unsafe_allow_html=True)

with kpi2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">🇰🇷 원화 환산단가</div>
        <div class="kpi-value">₩{avg_krw_price:,.0f} <span style="font-size:1rem; font-weight:normal;">/ kg</span></div>
        <div class="kpi-sub">[평균 외화단가 × 실시간 환율]</div>
    </div>
    """, unsafe_allow_html=True)

with kpi3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">📦 총 수입량</div>
        <div class="kpi-value">{total_volume_ton:,.1f} <span style="font-size:1rem; font-weight:normal;">Ton</span></div>
        <div class="kpi-sub">{total_volume_kg:,.0f} kg</div>
    </div>
    """, unsafe_allow_html=True)

with kpi4:
    formatted_rate_date = datetime.strptime(rate_date, "%Y%m%d").strftime("%Y-%m-%d") if len(rate_date) == 8 else rate_date
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">💱 실시간 USD 환율</div>
        <div class="kpi-value">₩{usd_rate:,.2f}</div>
        <div class="kpi-sub">
            <span class="badge-api">{rate_source}</span>
            <span style="color:#94a3b8; font-size:0.7rem;">({formatted_rate_date})</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 [Tab 1] 시세 추이 & 환율 영향도",
    "🍩 [Tab 2] 원산지 공급 비중",
    "📊 [Tab 3] 수출입 네트워크 Top 5",
    "📰 [Tab 4] 핵심이슈 & 수급 인사이트",
    "📋 [Tab 5] RAW DATA 세부내역"
])


with tab1:
    st.subheader("📈 시세 추이 및 환율 영향도 시계열 분석")
    st.write("월별 어종별 외화단가($/kg)와 실시간 환율 반영 원화단가(원/kg) 추이를 비교 분석합니다.")
    
    if filtered_df.empty:
        st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
    else:
        # 월별, 어종별 집계
        ts_df = filtered_df.groupby(['기준연월', '어종']).agg({
            '수입금액': 'sum',
            '수입물량': 'sum',
            '외화단가': 'mean'
        }).reset_index()
        
        # 물량 가중평균 단가 재계산
        ts_df['가중외화단가'] = ts_df['수입금액'] / ts_df['수입물량']
        ts_df['가중외화단가'] = ts_df['가중외화단가'].fillna(ts_df['외화단가'])
        ts_df['가중원화단가'] = ts_df['가중외화단가'] * usd_rate
        
        col_t1_left, col_t1_right = st.columns(2)
        
        with col_t1_left:
            # 외화단가 추이 ($/kg)
            fig_usd = px.line(
                ts_df,
                x='기준연월',
                y='가중외화단가',
                color='어종',
                markers=True,
                title="<b>[USD] 어종별 외화단가 추이 ($/kg)</b>",
                labels={'가중외화단가': '외화단가 (USD/kg)', '기준연월': '년월'},
                template="plotly_white",
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_usd.update_traces(line=dict(width=2.5), marker=dict(size=7))
            fig_usd.update_layout(hovermode="x unified", legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig_usd, use_container_width=True)

        with col_t1_right:
            # 원화단가 추이 (원/kg)
            fig_krw = px.line(
                ts_df,
                x='기준연월',
                y='가중원화단가',
                color='어종',
                markers=True,
                title=f"<b>[KRW] 원화 환산단가 추이 (원/kg - 적용 환율: ₩{usd_rate:,.1f})</b>",
                labels={'가중원화단가': '원화단가 (원/kg)', '기준연월': '년월'},
                template="plotly_white",
                color_discrete_sequence=px.colors.qualitative.Dark2
            )
            fig_krw.update_traces(line=dict(width=2.5), marker=dict(size=7))
            fig_krw.update_layout(hovermode="x unified", legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig_krw, use_container_width=True)
            
        # 환율 변동 가상 시뮬레이션
        with st.expander("💡 **환율 변동 시뮬레이션 (Exchange Rate Sensitivity)**"):
            sim_rate = st.slider("테스트 환율 설정 (원/USD)", min_value=1100.0, max_value=1600.0, value=float(usd_rate), step=10.0)
            sim_avg_krw = avg_usd_price * sim_rate
            diff_krw = sim_avg_krw - avg_krw_price
            st.info(f"설정 환율 **₩{sim_rate:,.1f}** 적용 시, 평균 원화 단가는 **₩{sim_avg_krw:,.0f}/kg** 로 현재 대비 **{diff_krw:+,.0f}원/kg** 변동합니다.")


with tab2:
    st.subheader("🍩 원산지 공급 비중 도넛 분석")
    st.write("주요 수입 원산지(수출국)의 공급 비중을 물량(Ton) 또는 금액(USD) 기준으로 확인합니다.")
    
    if filtered_df.empty:
        st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
    else:
        # 기준 선택 라디오 버튼
        basis = st.radio(
            "비중 산출 기준 선택:",
            ["📦 수입물량 베이스 (Ton)", "💵 수입금액 베이스 (USD)"],
            horizontal=True
        )
        
        target_col = '수입물량' if "수입물량" in basis else '수입금액'
        
        # 어종별 도넛 차트 나열 또는 전체 도넛 차트
        col_pie1, col_pie2 = st.columns([1, 1])
        
        # 1. 전체 원산지 비중
        origin_summary = filtered_df.groupby('주요원산지')[target_col].sum().reset_index()
        if target_col == '수입물량':
            origin_summary['표시값'] = origin_summary['수입물량'] / 1000.0
            unit_label = "Ton"
        else:
            origin_summary['표시값'] = origin_summary['수입금액']
            unit_label = "USD"
            
        with col_pie1:
            fig_donut = px.pie(
                origin_summary,
                names='주요원산지',
                values='표시값',
                hole=0.45,
                title=f"<b>전체 원산지 공급 비중 ({unit_label})</b>",
                template="plotly_white",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_donut.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_donut, use_container_width=True)
            
        # 2. 어종별 원산지 비중 (Sunburst)
        with col_pie2:
            fig_sunburst = px.sunburst(
                filtered_df,
                path=['어종', '주요원산지'],
                values=target_col,
                title=f"<b>어종 ➔ 원산지 계층 구조 ({unit_label})</b>",
                color='어종',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig_sunburst, use_container_width=True)


with tab3:
    st.subheader("📊 주요 해외공급사 및 국내수입사 Top 5 점유율")
    st.write("해외 공급처(수출사)와 국내 수입사의 점유율 구조를 가로형 막대그래프로 분석합니다.")
    
    if filtered_df.empty:
        st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
    else:
        type_choice = st.radio(
            "분석 대상 선택:",
            ["🏢 해외공급사 (수출사) Top 5", "🏬 국내수입사 (수입사) Top 5"],
            horizontal=True
        )
        
        target_group_col = '해외공급사' if "해외공급사" in type_choice else '국내수입사'
        
        top_df = filtered_df.groupby(target_group_col).agg({
            '수입물량': 'sum',
            '수입금액': 'sum',
            '외화단가': 'mean'
        }).reset_index()
        
        top_df['수입물량(Ton)'] = top_df['수입물량'] / 1000.0
        top_df = top_df.sort_values(by='수입물량(Ton)', ascending=True).tail(5)
        
        # Plotly horizontal bar chart
        fig_bar = px.bar(
            top_df,
            x='수입물량(Ton)',
            y=target_group_col,
            orientation='h',
            text='수입물량(Ton)',
            title=f"<b>{target_group_col} 물량 기준 Top 5</b>",
            labels={'수입물량(Ton)': '수입량 (Ton)', target_group_col: target_group_col},
            color='수입물량(Ton)',
            color_continuous_scale='Blues',
            template="plotly_white"
        )
        
        # Detailed Hover Tooltip
        fig_bar.update_traces(
            texttemplate='%{text:,.1f} Ton',
            textposition='outside',
            hovertemplate="<b>%{y}</b><br>수입량: %{x:,.1f} Ton<br>"
        )
        
        st.plotly_chart(fig_bar, use_container_width=True)


with tab4:
    st.subheader("📰 실시간 핵심이슈 & 수급 인사이트")
    st.write("어획 쿼터, 물류 동향 및 어묵 원자재 관련 최신 뉴스 및 보고서 링크를 전달합니다.")
    
    col_n1, col_n2 = st.columns(2)
    
    with col_n1:
        st.markdown("### 🌊 어획 쿼터 & 원자재 이슈")
        
        st.markdown("""
        <div class="news-card">
            <a href="https://search.naver.com/search.naver?query=명태+어획쿼터+러시아+미국" target="_blank" class="news-title">
                📌 러시아/미국 명태 어획 쿼터 및 수급 동향 검색 ↗
            </a>
            <div class="news-desc">2025-2026 베링해 및 오호츠크해 명태 어획 쿼터 변동에 따른 국내 명태 Surimi 수입 단가 영향 파악</div>
        </div>
        
        <div class="news-card">
            <a href="https://search.naver.com/search.naver?query=연육+원자재+어묵+시세" target="_blank" class="news-title">
                📌 연육 원자재(갈치/실꼬리돔) 및 어묵 제조원가 뉴스 ↗
            </a>
            <div class="news-desc">동남아(베트남, 인도네시아) 실꼬리돔 연육 가공 공장 가동률 및 국내 어묵 제조사 원자재 수급 전망</div>
        </div>
        """, unsafe_allow_html=True)

    with col_n2:
        st.markdown("### ⚓ 해상 물류 & 수산물 리포트")
        
        st.markdown("""
        <div class="news-card">
            <a href="https://www.kamis.or.kr" target="_blank" class="news-title">
                📊 KAMIS 농수산물 유통정보 시스템 ↗
            </a>
            <div class="news-desc">국내 수산물 도소매 가격 및 수입 수산물 유통 동향 종합 데이터 베이스</div>
        </div>
        
        <div class="news-card">
            <a href="https://www.mof.go.kr" target="_blank" class="news-title">
                🏛️ 해양수산부 수산물 수급 동향 리포트 ↗
            </a>
            <div class="news-desc">원양어선 어획량 발표 및 수산물 수입 관세/원산지 단속 정책 발표자료</div>
        </div>
        """, unsafe_allow_html=True)


with tab5:
    st.subheader("📋 RAW DATA 세부내역")
    st.write("필터링된 상세 데이터 프레임입니다. 칼럼별 정렬 및 검색이 가능하며 CSV 파일로 다운로드할 수 있습니다.")
    
    if filtered_df.empty:
        st.warning("표시할 데이터가 없습니다.")
    else:
        # 데이터프레임 서식 정리
        display_df = filtered_df[['기준연월', '어종', '주요원산지', '해외공급사', '국내수입사', '외화단가', '원화단가', '수입물량', '수입금액']].copy()
        display_df.columns = ['기준연월', '어종', '주요원산지', '해외공급사', '국내수입사', '외화단가($/kg)', '원화단가(원/kg)', '수입물량(kg)', '수입금액(USD)']
        
        # Interactive DataFrame
        st.dataframe(
            display_df.style.format({
                '외화단가($/kg)': '${:,.2f}',
                '원화단가(원/kg)': '₩{:,.0f}',
                '수입물량(kg)': '{:,.0f}',
                '수입금액(USD)': '${:,.2f}'
            }),
            use_container_width=True,
            height=400
        )
        
        # CSV Download Button
        csv_buffer = io.StringIO()
        display_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        
        st.download_button(
            label="📥 Filtered RAW DATA CSV 다운로드",
            data=csv_buffer.getvalue(),
            file_name=f"frozen_fish_price_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

st.markdown("---")
st.caption("🐟 Seafood Raw Material BI Dashboard | Powered by Streamlit & Plotly | 한국수출입은행 Open API 연동")