from __future__ import annotations
import pandas as pd
from rd_loader import (
    agg_kpi, agg_kpi_active, COL_SEG, COL_DETAIL,
    MERGED_DETAIL_SEGS, MERGED_LABELS,
)

SEGMENT_ORDER = ['무탠다드맨', '무탠다드우먼', '무탠다드통합']


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


def _kpi_str(kpi: dict) -> str:
    return (
        f"- 전일 광고비 {format_won(kpi['광고비'])}, "
        f"활성CPU {format_cpu(kpi['활성CPU'])}, "
        f"고활성CPU {format_cpu(kpi['고활성CPU'])}, "
        f"저활성CPU {format_cpu(kpi['저활성CPU'])}"
    )


def build_mutandard_comment(
    day_df: pd.DataFrame,
    target_date: pd.Timestamp,
    month_df: pd.DataFrame,
) -> str:
    lines: list[str] = []

    month_kpi  = agg_kpi(month_df)
    day_kpi    = agg_kpi(day_df)
    month_name = f"{target_date.month}월"

    lines.append('#무탠유입')
    lines.append(
        f"- {month_name} 누적 광고비 {format_won(month_kpi['광고비'])}, "
        f"활성CPU {format_cpu(month_kpi['활성CPU'])}, "
        f"고활성CPU {format_cpu(month_kpi['고활성CPU'])}, "
        f"저활성CPU {format_cpu(month_kpi['저활성CPU'])}"
    )
    lines.append(_kpi_str(day_kpi))

    for seg in SEGMENT_ORDER:
        seg_df = day_df[day_df[COL_SEG] == seg]
        if seg_df.empty:
            continue

        lines.append('')
        lines.append(f'[{seg}]')

        if seg in MERGED_DETAIL_SEGS:
            merged_df = seg_df[seg_df[COL_DETAIL].isin(MERGED_LABELS)]
            if not merged_df.empty:
                lines.append('기획전+상시')
                lines.append(_kpi_str(agg_kpi(merged_df)))

            camp_df = seg_df[seg_df[COL_DETAIL] == '캠페인']
            if not camp_df.empty:
                lines.append('캠페인')
                lines.append(_kpi_str(agg_kpi(camp_df)))
        else:
            cat_df = seg_df[seg_df[COL_DETAIL] == '카탈로그']
            if not cat_df.empty:
                lines.append('카탈로그')
                lines.append(_kpi_str(agg_kpi(cat_df)))

    return '\n'.join(lines)


def build_mubaedan_comment(
    day_df: pd.DataFrame,
    target_date: pd.Timestamp,
    month_df: pd.DataFrame,
    detail_col: str,
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
    lines.append(_kpi_str(day_kpi))

    for detail in day_df[detail_col].dropna().unique():
        d_df = day_df[day_df[detail_col] == detail]
        lines.append(f'\n{detail}')
        lines.append(_kpi_str(agg_kpi(d_df)))

    return '\n'.join(lines)


def _active_kpi_str(kpi: dict, italic: bool = False) -> str:
    line = (
        f"- 전일 광고비 {format_won(kpi['광고비'])}, "
        f"GMV ROAS {format_roas(kpi['GMV ROAS'])}"
    )
    return f"_{line}_" if italic else line


def build_active_comment(
    day_df: pd.DataFrame,
    target_date: pd.Timestamp,
    month_df: pd.DataFrame,
    detail_col: str,
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
    lines.append(_active_kpi_str(day_kpi, italic=True))

    for detail in day_df[detail_col].dropna().unique():
        d_df = day_df[day_df[detail_col] == detail]
        kpi  = agg_kpi_active(d_df)
        if kpi['광고비'] <= 0:
            continue
        lines.append(f'\n*{detail}*')
        lines.append(_active_kpi_str(kpi))

    return '\n'.join(lines)
