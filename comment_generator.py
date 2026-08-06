from __future__ import annotations
import pandas as pd
from rd_loader import (
    agg_kpi, agg_kpi_active, COL_SEG, COL_DETAIL, COL_MEDIA,
    MERGED_DETAIL_SEGS, MERGED_LABELS,
)

SEGMENT_ORDER = ['무탠다드맨', '무탠다드우먼', '무탠다드통합']
ROAS_MEDIA    = {'Facebook', 'Kakao'}


def format_won(amount: float) -> str:
    rounded = round(amount / 10_000) * 10_000  # 1만원 단위 반올림
    eok = int(rounded) // 100_000_000
    man = (int(rounded) % 100_000_000) // 10_000
    if eok > 0 and man > 0:
        return f'{eok}억 {man:,}만원'
    if eok > 0:
        return f'{eok}억원'
    return f'{man:,}만원'


def format_cpu(cpu: int | None) -> str:
    if cpu is None:
        return '—'
    return f'{cpu:,}원'


def format_cvr(cvr: float | None) -> str:
    if cvr is None:
        return '—'
    return f'{cvr:.1f}%'


def format_roas(roas: float | None) -> str:
    if roas is None:
        return '—'
    return f'{roas * 100:.0f}%'


def format_count(n: int | None) -> str:
    if n is None:
        return '—'
    return f'{n:,}명'


def _kpi_str(kpi: dict, period_label: str = '전일') -> str:
    return (
        f"- {period_label} 광고비 {format_won(kpi['광고비'])}, "
        f"활성CPU {format_cpu(kpi['활성CPU'])}, "
        f"고활성CPU {format_cpu(kpi['고활성CPU'])}, "
        f"저활성CPU {format_cpu(kpi['저활성CPU'])}"
    )


def _roas_line(kpi: dict, italic: bool = False, period_label: str = '전일') -> str:
    line = (
        f"- {period_label} 광고비 {format_won(kpi['광고비'])}, "
        f"ROAS {format_roas(kpi['GMV ROAS'])}"
    )
    return f"_{line}_" if italic else line


def build_mutandard_comment(
    day_df: pd.DataFrame,
    target_date: pd.Timestamp,
    month_df: pd.DataFrame,
    period_label: str = '전일',
) -> str:
    lines: list[str] = []
    month_name = f"{target_date.month}월"

    roas_day   = day_df[day_df[COL_MEDIA].isin(ROAS_MEDIA)]
    inflow_day = day_df[~day_df[COL_MEDIA].isin(ROAS_MEDIA)]
    roas_month   = month_df[month_df[COL_MEDIA].isin(ROAS_MEDIA)]
    inflow_month = month_df[~month_df[COL_MEDIA].isin(ROAS_MEDIA)]

    # ── [거래액(무탠)] ──────────────────────────────────────────────
    if not roas_day.empty:
        roas_day_kpi   = agg_kpi_active(roas_day)
        roas_month_kpi = agg_kpi_active(roas_month)

        lines.append('*[거래액(무탠)]*')
        lines.append(
            f"*_- {month_name} 누적 광고비 {format_won(roas_month_kpi['광고비'])}, "
            f"ROAS {format_roas(roas_month_kpi['GMV ROAS'])}_*"
        )
        lines.append(_roas_line(roas_day_kpi, italic=True, period_label=period_label))

        for seg in SEGMENT_ORDER:
            seg_df = roas_day[roas_day[COL_SEG] == seg]
            if seg_df.empty:
                continue

            lines.append('')
            lines.append(f'*[{seg}]*')

            if seg in MERGED_DETAIL_SEGS:
                merged_df = seg_df[seg_df[COL_DETAIL].isin(MERGED_LABELS)]
                if not merged_df.empty:
                    lines.append('*상시/기획전*')
                    lines.append(_roas_line(agg_kpi_active(merged_df), period_label=period_label))

                camp_df = seg_df[seg_df[COL_DETAIL] == '캠페인']
                if not camp_df.empty:
                    lines.append('*캠페인*')
                    lines.append(_roas_line(agg_kpi_active(camp_df), period_label=period_label))
            else:
                lines.append(_roas_line(agg_kpi_active(seg_df), period_label=period_label))

    # ── [유입(무탠)] ───────────────────────────────────────────────
    if not inflow_day.empty:
        inflow_day_kpi   = agg_kpi(inflow_day)
        inflow_month_kpi = agg_kpi(inflow_month)

        lines.append('')
        lines.append('')
        lines.append('*[유입(무탠)]*')
        lines.append(
            f"*_- {month_name} 누적 광고비 {format_won(inflow_month_kpi['광고비'])}, "
            f"활성CPU {format_cpu(inflow_month_kpi['활성CPU'])}_*"
        )
        lines.append(
            f"_- {period_label} 광고비 {format_won(inflow_day_kpi['광고비'])}, "
            f"활성CPU {format_cpu(inflow_day_kpi['활성CPU'])}_"
        )

    return '\n'.join(lines)


def build_mubaedan_comment(
    day_df: pd.DataFrame,
    target_date: pd.Timestamp,
    month_df: pd.DataFrame,
    detail_col: str,
    period_label: str = '전일',
) -> str:
    lines: list[str] = []

    month_kpi  = agg_kpi(month_df)
    day_kpi    = agg_kpi(day_df)
    month_name = f"{target_date.month}월"

    lines.append('#무배당발')
    lines.append(
        f"- {month_name} 누적 광고비 {format_won(month_kpi['광고비'])}, "
        f"활성CPU {format_cpu(month_kpi['활성CPU'])}, "
        f"고활성CPU {format_cpu(month_kpi['고활성CPU'])}, "
        f"저활성CPU {format_cpu(month_kpi['저활성CPU'])}"
    )
    lines.append(_kpi_str(day_kpi, period_label=period_label))

    for detail in day_df[detail_col].dropna().unique():
        d_df = day_df[day_df[detail_col] == detail]
        lines.append(f'\n{detail}')
        lines.append(_kpi_str(agg_kpi(d_df), period_label=period_label))

    return '\n'.join(lines)


def _active_kpi_str(kpi: dict, italic: bool = False, period_label: str = '전일') -> str:
    line = (
        f"- {period_label} 광고비 {format_won(kpi['광고비'])}, "
        f"GMV ROAS {format_roas(kpi['GMV ROAS'])}"
    )
    return f"_{line}_" if italic else line


def build_active_comment(
    day_df: pd.DataFrame,
    target_date: pd.Timestamp,
    month_df: pd.DataFrame,
    detail_col: str,
    period_label: str = '전일',
) -> str:
    lines: list[str] = []

    month_kpi  = agg_kpi_active(month_df)
    day_kpi    = agg_kpi_active(day_df)
    month_name = f"{target_date.month}월"

    lines.append('*[거래액(활성)]*')
    lines.append(
        f"*_- {month_name} 누적 광고비 {format_won(month_kpi['광고비'])}, "
        f"GMV ROAS {format_roas(month_kpi['GMV ROAS'])}_*"
    )
    lines.append(_active_kpi_str(day_kpi, italic=True, period_label=period_label))

    for detail in day_df[detail_col].dropna().unique():
        d_df = day_df[day_df[detail_col] == detail]
        kpi  = agg_kpi_active(d_df)
        if kpi['광고비'] <= 0:
            continue
        lines.append(f'\n*{detail}*')
        lines.append(_active_kpi_str(kpi, period_label=period_label))

    return '\n'.join(lines)
