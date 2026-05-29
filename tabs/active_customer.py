from __future__ import annotations
import pandas as pd
import streamlit as st

from rd_loader import (
    agg_kpi, delta_pct, delta_label, get_prev_date,
    COL_DATE, COL_DETAIL, COL_PART,
    PART_ACTIVE_CUS,
)
from comment_generator import build_active_comment, format_won, format_cpu


def render(full_df: pd.DataFrame, raw_df: pd.DataFrame | None = None):
    ac_df = full_df[full_df[COL_PART] == PART_ACTIVE_CUS].copy()
    if ac_df.empty:
        st.info("활성고객 데이터가 없습니다.")
        return

    dates       = ac_df[COL_DATE].drop_duplicates().sort_values()
    target_date = dates.max()
    prev_date   = get_prev_date(dates, target_date)

    day_df  = ac_df[ac_df[COL_DATE] == target_date]
    prev_df = ac_df[ac_df[COL_DATE] == prev_date] if prev_date is not None else pd.DataFrame()

    st.markdown(
        f"<div style='font-size:18px;font-weight:700;margin-bottom:16px'>"
        f"📅 {target_date.strftime('%Y-%m-%d')} 기준 (전일 성과)</div>",
        unsafe_allow_html=True,
    )

    day_kpi  = agg_kpi(day_df)
    prev_kpi = agg_kpi(prev_df) if not prev_df.empty else None

    c1, c2, c3, c4 = st.columns(4)
    for col, label, key in [
        (c1, '광고비',    '광고비'),
        (c2, '활성CPU',   '활성CPU'),
        (c3, '고활성CPU', '고활성CPU'),
        (c4, '저활성CPU', '저활성CPU'),
    ]:
        val  = day_kpi.get(key)
        prev = prev_kpi.get(key) if prev_kpi else None
        pct  = delta_pct(val, prev)
        display = format_won(val) if key == '광고비' else format_cpu(val)
        col.metric(label, display, delta_label(pct))

    st.markdown("---")

    st.markdown("**📂 상세구분별 성과**")
    details = day_df[COL_DETAIL].dropna().unique()
    if len(details) > 0:
        cols = st.columns(min(len(details), 3))
        for i, detail in enumerate(details):
            d_df = day_df[day_df[COL_DETAIL] == detail]
            kpi  = agg_kpi(d_df)
            with cols[i % 3]:
                st.markdown(
                    f"<div style='background:#fff;border:1px solid #e8e8e8;border-radius:8px;"
                    f"padding:12px 14px;margin-bottom:8px'>"
                    f"<div style='font-weight:700;margin-bottom:6px'>{detail}</div>"
                    f"<div style='font-size:12px;color:#555'>광고비: {format_won(kpi['광고비'])}</div>"
                    f"<div style='font-size:12px;color:#555'>활성CPU: {format_cpu(kpi['활성CPU'])}</div>"
                    f"<div style='font-size:12px;color:#555'>고활성CPU: {format_cpu(kpi['고활성CPU'])}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    st.markdown("---")
    col_left, col_right = st.columns([3, 1])
    with col_left:
        st.markdown("**✍️ 활성고객 코멘트 생성**")
        st.caption("전일 데이터 기준 · TOTAL + 상세구분별")
    with col_right:
        generate = st.button("코멘트 생성", type="primary", key="gen_active")

    if generate or st.session_state.get('active_comment'):
        if generate:
            base_df  = raw_df if raw_df is not None else full_df
            raw_ac   = base_df[base_df[COL_PART] == PART_ACTIVE_CUS]
            month_df = raw_ac[
                (raw_ac[COL_DATE].dt.year  == target_date.year) &
                (raw_ac[COL_DATE].dt.month == target_date.month) &
                (raw_ac[COL_DATE].dt.date  <= target_date.date())
            ]
            st.session_state['active_comment'] = build_active_comment(
                day_df, target_date, month_df, COL_DETAIL
            )
        st.text_area(
            "💬 활성고객 코멘트",
            value=st.session_state['active_comment'],
            height=300,
            key="active_comment_area",
        )
        st.caption("✏️ 수정 후 복사해서 슬랙에 붙여넣으세요")
