from __future__ import annotations
import pandas as pd
import streamlit as st

from rd_loader import (
    agg_kpi, delta_pct, delta_label, delta_status, get_prev_date,
    COL_DATE, COL_SEG, COL_DETAIL, COL_PART,
    PART_MUTANDARD, MERGED_DETAIL_SEGS, MERGED_LABELS,
)
from comment_generator import build_mutandard_comment, format_won, format_cpu

SEGMENT_ORDER = ['무탠다드맨', '무탠다드우먼', '무탠다드통합']
SEGMENT_EMOJI = {'무탠다드맨': '🔵', '무탠다드우먼': '🔴', '무탠다드통합': '🟢'}
SEGMENT_BG    = {'무탠다드맨': '#eef3fb', '무탠다드우먼': '#fdf2fb', '무탠다드통합': '#eefaf3'}

_BADGE = {
    'good': '<span style="background:#dcfce7;color:#16a34a;border-radius:8px;padding:1px 8px;font-size:11px;font-weight:700">▼ 개선</span>',
    'bad':  '<span style="background:#fee2e2;color:#e53e3e;border-radius:8px;padding:1px 8px;font-size:11px;font-weight:700">▲ 악화</span>',
    'flat': '<span style="background:#f1f5f9;color:#64748b;border-radius:8px;padding:1px 8px;font-size:11px;font-weight:700">— 동수준</span>',
}


def _badge(pct: float | None) -> str:
    return _BADGE[delta_status(pct)]


def _render_kpi_cards(kpi: dict, prev_kpi: dict | None):
    c1, c2, c3, c4 = st.columns(4)
    for col, label, key in [
        (c1, '광고비',    '광고비'),
        (c2, '활성CPU',   '활성CPU'),
        (c3, '고활성CPU', '고활성CPU'),
        (c4, '저활성CPU', '저활성CPU'),
    ]:
        val  = kpi.get(key)
        prev = prev_kpi.get(key) if prev_kpi else None
        pct  = delta_pct(val, prev)
        display = format_won(val) if key == '광고비' else format_cpu(val)
        col.metric(label, display, delta_label(pct))


def render(full_df: pd.DataFrame, raw_df: pd.DataFrame | None = None):
    mt_df = full_df[full_df[COL_PART] == PART_MUTANDARD].copy()
    if mt_df.empty:
        st.info("무탠다드유입 데이터가 없습니다.")
        return

    dates       = mt_df[COL_DATE].drop_duplicates().sort_values()
    target_date = dates.max()
    prev_date   = get_prev_date(dates, target_date)

    day_df  = mt_df[mt_df[COL_DATE] == target_date]
    prev_df = mt_df[mt_df[COL_DATE] == prev_date] if prev_date is not None else pd.DataFrame()

    # 월 누적: 날짜 필터 미적용 원본 기준 당월 1일~target_date
    base_df  = raw_df if raw_df is not None else full_df
    raw_mt   = base_df[base_df[COL_PART] == PART_MUTANDARD]
    month_df = raw_mt[
        (raw_mt[COL_DATE].dt.year  == target_date.year) &
        (raw_mt[COL_DATE].dt.month == target_date.month) &
        (raw_mt[COL_DATE].dt.date  <= target_date.date())
    ]

    st.markdown(
        f"<div style='font-size:18px;font-weight:700;margin-bottom:16px'>"
        f"📅 {target_date.strftime('%Y-%m-%d')} 기준 (전일 성과)</div>",
        unsafe_allow_html=True,
    )

    day_kpi  = agg_kpi(day_df)
    prev_kpi = agg_kpi(prev_df) if not prev_df.empty else None
    _render_kpi_cards(day_kpi, prev_kpi)

    st.markdown("**📂 세그먼트 × 상세구분 성과**")

    rows_html = [
        "<table style='width:100%;border-collapse:collapse;font-size:12px'>"
        "<thead><tr style='background:#f8f9fa'>"
        "<th style='padding:9px 14px;text-align:left;border-bottom:1px solid #e8e8e8'>세그먼트 / 상세구분</th>"
        "<th style='padding:9px 14px;text-align:right;border-bottom:1px solid #e8e8e8'>광고비</th>"
        "<th style='padding:9px 14px;text-align:right;border-bottom:1px solid #e8e8e8'>활성CPU</th>"
        "<th style='padding:9px 14px;text-align:right;border-bottom:1px solid #e8e8e8'>고활성CPU</th>"
        "<th style='padding:9px 14px;text-align:right;border-bottom:1px solid #e8e8e8'>저활성CPU</th>"
        "<th style='padding:9px 14px;text-align:right;border-bottom:1px solid #e8e8e8'>전일比</th>"
        "</tr></thead><tbody>"
    ]

    for seg in SEGMENT_ORDER:
        seg_day  = day_df[day_df[COL_SEG] == seg]
        seg_prev = prev_df[prev_df[COL_SEG] == seg] if not prev_df.empty else pd.DataFrame()
        if seg_day.empty:
            continue

        seg_kpi      = agg_kpi(seg_day)
        prev_seg_kpi = agg_kpi(seg_prev) if not seg_prev.empty else None
        pct  = delta_pct(seg_kpi['활성CPU'], prev_seg_kpi['활성CPU'] if prev_seg_kpi else None)
        bg   = SEGMENT_BG[seg]
        emoji = SEGMENT_EMOJI[seg]

        rows_html.append(
            f"<tr style='background:{bg}'>"
            f"<td style='padding:8px 14px;font-weight:700'>{emoji} {seg}</td>"
            f"<td style='padding:8px 14px;text-align:right'>{format_won(seg_kpi['광고비'])}</td>"
            f"<td style='padding:8px 14px;text-align:right'>—</td>"
            f"<td style='padding:8px 14px;text-align:right'>—</td>"
            f"<td style='padding:8px 14px;text-align:right'>—</td>"
            f"<td style='padding:8px 14px;text-align:right'>{_badge(pct)}</td>"
            f"</tr>"
        )
        rows_html.extend(_get_detail_rows(seg, seg_day, seg_prev))

    rows_html.append("</tbody></table>")
    st.markdown(''.join(rows_html), unsafe_allow_html=True)
    st.markdown("")

    st.markdown("---")
    col_left, col_right = st.columns([3, 1])
    with col_left:
        st.markdown("**✍️ 무탠유입 코멘트 생성**")
        st.caption("세그먼트 3개 × 기획전+상시·캠페인 구분 · 전일 데이터 기준")
    with col_right:
        generate = st.button("코멘트 생성", type="primary", key="gen_mutandard")

    if generate or st.session_state.get('mutandard_comment'):
        if generate:
            st.session_state['mutandard_comment'] = build_mutandard_comment(
                day_df, target_date, month_df
            )
        st.text_area(
            "💬 무탠유입 코멘트",
            value=st.session_state['mutandard_comment'],
            height=400,
            key="mutandard_comment_area",
        )
        st.caption("✏️ 수정 후 복사해서 슬랙에 붙여넣으세요")


def _get_detail_rows(seg: str, seg_day: pd.DataFrame, seg_prev: pd.DataFrame) -> list[str]:
    rows: list[str] = []

    def _row(label: str, kpi: dict, prev_kpi: dict | None) -> str:
        pct = delta_pct(kpi['활성CPU'], prev_kpi['활성CPU'] if prev_kpi else None)
        return (
            f"<tr style='border-bottom:1px solid #f5f5f5'>"
            f"<td style='padding:8px 14px 8px 32px;color:#555'>{label}</td>"
            f"<td style='padding:8px 14px;text-align:right;font-weight:600'>{format_won(kpi['광고비'])}</td>"
            f"<td style='padding:8px 14px;text-align:right;font-weight:600'>{format_cpu(kpi['활성CPU'])}</td>"
            f"<td style='padding:8px 14px;text-align:right;font-weight:600'>{format_cpu(kpi['고활성CPU'])}</td>"
            f"<td style='padding:8px 14px;text-align:right;font-weight:600'>{format_cpu(kpi['저활성CPU'])}</td>"
            f"<td style='padding:8px 14px;text-align:right'>{_badge(pct)}</td>"
            f"</tr>"
        )

    if seg in MERGED_DETAIL_SEGS:
        merged_day  = seg_day[seg_day[COL_DETAIL].isin(MERGED_LABELS)]
        merged_prev = seg_prev[seg_prev[COL_DETAIL].isin(MERGED_LABELS)] if not seg_prev.empty else pd.DataFrame()
        if not merged_day.empty:
            rows.append(_row('기획전+상시', agg_kpi(merged_day),
                             agg_kpi(merged_prev) if not merged_prev.empty else None))

        camp_day  = seg_day[seg_day[COL_DETAIL] == '캠페인']
        camp_prev = seg_prev[seg_prev[COL_DETAIL] == '캠페인'] if not seg_prev.empty else pd.DataFrame()
        if not camp_day.empty:
            rows.append(_row('캠페인', agg_kpi(camp_day),
                             agg_kpi(camp_prev) if not camp_prev.empty else None))
    else:
        cat_day  = seg_day[seg_day[COL_DETAIL] == '카탈로그']
        cat_prev = seg_prev[seg_prev[COL_DETAIL] == '카탈로그'] if not seg_prev.empty else pd.DataFrame()
        if not cat_day.empty:
            rows.append(_row('카탈로그', agg_kpi(cat_day),
                             agg_kpi(cat_prev) if not cat_prev.empty else None))

    return rows
