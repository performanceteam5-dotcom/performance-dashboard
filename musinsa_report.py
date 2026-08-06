from __future__ import annotations
import io
import os
from datetime import timedelta
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from rd_loader import load_rd, COL_DATE


def _weekend_range(reference, weeks_back: int = 0):
    """reference 기준 가장 최근 금~일 범위 반환. weeks_back=1이면 그 전 주."""
    wd = reference.weekday()  # Mon=0, Sun=6
    days_to_last_sun = (wd + 1) % 7
    sun = reference - timedelta(days=days_to_last_sun + weeks_back * 7)
    fri = sun - timedelta(days=2)
    return fri, sun
from tabs import mutandard, active_customer, mubaedan, return_user, dau

load_dotenv()
_HAS_AUTO = bool(os.environ.get('DROPBOX_APP_KEY') or os.environ.get('RD_FOLDER_PATH'))

st.set_page_config(
    page_title="무신사 리포트 대시보드",
    layout="wide",
    page_icon="📦",
)

# ── 사이드바: 데이터 로딩 ──────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 무신사 리포트")

    # 자동 연동 버튼 (Dropbox API 또는 로컬 경로 설정 시)
    if _HAS_AUTO:
        if st.button("🔄 최신 RD 불러오기", use_container_width=True):
            with st.spinner("최신 파일 불러오는 중..."):
                try:
                    from drive_loader import load_latest_rd
                    df, name = load_latest_rd()
                    st.session_state['rd_df'] = df
                    st.session_state['rd_name'] = name
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        st.markdown("<div style='text-align:center;color:#aaa;margin:4px 0'>또는</div>", unsafe_allow_html=True)

    # 수동 파일 업로드 (항상 표시)
    uploaded = st.file_uploader(
        "RD CSV 업로드",
        type=['csv'],
        help="musinsa_Total_*.csv 파일을 업로드하세요",
    )
    if uploaded:
        @st.cache_data(show_spinner="데이터 로딩 중...")
        def _load(file_bytes: bytes, name: str) -> pd.DataFrame:
            return load_rd(io.BytesIO(file_bytes))

        df = _load(uploaded.read(), uploaded.name)
        st.session_state['rd_df'] = df
        st.session_state['rd_name'] = uploaded.name

    # 로드된 데이터 없으면 안내 후 대기
    if 'rd_df' not in st.session_state:
        if _HAS_AUTO:
            st.info("버튼을 눌러 최신 파일을 불러오거나 CSV를 직접 업로드하세요.")
        else:
            st.info(
                "RD CSV를 업로드하면 대시보드가 표시됩니다.\n\n"
                "자동 연동: `.env`에 `RD_FOLDER_PATH`를 추가하세요."
            )
        st.stop()

    df = st.session_state['rd_df']
    rd_name = st.session_state.get('rd_name', 'RD 데이터')
    st.success(f"✅ {rd_name}")

    # ── 날짜·매체 필터 ──
    date_min = df[COL_DATE].min().date()
    date_max = df[COL_DATE].max().date()

    # 기간 선택
    st.caption("기간 선택")
    p1, p2, p3 = st.columns(3)
    if p1.button("전일", use_container_width=True):
        st.session_state['date_preset'] = (date_max, date_max)
        st.session_state['show_date_input'] = False
    if p2.button("직전 주말", use_container_width=True):
        fri, sun = _weekend_range(date_max, weeks_back=0)
        fri = max(fri, date_min)
        sun = min(sun, date_max)
        st.session_state['date_preset'] = (fri, sun)
        st.session_state['show_date_input'] = False
    if p3.button("직접입력", use_container_width=True):
        st.session_state['show_date_input'] = True

    if st.session_state.get('show_date_input', False):
        preset = st.session_state.get('date_preset', (date_max, date_max))
        date_range = st.date_input(
            "날짜 범위",
            value=preset,
            min_value=date_min,
            max_value=date_max,
            key='date_range_input',
        )
        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            st.session_state['date_preset'] = date_range
    else:
        date_range = st.session_state.get('date_preset', (date_max, date_max))

    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start, end = date_range
    else:
        start = end = date_max

    all_media = sorted(df['매체_표기'].dropna().unique().tolist())
    sel_media = st.multiselect("매체", all_media, default=all_media)

# ── 필터 적용 ──────────────────────────────────────────────────────
mask = (df[COL_DATE].dt.date >= start) & (df[COL_DATE].dt.date <= end)
if sel_media:
    mask &= df['매체_표기'].isin(sel_media)
fdf = df[mask]

if fdf.empty:
    st.warning("필터 조건에 맞는 데이터가 없습니다.")
    st.stop()

# ── 탭 ────────────────────────────────────────────────────────────
st.title("📊 무신사 퍼포먼스 대시보드")

tab_dau, tab_active, tab_mt, tab_churn, tab_mb = st.tabs([
    "📊 DAU",
    "🎯 활성고객",
    "📦 무탠유입",
    "↩️ 중저복귀",
    "🎪 무배당발",
])

with tab_dau:
    dau.render(fdf, df)

with tab_active:
    active_customer.render(fdf, df)

with tab_mt:
    mutandard.render(fdf, df)

with tab_churn:
    return_user.render(fdf, df)

with tab_mb:
    mubaedan.render(fdf, df)
