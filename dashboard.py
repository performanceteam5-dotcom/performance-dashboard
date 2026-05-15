import streamlit as st
from data_loader import load_merged, BRAND_KW_CAMPAIGN
from tabs import summary, trend, creative, report, af_verify

st.set_page_config(page_title="퍼포먼스 마케팅 대시보드", layout="wide")
st.title("📊 퍼포먼스 마케팅 대시보드")


@st.cache_data(ttl=0)
def get_data():
    return load_merged()


df = get_data()

if df.empty:
    st.error("데이터 없음 — data/raw/channel/ 에 CSV를 추가하세요.")
    st.stop()

# ── 공통 사이드바 필터 ────────────────────────────────────────────
with st.sidebar:
    st.header("필터")

    date_min = df["일"].min().date()
    date_max = df["일"].max().date()
    date_range = st.date_input(
        "날짜 범위", value=(date_min, date_max),
        min_value=date_min, max_value=date_max,
    )
    start, end = (date_range[0], date_range[1]) if len(date_range) == 2 else (date_min, date_max)

    all_channels = sorted(df["채널"].dropna().unique().tolist())
    sel_ch = st.multiselect("채널", all_channels, default=all_channels)

    exclude_brand_kw = st.toggle("브랜드KW 제외 (NVR_CMP_01)", value=False)
    exclude_naver = st.toggle("자체매체(네이버) 제외", value=False)

# ── 필터 적용 ─────────────────────────────────────────────────────
mask = (df["일"].dt.date >= start) & (df["일"].dt.date <= end)
if sel_ch:
    mask &= df["채널"].isin(sel_ch)
if exclude_brand_kw:
    mask &= df["캠페인"] != BRAND_KW_CAMPAIGN
if exclude_naver:
    mask &= df["채널"] != "네이버"

fdf = df[mask]

if fdf.empty:
    st.warning("필터 조건에 맞는 데이터가 없습니다.")
    st.stop()

# ── 탭 라우팅 ─────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 오늘 요약", "📈 트렌드", "🎨 소재 분석", "📋 보고서", "🔗 AF 검증"
])

with tab1:
    summary.render(fdf)
with tab2:
    trend.render(fdf)
with tab3:
    creative.render(fdf)
with tab4:
    report.render(fdf)
with tab5:
    af_verify.render(fdf)
