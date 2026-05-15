from __future__ import annotations
import io
import pandas as pd

COL_DATE   = '일'
COL_PART   = '종료일자'
COL_SEG    = '캠페인/구분'
COL_DETAIL = '상세구분'
COL_MEDIA  = '매체'
COL_COST   = '광고비_Fee포함'
COL_ACTIVE = 'GA_활성사용자수'
COL_HIGH   = 'GA_고활성사용자수'
COL_LOW    = 'GA_저활성사용자수'

MEDIA_MAP: dict[str, str] = {
    'Facebook':            '메타',
    'Kakao':               '카카오',
    'KAKAO':               '카카오',
    'tiktok':              '틱톡',
    'moloco':              '몰로코',
    'appier':              '에피어',
    'cauly_int':           '카울리',
    'carrot':              '당근',
    'toss_rw':             '토스',
    'adisonofferwall_rw':  '애디슨',
    'cookieoven_rw':       '쿠키오븐',
}

PART_MUTANDARD  = '무탠다드유입'
PART_ACTIVE_CUS = '활성고객'

MERGED_DETAIL_SEGS = {'무탠다드맨', '무탠다드우먼'}
MERGED_LABELS      = ('기획전', '상시')


def load_rd(path: str | io.BytesIO) -> pd.DataFrame:
    df = pd.read_csv(path, encoding='utf-8')
    df[COL_DATE] = pd.to_datetime(df[COL_DATE])
    df['매체_표기'] = df[COL_MEDIA].map(MEDIA_MAP).fillna(df[COL_MEDIA])
    return df


def calc_cpu(cost: float, users: float | None) -> int | None:
    if users and users > 0:
        return round(cost / users)
    return None


def agg_kpi(df: pd.DataFrame) -> dict:
    cost   = df[COL_COST].sum()
    active = df[COL_ACTIVE].sum()
    high   = df[COL_HIGH].sum()
    low    = df[COL_LOW].sum()
    return {
        '광고비':    cost,
        '활성CPU':   calc_cpu(cost, active),
        '고활성CPU': calc_cpu(cost, high),
        '저활성CPU': calc_cpu(cost, low),
    }


def get_prev_date(
    available_dates: pd.DatetimeIndex | pd.Series,
    target: pd.Timestamp,
) -> pd.Timestamp | None:
    earlier = sorted(d for d in pd.DatetimeIndex(available_dates) if d < target)
    return earlier[-1] if earlier else None


def delta_pct(curr: int | float | None, prev: int | float | None) -> float | None:
    if curr is None or prev is None or prev == 0:
        return None
    return (curr - prev) / abs(prev) * 100


def delta_label(pct: float | None) -> str:
    if pct is None:
        return '—'
    if abs(pct) < 5:
        return '— 동수준'
    sign = '▲' if pct > 0 else '▼'
    return f'{sign} {abs(pct):.0f}%'


def delta_status(pct: float | None) -> str:
    """CPU 기준: 올라가면 악화, 내려가면 개선."""
    if pct is None:
        return 'flat'
    if pct > 5:
        return 'bad'
    if pct < -5:
        return 'good'
    return 'flat'
