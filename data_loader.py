import glob
import os
import pandas as pd

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
CHANNEL_DIR = os.path.join(DATA_DIR, "data", "raw", "channel")
AF_DIR = os.path.join(DATA_DIR, "data", "raw", "appsflyer")

CHANNEL_MAP = {
    "구글": "googleadwords_int",
    "메타": "Facebook Ads",
    "네이버": "naver_search",
}

ROAS_GOOD = 4.0
ROAS_WATCH = 2.0

CHANNEL_COLORS = {
    "구글": "#4285F4",
    "메타": "#1877F2",
    "네이버": "#03C75A",
}

BRAND_KW_CAMPAIGN = "NVR_CMP_01_브랜드KW"


def _parse_creative(series: pd.Series) -> pd.DataFrame:
    parts = series.str.split("_", expand=True).reindex(columns=range(5))
    ab_mask = parts[3].isin(["A", "B"])
    return pd.DataFrame({
        "소재유형": parts[0],
        "소재카테고리": parts[1],
        "소재시즌": parts[2],
        "소재AB": parts[3].where(ab_mask, other=None),
        "소재버전": parts[4].where(ab_mask, other=parts[3]),
    })


def _roas_status(roas: pd.Series) -> pd.Series:
    return pd.cut(
        roas,
        bins=[-float("inf"), ROAS_WATCH, ROAS_GOOD, float("inf")],
        labels=["개선필요", "관찰", "양호"],
    )


def get_wow_pair(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """최신 날짜 데이터와 7일 전 데이터를 반환한다."""
    latest = df["일"].max()
    prev = latest - pd.Timedelta(days=7)
    return df[df["일"] == latest].copy(), df[df["일"] == prev].copy()

JOIN_KEYS = ["일", "캠페인", "그룹", "소재"]


def load_channel() -> pd.DataFrame:
    files = glob.glob(os.path.join(CHANNEL_DIR, "*.csv"))
    if not files:
        return pd.DataFrame()
    df = pd.concat([pd.read_csv(f) for f in sorted(files)], ignore_index=True)
    df["일"] = pd.to_datetime(df["일"])
    df["미디어소스"] = df["채널"].map(CHANNEL_MAP)
    return df


def load_appsflyer() -> pd.DataFrame:
    files = glob.glob(os.path.join(AF_DIR, "*.csv"))
    if not files:
        return pd.DataFrame()
    df = pd.concat([pd.read_csv(f) for f in sorted(files)], ignore_index=True)
    df["일"] = pd.to_datetime(df["일"])
    return df


def load_merged() -> pd.DataFrame:
    ch = load_channel()
    af = load_appsflyer()

    if ch.empty:
        return pd.DataFrame()

    af_cols = JOIN_KEYS + ["클릭", "회원가입", "구매", "구매매출"]
    af_rename = {
        "클릭": "af_클릭",
        "회원가입": "af_회원가입",
        "구매": "af_구매",
        "구매매출": "af_구매매출",
    }

    if not af.empty:
        af_sub = af[af_cols].rename(columns=af_rename)
        merged = ch.merge(af_sub, on=JOIN_KEYS, how="left")
    else:
        merged = ch.copy()
        for col in af_rename.values():
            merged[col] = None

    # 파생 지표
    safe = lambda s: s.replace([float("inf"), float("-inf")], None)
    merged["ROAS"]        = safe(merged["구매매출"] / merged["비용"])
    merged["CTR"]         = safe(merged["클릭"] / merged["노출"])
    merged["CVR"]         = safe(merged["구매"] / merged["클릭"])
    merged["CPA"]         = safe(merged["비용"] / merged["구매"])
    merged["CPM"]         = safe(merged["비용"] / merged["노출"] * 1000)
    merged["가입_CPA"]    = safe(merged["비용"] / merged["af_회원가입"])
    merged["af_커버리지"] = safe(merged["af_회원가입"] / merged["회원가입"] * 100)

    if "af_구매매출" in merged.columns:
        merged["AF_ROAS"] = safe(merged["af_구매매출"] / merged["비용"])

    # 소재명 파싱
    creative_parsed = _parse_creative(merged["소재"])
    merged = pd.concat([merged, creative_parsed], axis=1)

    # ROAS 상태 분류
    merged["roas_상태"] = _roas_status(merged["ROAS"])

    return merged
