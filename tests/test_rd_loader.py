import pandas as pd
import pytest
from rd_loader import load_rd, calc_cpu, agg_kpi, get_prev_date, COL_DATE


def _make_df(rows):
    return pd.DataFrame(rows)


def test_calc_cpu_normal():
    assert calc_cpu(1_000_000, 10_000) == 100

def test_calc_cpu_zero_users():
    assert calc_cpu(1_000_000, 0) is None

def test_calc_cpu_none_users():
    assert calc_cpu(1_000_000, None) is None

def test_agg_kpi_basic():
    df = _make_df([
        {'광고비_Fee포함': 1_000_000, 'GA_활성사용자수': 10_000,
         'GA_고활성사용자수': 8_000, 'GA_저활성사용자수': 2_000},
        {'광고비_Fee포함': 500_000,  'GA_활성사용자수': 5_000,
         'GA_고활성사용자수': 4_000, 'GA_저활성사용자수': 1_000},
    ])
    result = agg_kpi(df)
    assert result['광고비'] == 1_500_000
    assert result['활성CPU'] == 100   # 1500000 / 15000
    assert result['고활성CPU'] == 125  # 1500000 / 12000
    assert result['저활성CPU'] == 500  # 1500000 / 3000

def test_agg_kpi_all_zero_users():
    df = _make_df([
        {'광고비_Fee포함': 1_000_000, 'GA_활성사용자수': 0,
         'GA_고활성사용자수': 0, 'GA_저활성사용자수': 0},
    ])
    result = agg_kpi(df)
    assert result['활성CPU'] is None
    assert result['고활성CPU'] is None
    assert result['저활성CPU'] is None

def test_get_prev_date():
    dates = pd.to_datetime(['2026-05-13', '2026-05-14'])
    assert get_prev_date(dates, pd.Timestamp('2026-05-14')) == pd.Timestamp('2026-05-13')

def test_get_prev_date_no_prev():
    dates = pd.to_datetime(['2026-05-14'])
    assert get_prev_date(dates, pd.Timestamp('2026-05-14')) is None

def test_load_rd_returns_datetime(tmp_path):
    csv = tmp_path / "test.csv"
    csv.write_text(
        "일,종료일자,캠페인/구분,상세구분,매체,광고비_Fee포함,"
        "GA_활성사용자수,GA_고활성사용자수,GA_저활성사용자수\n"
        "2026-05-14,무탠다드유입,무탠다드맨,상시,Facebook,500000,5000,4000,1000\n",
        encoding='utf-8'
    )
    df = load_rd(str(csv))
    assert pd.api.types.is_datetime64_any_dtype(df['일'])
    assert df['매체_표기'].iloc[0] == '메타'
