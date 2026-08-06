from __future__ import annotations
import os
from datetime import timedelta
import pandas as pd
import streamlit as st

from rd_loader import (
    agg_kpi, agg_kpi_active, delta_pct, delta_label, get_prev_date, get_period_label,
    COL_DATE, COL_DETAIL, COL_PART, COL_BRAND_DETAIL,
    PART_ACTIVE_CUS, ACTIVE_EXCLUDE_BRANDS,
)
from comment_generator import build_active_comment, format_won, format_cpu, format_cvr, format_roas, format_count


def render(full_df: pd.DataFrame, raw_df: pd.DataFrame | None = None):
    ac_df = full_df[full_df[COL_PART] == PART_ACTIVE_CUS].copy()
    # 제휴 브랜드 제외
    if COL_BRAND_DETAIL in ac_df.columns:
        ac_df = ac_df[~ac_df[COL_BRAND_DETAIL].isin(ACTIVE_EXCLUDE_BRANDS)]
    if ac_df.empty:
        st.info("활성고객 데이터가 없습니다.")
        return

    target_date = ac_df[COL_DATE].max()
    start_date  = ac_df[COL_DATE].min().date()
    end_date    = target_date.date()
    is_multiday = start_date != end_date

    # 브랜드 제외 적용된 전체 raw (날짜 필터 없음)
    raw_ac = raw_df[raw_df[COL_PART] == PART_ACTIVE_CUS].copy() if raw_df is not None else ac_df.copy()
    if COL_BRAND_DETAIL in raw_ac.columns:
        raw_ac = raw_ac[~raw_ac[COL_BRAND_DETAIL].isin(ACTIVE_EXCLUDE_BRANDS)]

    if is_multiday:
        period_days     = (end_date - start_date).days + 1
        prev_end_date   = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - timedelta(days=period_days - 1)
        day_df  = ac_df  # 선택 기간 전체 합산
        prev_df = raw_ac[
            (raw_ac[COL_DATE].dt.date >= prev_start_date) &
            (raw_ac[COL_DATE].dt.date <= prev_end_date)
        ]
        header_text = (
            f"📅 {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')} "
            f"합산 성과 (전{period_days}일 대비)"
        )
    else:
        day_df    = ac_df[ac_df[COL_DATE] == target_date]
        all_dates = raw_ac[COL_DATE].drop_duplicates().sort_values()
        prev_date = get_prev_date(all_dates, target_date)
        prev_df   = raw_ac[raw_ac[COL_DATE] == prev_date] if prev_date is not None else pd.DataFrame()
        header_text = f"📅 {target_date.strftime('%Y-%m-%d')} 기준 (전일 성과)"

    st.markdown(
        f"<div style='font-size:18px;font-weight:700;margin-bottom:16px'>{header_text}</div>",
        unsafe_allow_html=True,
    )

    day_kpi  = agg_kpi_active(day_df)
    prev_kpi = agg_kpi_active(prev_df) if not prev_df.empty else None

    row1 = st.columns(3)
    row2 = st.columns(3)
    metrics = [
        (row1[0], '광고비',       '광고비',    format_won),
        (row1[1], 'GMV 7D',       'GMV7D',     format_won),
        (row1[2], 'GMV 7D ROAS',  'GMV ROAS',  format_roas),
        (row2[0], '활성CPU',      '활성CPU',   format_cpu),
        (row2[1], 'GGMV 1D',      'GGMV1D',    format_won),
        (row2[2], 'GGMV 1D ROAS', 'GGMV ROAS', format_roas),
    ]
    for col, label, key, fmt in metrics:
        val  = day_kpi.get(key)
        prev = prev_kpi.get(key) if prev_kpi else None
        pct  = delta_pct(val, prev)
        col.metric(label, fmt(val), delta_label(pct))

    st.markdown("---")

    st.markdown("**📂 상세구분별 성과**")
    details = day_df[COL_DETAIL].dropna().unique()
    if len(details) > 0:
        cols = st.columns(min(len(details), 3))
        for i, detail in enumerate(details):
            d_df = day_df[day_df[COL_DETAIL] == detail]
            kpi  = agg_kpi_active(d_df)
            if kpi['광고비'] <= 0:
                continue
            with cols[i % 3]:
                st.markdown(
                    f"<div style='background:#fff;border:1px solid #e8e8e8;border-radius:8px;"
                    f"padding:12px 14px;margin-bottom:8px'>"
                    f"<div style='font-weight:700;margin-bottom:6px'>{detail}</div>"
                    f"<div style='font-size:12px;color:#555'>광고비: {format_won(kpi['광고비'])}</div>"
                    f"<div style='font-size:12px;color:#555'>GMV 7D ROAS: {format_roas(kpi['GMV ROAS'])}</div>"
                    f"<div style='font-size:12px;color:#555'>GGMV 1D ROAS: {format_roas(kpi['GGMV ROAS'])}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    st.markdown("---")
    st.markdown("**✍️ 활성고객 코멘트 생성**")
    st.caption("전일 데이터 기준 · TOTAL + 상세구분별")

    col_gen, col_slack = st.columns([2, 1])
    with col_gen:
        generate = st.button("코멘트 생성", type="primary", key="gen_active", use_container_width=True)
    with col_slack:
        slack_ready = bool(os.environ.get('SLACK_BOT_TOKEN') and os.environ.get('SLACK_CHANNEL_ID'))
        has_comment = bool(st.session_state.get('active_comment')) or generate
        slack_btn = st.button(
            "📤 슬랙으로 발송",
            key="slack_active",
            use_container_width=True,
            disabled=not (has_comment and slack_ready),
        )

    if generate or st.session_state.get('active_comment'):
        if generate:
            base_df     = raw_df if raw_df is not None else full_df
            raw_ac_base = base_df[base_df[COL_PART] == PART_ACTIVE_CUS]
            if COL_BRAND_DETAIL in raw_ac_base.columns:
                raw_ac_base = raw_ac_base[~raw_ac_base[COL_BRAND_DETAIL].isin(ACTIVE_EXCLUDE_BRANDS)]
            month_df = raw_ac_base[
                (raw_ac_base[COL_DATE].dt.year  == target_date.year) &
                (raw_ac_base[COL_DATE].dt.month == target_date.month) &
                (raw_ac_base[COL_DATE].dt.date  <= target_date.date())
            ]
            st.session_state['active_comment'] = build_active_comment(
                day_df, target_date, month_df, COL_DETAIL,
                period_label=get_period_label(start_date, end_date),
            )
        comment = st.session_state['active_comment']
        st.text_area(
            "💬 활성고객 코멘트",
            value=comment,
            height=300,
            key="active_comment_area",
        )
        st.caption("✏️ 수정 후 복사하거나 슬랙으로 바로 발송하세요")

        if slack_btn:
            from slack_sender import send_to_slack
            ok, err = send_to_slack(comment)
            if ok:
                st.success("✅ 슬랙 발송 완료!")
            else:
                st.error(f"발송 실패: {err}")

    if not slack_ready:
        st.caption("💡 슬랙 발송 활성화: `.env`에 `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID` 추가")
