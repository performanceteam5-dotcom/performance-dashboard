import pandas as pd
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from data_loader import _parse_creative, _roas_status, get_wow_pair

def make_df(**kwargs):
    defaults = dict(
        일=pd.to_datetime(["2025-01-08", "2025-01-08", "2025-01-01"]),
        비용=[100_000, 200_000, 150_000],
        구매매출=[500_000, 300_000, 600_000],
        회원가입=[10, 5, 8],
        af_회원가입=[9, 4, 7],
        소재=["VID_플러스멤버십_겨울_A_v1", "IMG_적립혜택_상시_v1", "CRS_할인쿠폰_봄_B_v2"],
    )
    defaults.update(kwargs)
    return pd.DataFrame(defaults)


def test_parse_creative_five_parts():
    df = make_df()
    result = _parse_creative(df["소재"])
    row = result.iloc[0]
    assert row["소재유형"] == "VID"
    assert row["소재카테고리"] == "플러스멤버십"
    assert row["소재시즌"] == "겨울"
    assert row["소재AB"] == "A"
    assert row["소재버전"] == "v1"


def test_parse_creative_four_parts_no_ab():
    df = make_df()
    result = _parse_creative(df["소재"])
    row = result.iloc[1]  # IMG_적립혜택_상시_v1
    assert row["소재유형"] == "IMG"
    assert row["소재AB"] is None or pd.isna(row["소재AB"])
    assert row["소재버전"] == "v1"


def test_roas_status_labels():
    roas = pd.Series([5.0, 3.0, 1.5, float("nan")])
    result = _roas_status(roas)
    assert result.iloc[0] == "양호"
    assert result.iloc[1] == "관찰"
    assert result.iloc[2] == "개선필요"
    assert pd.isna(result.iloc[3])


def test_get_wow_pair_returns_correct_dates():
    df = make_df()
    curr, prev = get_wow_pair(df)
    assert (curr["일"] == pd.Timestamp("2025-01-08")).all()
    assert (prev["일"] == pd.Timestamp("2025-01-01")).all()


def test_load_merged_adds_derived_columns(tmp_path):
    pytest.skip("integration test requires real CSV files")
