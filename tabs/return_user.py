from __future__ import annotations
import os
from datetime import timedelta
import pandas as pd
import streamlit as st

from rd_loader import (
    agg_kpi_return, delta_pct, delta_label, get_prev_date, get_period_label,
    COL_DATE, COL_DETAIL, COL_MEDIA, COL_PART,
    PART_RETURN_USR,
)

_BS_MEDIA = 'naver_brandsearch'
from comment_generator import build_return_comment, format_won, format_cpu, format_roas


def render(full_df: pd.DataFrame, raw_df: pd.DataFrame | None = None):
    ru_df = full_df[full_df[COL_PART] == PART_RETURN_USR].copy()
    if ru_df.empty:
        st.info("중저복귀 데이터가 없습니다.")
        return

    target_date = ru_df[COL_DATE].max()
    start_date  = ru_df[COL_DATE].min().date()
    end_date    = target_date.date()
    is_multiday = start_date != end_date

    raw_ru = (raw_df if raw_df is not None else full_df)
    raw_ru = raw_ru[raw_ru[COL_PART] == PART_RETURN_USR]

    if is_multiday:
        period_days     = (end_date - start_date).days + 1
        prev_end_date   = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - timedelta(days=period_days - 1)
        day_df  = ru_df
        prev_df = raw_ru[
            (raw_ru[COL_DATE].dt.date >= prev_start_date) &
            (raw_ru[COL_DATE].dt.date <= prev_end_date)
        ]
        header_text = (
            f"📅 {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')} "
            f"합산 성과 (전{period_days}일 대비)"
        )
    else:
        day_df    = ru_df[ru_df[COL_DATE] == target_date]
        all_dates = raw_ru[COL_DATE].drop_duplicates().sort_values()
        prev_date = get_prev_date(all_dates, target_date)
        prev_df   = raw_ru[raw_ru[COL_DATE] == prev_date] if prev_date is not None else pd.DataFrame()
        header_text = f"📅 {target_date.strftime('%Y-%m-%d')} 기준 (전일 성과)"

    period_label = get_period_label(start_date, end_date)

    st.markdown(
        f"<div style='font-size:18px;font-weight:700;margin-bottom:16px'>{header_text}</div>",
        unsafe_allow_html=True,
    )

    metrics_def = [
        ('광고비',       '광고비',    format_won),
        ('GMV 7D',       'GMV7D',     format_won),
        ('GMV 7D ROAS',  'GMV ROAS',  format_roas),
        ('중저복귀CPU',  '중저복귀CPU', format_cpu),
        ('GGMV 1D',      'GGMV1D',    format_won),
        ('GGMV 1D ROAS', 'GGMV ROAS', format_roas),
    ]

    def _render_cards(d_df: pd.DataFrame, p_df: pd.DataFrame, title: str):
        st.markdown(f"**{title}**")
        kpi  = agg_kpi_return(d_df)
        prev = agg_kpi_return(p_df) if not p_df.empty else None
        row1 = st.columns(3)
        row2 = st.columns(3)
        for col, (label, key, fmt) in zip(row1 + row2, metrics_def):
            val  = kpi.get(key)
            pval = prev.get(key) if prev else None
            col.metric(label, fmt(val), delta_label(delta_pct(val, pval)))

    bs_mask     = day_df[COL_MEDIA]  == _BS_MEDIA
    bs_mask_p   = prev_df[COL_MEDIA] == _BS_MEDIA if not prev_df.empty else pd.Series(dtype=bool)

    _render_cards(day_df, prev_df, '브검 포함')
    st.markdown("")
    _render_cards(
        day_df[~bs_mask],
        prev_df[~bs_mask_p] if not prev_df.empty else prev_df,
        '브검 미포함',
    )

    st.markdown("---")

    st.markdown("**📂 상세구분별 성과**")
    details = day_df[COL_DETAIL].dropna().unique()
    if len(details) > 0:
        cols = st.columns(min(len(details), 3))
        for i, detail in enumerate(details):
            d_df = day_df[day_df[COL_DETAIL] == detail]
            kpi  = agg_kpi_return(d_df)
            if kpi['광고비'] <= 0:
                continue
            with cols[i % 3]:
                st.markdown(
                    f"<div style='background:#fff;border:1px solid #e8e8e8;border-radius:8px;"
                    f"padding:12px 14px;margin-bottom:8px'>"
                    f"<div style='font-weight:700;margin-bottom:6px'>{detail}</div>"
                    f"<div style='font-size:12px;color:#555'>광고비: {format_won(kpi['광고비'])}</div>"
                    f"<div style='font-size:12px;color:#555'>중저복귀CPU: {format_cpu(kpi['중저복귀CPU'])}</div>"
                    f"<div style='font-size:12px;color:#555'>GMV 7D ROAS: {format_roas(kpi['GMV ROAS'])}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    st.markdown("---")
    st.markdown("**✍️ 중저복귀 코멘트 생성**")
    st.caption("전일 데이터 기준 · TOTAL + 상세구분별")

    col_gen, col_slack = st.columns([2, 1])
    with col_gen:
        generate = st.button("코멘트 생성", type="primary", key="gen_return", use_container_width=True)
    with col_slack:
        slack_ready = bool(os.environ.get('SLACK_BOT_TOKEN') and os.environ.get('SLACK_CHANNEL_ID'))
        has_comment = bool(st.session_state.get('return_comment')) or generate
        slack_btn = st.button(
            "📤 슬랙으로 발송",
            key="slack_return",
            use_container_width=True,
            disabled=not (has_comment and slack_ready),
        )

    if generate or st.session_state.get('return_comment'):
        if generate:
            base_df  = raw_df if raw_df is not None else full_df
            raw_base = base_df[base_df[COL_PART] == PART_RETURN_USR]
            month_df = raw_base[
                (raw_base[COL_DATE].dt.year  == target_date.year) &
                (raw_base[COL_DATE].dt.month == target_date.month) &
                (raw_base[COL_DATE].dt.date  <= target_date.date())
            ]
            st.session_state['return_comment'] = build_return_comment(
                day_df, target_date, month_df,
                period_label=period_label,
            )
        comment = st.session_state['return_comment']
        st.text_area(
            "💬 중저복귀 코멘트",
            value=comment,
            height=300,
            key="return_comment_area",
        )
        st.caption("✏️ 수정 후 복사하거나 슬랙으로 바로 발송하세요")

        if slack_btn:
            from slack_sender import send_to_slack
            ok, err = send_to_slack(comment)
            if ok:
                st.success("✅ 슬랙 발송 완료!")
            else:
                st.error(f"발송 실패: {err}")
