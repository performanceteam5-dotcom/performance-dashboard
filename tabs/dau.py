from __future__ import annotations
import os
from datetime import timedelta
import pandas as pd
import streamlit as st

from rd_loader import (
    agg_kpi_active, delta_pct, delta_label, get_prev_date, get_period_label,
    COL_DATE, COL_PART,
    PART_ACTIVE_CUS, PART_MUTANDARD, PART_RETURN_USR,
)
from comment_generator import format_won, format_cpu, format_roas, build_dau_total_comment
from tabs.active_customer import get_comment as _ac_comment
from tabs.mutandard import get_comment as _mt_comment
from tabs.return_user import get_comment as _ru_comment

_DAU_PARTS = {PART_ACTIVE_CUS, PART_MUTANDARD, PART_RETURN_USR}


def render(full_df: pd.DataFrame, raw_df: pd.DataFrame | None = None):
    dau_df = full_df[full_df[COL_PART].isin(_DAU_PARTS)].copy()
    if dau_df.empty:
        st.info("DAU 데이터가 없습니다.")
        return

    target_date  = dau_df[COL_DATE].max()
    start_date   = dau_df[COL_DATE].min().date()
    end_date     = target_date.date()
    is_multiday  = start_date != end_date
    period_label = get_period_label(start_date, end_date)

    base_df = raw_df if raw_df is not None else full_df
    raw_dau = base_df[base_df[COL_PART].isin(_DAU_PARTS)]

    if is_multiday:
        period_days     = (end_date - start_date).days + 1
        prev_end_date   = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - timedelta(days=period_days - 1)
        day_df  = dau_df
        prev_df = raw_dau[
            (raw_dau[COL_DATE].dt.date >= prev_start_date) &
            (raw_dau[COL_DATE].dt.date <= prev_end_date)
        ]
        header_text = (
            f"📅 {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')} "
            f"합산 성과 (전{period_days}일 대비)"
        )
    else:
        day_df    = dau_df[dau_df[COL_DATE] == target_date]
        all_dates = raw_dau[COL_DATE].drop_duplicates().sort_values()
        prev_date = get_prev_date(all_dates, target_date)
        prev_df   = raw_dau[raw_dau[COL_DATE] == prev_date] if prev_date is not None else pd.DataFrame()
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
        col.metric(label, fmt(val), delta_label(delta_pct(val, prev)))

    st.markdown("---")
    st.markdown("**✍️ DAU 코멘트 생성**")
    st.caption("활성고객 + 무탠유입 + 중저복귀 코멘트 통합")

    col_gen, col_slack = st.columns([2, 1])
    with col_gen:
        generate = st.button("코멘트 생성", type="primary", key="gen_dau", use_container_width=True)
    with col_slack:
        slack_ready = bool(os.environ.get('SLACK_BOT_TOKEN') and os.environ.get('SLACK_CHANNEL_ID'))
        has_comment = bool(st.session_state.get('dau_comment')) or generate
        slack_btn = st.button(
            "📤 슬랙으로 발송",
            key="slack_dau",
            use_container_width=True,
            disabled=not (has_comment and slack_ready),
        )

    if generate or st.session_state.get('dau_comment'):
        if generate:
            raw_dau_all = base_df[base_df[COL_PART].isin(_DAU_PARTS)]
            month_df = raw_dau_all[
                (raw_dau_all[COL_DATE].dt.year  == target_date.year) &
                (raw_dau_all[COL_DATE].dt.month == target_date.month) &
                (raw_dau_all[COL_DATE].dt.date  <= target_date.date())
            ]
            parts: list[str] = [build_dau_total_comment(day_df, target_date, month_df, period_label)]
            if not day_df[day_df[COL_PART] == PART_ACTIVE_CUS].empty:
                parts.append(_ac_comment(base_df, target_date, start_date, end_date, period_label))
            if not day_df[day_df[COL_PART] == PART_MUTANDARD].empty:
                parts.append(_mt_comment(base_df, target_date, start_date, end_date, period_label))
            if not day_df[day_df[COL_PART] == PART_RETURN_USR].empty:
                parts.append(_ru_comment(base_df, target_date, start_date, end_date, period_label))
            st.session_state['dau_comment'] = '\n\n\n'.join(parts)

        comment = st.session_state['dau_comment']
        st.text_area(
            "💬 DAU 코멘트",
            value=comment,
            height=500,
            key="dau_comment_area",
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
