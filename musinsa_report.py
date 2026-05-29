from __future__ import annotations
import io
import streamlit as st
import pandas as pd
from rd_loader import load_rd, COL_DATE
from tabs import mutandard, active_customer

st.set_page_config(
    page_title="무신사 리포트 대시보드",
    layout="wide",
    page_icon="📦",
)

with st.sidebar:
    st.markdown("## 📊 무신사 리포트")
    uploaded = st.file_uploader(
        "RD CSV 업로드",
        type=['csv'],
        help="musinsa_Total_*.csv 파일을 업로드하세요",
    )

    if uploaded is None:
        st.info("RD CSV를 업로드하면 대시보드가 표시됩니다.")
        st.stop()

    @st.cache_data(show_spinner="데이터 로딩 중...")
    def _load(file_bytes: bytes, name: str) -> pd.DataFrame:
        return load_rd(io.BytesIO(file_bytes))

    df = _load(uploaded.read(), uploaded.name)
    st.success(f"✅ {uploaded.name}")

    date_min = df[COL_DATE].min().date()
    date_max = df[COL_DATE].max().date()
    date_range = st.date_input(
        "날짜 범위",
        value=(date_max, date_max),
        min_value=date_min,
        max_value=date_max,
    )
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start, end = date_range
    else:
        start = end = date_max

    all_media = sorted(df['매체_표기'].dropna().unique().tolist())
    sel_media = st.multiselect("매체", all_media, default=all_media)

mask = (df[COL_DATE].dt.date >= start) & (df[COL_DATE].dt.date <= end)
if sel_media:
    mask &= df['매체_표기'].isin(sel_media)
fdf = df[mask]

if fdf.empty:
    st.warning("필터 조건에 맞는 데이터가 없습니다.")
    st.stop()

st.title("📊 무신사 퍼포먼스 대시보드")

tab_active, tab_churn, tab_youth, tab_mt, tab_beauty, tab_foot = st.tabs([
    "🎯 활성고객",
    "↩️ 이탈고객",
    "👟 20대유입",
    "📦 무탠유입",
    "💄 뷰티",
    "👠 풋웨어",
])

with tab_active:
    active_customer.render(fdf, df)

with tab_mt:
    mutandard.render(fdf, df)

for tab, name in [
    (tab_churn,  "이탈고객"),
    (tab_youth,  "20대유입"),
    (tab_beauty, "뷰티"),
    (tab_foot,   "풋웨어"),
]:
    with tab:
        st.info(f"'{name}' 탭은 추후 구현 예정입니다.")
