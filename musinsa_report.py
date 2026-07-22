from __future__ import annotations
import io
import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from rd_loader import load_rd, COL_DATE
from tabs import mutandard, active_customer

load_dotenv()
GDRIVE_FOLDER_ID = os.environ.get('GDRIVE_FOLDER_ID', '')

st.set_page_config(
    page_title="무신사 리포트 대시보드",
    layout="wide",
    page_icon="📦",
)

# ── 사이드바: 데이터 로딩 ──────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 무신사 리포트")

    # Drive 자동 연동 (GDRIVE_FOLDER_ID 설정 시)
    if GDRIVE_FOLDER_ID:
        if st.button("🔄 Drive에서 최신 파일 불러오기", use_container_width=True):
            with st.spinner("Drive에서 불러오는 중..."):
                try:
                    from drive_loader import load_latest_rd
                    df, name = load_latest_rd(GDRIVE_FOLDER_ID)
                    st.session_state['rd_df'] = df
                    st.session_state['rd_name'] = name
                    st.rerun()
                except FileNotFoundError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Drive 연동 오류: {e}")
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
        if GDRIVE_FOLDER_ID:
            st.info("Drive에서 불러오거나 CSV를 업로드하세요.")
        else:
            st.info(
                "RD CSV를 업로드하면 대시보드가 표시됩니다.\n\n"
                "Drive 자동 연동: `.env`에 `GDRIVE_FOLDER_ID`를 추가하세요."
            )
        st.stop()

    df = st.session_state['rd_df']
    rd_name = st.session_state.get('rd_name', 'RD 데이터')
    st.success(f"✅ {rd_name}")

    # ── 날짜·매체 필터 ──
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
