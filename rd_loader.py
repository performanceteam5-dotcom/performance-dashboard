from __future__ import annotations
import io
import pandas as pd

COL_DATE      = '일'
COL_PART      = '종료일자'
COL_SEG       = '캠페인/구분'
COL_DETAIL    = '상세구분'
COL_MEDIA     = '매체'
COL_COST      = '광고비_Fee포함'
COL_ACTIVE    = 'GA_활성사용자수'
COL_HIGH      = 'GA_고활성사용자수'
COL_LOW       = 'GA_저활성사용자수'
COL_BZ_BUYER    = 'BZ_구매자수(7d)'
COL_GA_LOGIN    = 'GA_로그인사용자수'
COL_IMPRESSION  = '노출'
COL_BRAND_DETAIL = '브랜드/소재상세1'
COL_GMV7D           = 'BZ_GMV(7D)'
COL_GGMV1D          = 'BZ_GGMV(1D)'
COL_RETURN_CPU_USER = 'GA_복귀사용자'

ACTIVE_EXCLUDE_BRANDS = {'2606케이뱅크결제제휴', '2607한국투자증권제휴'}

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
PART_MUBAEDAN   = '무배당발'
PART_RETURN_USR = '복귀사용자'

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


def calc_cvr(buyer: float | None, login: float | None) -> float | None:
    if buyer and login and login > 0:
        return buyer / login * 100
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


def calc_roas(revenue: float | None, cost: float) -> float | None:
    if revenue and cost > 0:
        return revenue / cost
    return None


def agg_kpi_active(df: pd.DataFrame) -> dict:
    cost   = df[COL_COST].sum()
    active = df[COL_ACTIVE].sum()
    # 구매 지표: 후속기여 미포함 (노출 > 0 행만)
    perf_df = df[df[COL_IMPRESSION] > 0] if COL_IMPRESSION in df.columns else df
    buyer  = perf_df[COL_BZ_BUYER].sum() if COL_BZ_BUYER in perf_df.columns else None
    login  = perf_df[COL_GA_LOGIN].sum() if COL_GA_LOGIN in perf_df.columns else None
    gmv7d  = perf_df[COL_GMV7D].sum()   if COL_GMV7D   in perf_df.columns else None
    ggmv1d = perf_df[COL_GGMV1D].sum()  if COL_GGMV1D  in perf_df.columns else None
    return {
        '광고비':      cost,
        '활성CPU':     calc_cpu(cost, active),
        '구매CVR':     calc_cvr(buyer, login),
        '구매자수':    int(buyer) if buyer else None,
        '구매자수CPA': calc_cpu(cost, buyer),
        'GMV7D':       gmv7d,
        'GMV ROAS':    calc_roas(gmv7d, cost),
        'GGMV1D':      ggmv1d,
        'GGMV ROAS':   calc_roas(ggmv1d, cost),
    }


def agg_kpi_return(df: pd.DataFrame) -> dict:
    cost     = df[COL_COST].sum()
    low      = df[COL_LOW].sum()             if COL_LOW             in df.columns else 0
    ret_user = df[COL_RETURN_CPU_USER].sum() if COL_RETURN_CPU_USER in df.columns else 0
    denom    = low + ret_user                # GA_저활성사용자수 + GA_복귀사용자
    perf_df  = df[df[COL_IMPRESSION] > 0]   if COL_IMPRESSION in df.columns else df
    gmv7d    = perf_df[COL_GMV7D].sum()     if COL_GMV7D  in perf_df.columns else None
    ggmv1d   = perf_df[COL_GGMV1D].sum()   if COL_GGMV1D in perf_df.columns else None
    return {
        '광고비':      cost,
        '중저복귀CPU': calc_cpu(cost, denom) if denom else 0,
        'GMV7D':       gmv7d,
        'GMV ROAS':    calc_roas(gmv7d, cost),
        'GGMV1D':      ggmv1d,
        'GGMV ROAS':   calc_roas(ggmv1d, cost),
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


def delta_label(pct: float | None) -> str | None:
    if pct is None or abs(pct) < 5:
        return None
    return f'{abs(pct):.0f}%' if pct > 0 else f'-{abs(pct):.0f}%'


_KO_WEEKDAY = ['월', '화', '수', '목', '금', '토', '일']


def get_period_label(start_date, end_date) -> str:
    """날짜 범위 → 코멘트용 기간 레이블 (전일 / 금-일 / 월-수 등)"""
    if start_date == end_date:
        return '전일'
    return f"{_KO_WEEKDAY[start_date.weekday()]}-{_KO_WEEKDAY[end_date.weekday()]}"


def delta_status(pct: float | None) -> str:
    """CPU 기준: 올라가면 악화, 내려가면 개선."""
    if pct is None:
        return 'flat'
    if pct > 5:
        return 'bad'
    if pct < -5:
        return 'good'
    return 'flat'
