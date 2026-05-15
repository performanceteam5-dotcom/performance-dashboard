# 퍼포먼스 마케팅 대시보드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Streamlit 기반 퍼포먼스 마케팅 대시보드를 5탭 구조로 재구성한다 — 아침 브리핑(오늘 요약), 트렌드, 소재 분석, 보고서(CSV 다운로드), AF 검증.

**Architecture:** data_loader.py에 파생 지표를 추가하고, 탭별 렌더 함수를 `tabs/` 모듈로 분리한다. dashboard.py는 공통 사이드바 필터 + 탭 라우팅만 담당한다.

**Tech Stack:** Python 3.11+, Streamlit ≥1.35, Plotly ≥5.20, pandas ≥2.0

---

## 파일 구조

```
clade_0514/
├── data_loader.py          # 수정: 파생 지표 추가, get_wow_pair() 추가
├── dashboard.py            # 수정: 5탭 구조 + 공통 사이드바
├── tabs/
│   ├── __init__.py         # 신규
│   ├── summary.py          # 신규: 탭1 오늘 요약
│   ├── trend.py            # 신규: 탭2 트렌드
│   ├── creative.py         # 신규: 탭3 소재 분석
│   ├── report.py           # 신규: 탭4 보고서
│   └── af_verify.py        # 신규: 탭5 AF 검증
└── tests/
    └── test_data_loader.py # 신규: data_loader 단위 테스트
```

---

## Task 1: data_loader.py 파생 지표 확장

**Files:**
- Modify: `data_loader.py`
- Create: `tests/test_data_loader.py`

- [ ] **Step 1: 테스트 파일 생성**

`tests/test_data_loader.py` 를 새로 만든다:

```python
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
    import shutil
    from data_loader import load_merged, CHANNEL_DIR, AF_DIR
    # 실제 data 디렉토리 파일이 있어야 동작하므로 통합 테스트는 스킵
    pytest.skip("integration test requires real CSV files")
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
python -m pytest tests/test_data_loader.py -v 2>&1 | head -30
```

Expected: `ImportError: cannot import name '_parse_creative'`

- [ ] **Step 3: data_loader.py에 헬퍼 함수 추가**

`data_loader.py` 상단 상수 아래에 삽입:

```python
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
```

- [ ] **Step 4: load_merged()에 파생 지표 추가**

`load_merged()` 의 `# 파생 지표` 블록을 아래로 교체한다:

```python
    # 파생 지표
    safe = lambda s: s.replace([float("inf"), float("-inf")], None)
    merged["ROAS"]     = safe(merged["구매매출"] / merged["비용"])
    merged["CTR"]      = safe(merged["클릭"] / merged["노출"])
    merged["CVR"]      = safe(merged["구매"] / merged["클릭"])
    merged["CPA"]      = safe(merged["비용"] / merged["구매"])
    merged["CPM"]      = safe(merged["비용"] / merged["노출"] * 1000)
    merged["가입_CPA"] = safe(merged["비용"] / merged["af_회원가입"])
    merged["af_커버리지"] = safe(merged["af_회원가입"] / merged["회원가입"] * 100)

    if "af_구매매출" in merged.columns:
        merged["AF_ROAS"] = safe(merged["af_구매매출"] / merged["비용"])

    # 소재명 파싱
    creative_parsed = _parse_creative(merged["소재"])
    merged = pd.concat([merged, creative_parsed], axis=1)

    # ROAS 상태 분류
    merged["roas_상태"] = _roas_status(merged["ROAS"])

    return merged
```

- [ ] **Step 5: 테스트 재실행 — 통과 확인**

```bash
python -m pytest tests/test_data_loader.py -v -k "not load_merged"
```

Expected: 4 tests PASSED

- [ ] **Step 6: 커밋**

```bash
git add data_loader.py tests/test_data_loader.py
git commit -m "feat: data_loader에 파생 지표 추가 (가입_CPA, af_커버리지, 소재 파싱, roas_상태)"
```

---

## Task 2: tabs/ 패키지 초기화

**Files:**
- Create: `tabs/__init__.py`

- [ ] **Step 1: 디렉토리 & __init__ 생성**

`tabs/__init__.py` 를 빈 파일로 만든다:

```python
```

- [ ] **Step 2: 커밋**

```bash
git add tabs/__init__.py
git commit -m "chore: tabs 패키지 초기화"
```

---

## Task 3: 탭1 — 오늘 요약 (tabs/summary.py)

**Files:**
- Create: `tabs/summary.py`

- [ ] **Step 1: summary.py 작성**

```python
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_loader import ROAS_GOOD, ROAS_WATCH, CHANNEL_COLORS, get_wow_pair, BRAND_KW_CAMPAIGN

_STATUS_EMOJI = {"양호": "🟢", "관찰": "🟡", "개선필요": "🔴"}
_STATUS_COLOR = {"양호": "#2ecc71", "관찰": "#f39c12", "개선필요": "#e74c3c"}


def _agg(df: pd.DataFrame) -> dict:
    cost = df["비용"].sum()
    rev = df["구매매출"].sum()
    signup = df["af_회원가입"].sum()
    ch_signup = df["회원가입"].sum()
    return {
        "비용": cost,
        "매출": rev,
        "ROAS": rev / cost if cost else None,
        "가입_CPA": cost / signup if signup else None,
        "af_커버리지": signup / ch_signup * 100 if ch_signup else None,
    }


def _delta_str(curr, prev) -> str:
    if prev is None or prev == 0 or curr is None:
        return ""
    pct = (curr - prev) / abs(prev) * 100
    sign = "▲" if pct > 0 else "▼"
    return f"{sign} {abs(pct):.1f}% vs 전주"


def _kpi_card(col, label: str, value, prev_value, fmt: str):
    if value is None:
        col.metric(label, "N/A")
        return
    if fmt == "won":
        display = f"₩{value/1e8:.1f}억" if value >= 1e8 else f"₩{value/1e4:.0f}만"
    elif fmt == "roas":
        display = f"{value:.2f}"
    elif fmt == "pct":
        display = f"{value:.1f}%"
    else:
        display = f"₩{value:,.0f}"
    delta = _delta_str(value, prev_value)
    col.metric(label, display, delta)


def render(df: pd.DataFrame):
    curr_df, prev_df = get_wow_pair(df)
    curr = _agg(curr_df)
    prev = _agg(prev_df)

    latest_date = df["일"].max().strftime("%Y-%m-%d")
    st.subheader(f"📅 {latest_date} 기준 (전일 성과)")

    # KPI 카드
    c1, c2, c3, c4 = st.columns(4)
    _kpi_card(c1, "총 비용", curr["비용"], prev["비용"], "won")
    _kpi_card(c2, "ROAS", curr["ROAS"], prev["ROAS"], "roas")
    _kpi_card(c3, "가입 CPA", curr["가입_CPA"], prev["가입_CPA"], "cpa")
    _kpi_card(c4, "AF 커버리지", curr["af_커버리지"], prev["af_커버리지"], "pct")

    # ROAS 신호등
    roas_val = curr["ROAS"]
    if roas_val is not None:
        status = "양호" if roas_val >= ROAS_GOOD else ("관찰" if roas_val >= ROAS_WATCH else "개선필요")
        color = _STATUS_COLOR[status]
        st.markdown(
            f"<div style='background:{color}22;border-left:4px solid {color};"
            f"padding:10px 16px;border-radius:6px;margin:8px 0'>"
            f"<b>전체 ROAS {roas_val:.2f}</b> — {_STATUS_EMOJI[status]} {status}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # 채널 상태
    st.markdown("**채널별 상태**")
    ch_roas = (
        curr_df.groupby("채널")
        .apply(lambda x: x["구매매출"].sum() / x["비용"].sum() if x["비용"].sum() else None)
        .dropna()
    )
    cols = st.columns(len(ch_roas))
    for col, (ch, roas) in zip(cols, ch_roas.items()):
        s = "양호" if roas >= ROAS_GOOD else ("관찰" if roas >= ROAS_WATCH else "개선필요")
        color = CHANNEL_COLORS.get(ch, "#aaa")
        col.markdown(
            f"<div style='background:#1a2332;border-top:3px solid {color};"
            f"padding:12px;border-radius:6px;text-align:center'>"
            f"<div style='color:{color};font-weight:700'>{ch}</div>"
            f"<div style='font-size:20px'>{_STATUS_EMOJI[s]}</div>"
            f"<div style='font-weight:700'>ROAS {roas:.2f}</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # 주의 캠페인
    camp_roas = (
        curr_df.groupby("캠페인")
        .apply(lambda x: x["구매매출"].sum() / x["비용"].sum() if x["비용"].sum() else None)
        .dropna()
        .sort_values()
    )
    warn = camp_roas[camp_roas < ROAS_GOOD]
    if warn.empty:
        st.success("모든 캠페인 ROAS 양호 (≥4.0)")
    else:
        st.markdown("**⚠️ 주의 캠페인**")
        for camp, roas in warn.items():
            s = "개선필요" if roas < ROAS_WATCH else "관찰"
            emoji = _STATUS_EMOJI[s]
            color = _STATUS_COLOR[s]
            st.markdown(
                f"<div style='background:{color}11;border-left:3px solid {color};"
                f"padding:8px 12px;border-radius:4px;margin:4px 0'>"
                f"{emoji} <b>{camp}</b> — ROAS {roas:.2f}</div>",
                unsafe_allow_html=True,
            )
```

- [ ] **Step 2: 임포트 검증 (앱 실행 없이)**

```bash
python -c "from tabs.summary import render; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: 커밋**

```bash
git add tabs/summary.py
git commit -m "feat: 탭1 오늘 요약 (KPI 카드 + 신호등 + 주의 캠페인)"
```

---

## Task 4: 탭2 — 트렌드 (tabs/trend.py)

**Files:**
- Create: `tabs/trend.py`

- [ ] **Step 1: trend.py 작성**

```python
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_loader import CHANNEL_COLORS


def render(df: pd.DataFrame):
    metric_map = {
        "ROAS": ("구매매출", "비용", "roas"),
        "비용": ("비용", None, "sum"),
        "매출": ("구매매출", None, "sum"),
        "가입수": ("af_회원가입", None, "sum"),
        "구매수": ("구매", None, "sum"),
    }
    col1, col2 = st.columns([2, 1])
    with col1:
        sel_metric = st.selectbox("지표", list(metric_map.keys()), key="trend_metric")
    with col2:
        split_weekday = st.toggle("평일/주말 분리", key="trend_split")

    # 채널별 주간 트렌드
    st.subheader("채널별 ROAS 주간 추이 (최근 4주)")
    week_df = df.copy()
    week_df["주차"] = week_df["일"].dt.to_period("W").apply(lambda p: p.start_time)
    week_roas = (
        week_df.groupby(["주차", "채널"])
        .apply(lambda x: x["구매매출"].sum() / x["비용"].sum() if x["비용"].sum() else None)
        .reset_index(name="ROAS")
        .dropna()
    )
    week_roas = week_roas[week_roas["주차"] >= week_roas["주차"].max() - pd.Timedelta(weeks=3)]
    color_map = {ch: CHANNEL_COLORS.get(ch, "#aaa") for ch in week_roas["채널"].unique()}
    fig_week = px.line(
        week_roas, x="주차", y="ROAS", color="채널",
        color_discrete_map=color_map, markers=True,
        title="채널별 주간 ROAS"
    )
    fig_week.add_hline(y=4.0, line_dash="dash", line_color="#2ecc71", annotation_text="양호 기준 4.0")
    fig_week.add_hline(y=2.0, line_dash="dash", line_color="#e74c3c", annotation_text="개선필요 기준 2.0")
    st.plotly_chart(fig_week, use_container_width=True)

    # 일별 트렌드 (선택 지표)
    st.subheader(f"일별 {sel_metric} 추이")
    daily = df.copy()
    if split_weekday:
        daily["구분"] = daily["일"].dt.dayofweek.apply(lambda d: "주말" if d >= 5 else "평일")
        group_cols = ["일", "채널", "구분"]
    else:
        group_cols = ["일", "채널"]

    y_col, denom_col, mode = metric_map[sel_metric]
    if mode == "roas":
        daily_grp = daily.groupby(group_cols).apply(
            lambda x: x[y_col].sum() / x[denom_col].sum() if x[denom_col].sum() else None
        ).reset_index(name=sel_metric).dropna()
    else:
        daily_grp = daily.groupby(group_cols)[y_col].sum().reset_index()
        daily_grp = daily_grp.rename(columns={y_col: sel_metric})

    color_col = "구분" if split_weekday else "채널"
    fig_daily = px.line(
        daily_grp, x="일", y=sel_metric, color=color_col,
        facet_col="채널" if split_weekday else None,
        markers=True, title=f"일별 {sel_metric}"
    )
    st.plotly_chart(fig_daily, use_container_width=True)

    # 전체 일별 비용·매출·ROAS (콤보 차트)
    st.subheader("전체 일별 비용·매출·ROAS")
    total = df.groupby("일").agg(비용=("비용", "sum"), 매출=("구매매출", "sum")).reset_index()
    total["ROAS"] = total["매출"] / total["비용"]
    fig_combo = go.Figure()
    fig_combo.add_trace(go.Bar(x=total["일"], y=total["비용"], name="비용", marker_color="#3498db"))
    fig_combo.add_trace(go.Bar(x=total["일"], y=total["매출"], name="매출", marker_color="#2ecc71"))
    fig_combo.add_trace(go.Scatter(
        x=total["일"], y=total["ROAS"], name="ROAS",
        mode="lines+markers", yaxis="y2", line=dict(color="#e74c3c", width=2)
    ))
    fig_combo.update_layout(
        barmode="group",
        yaxis=dict(title="금액(₩)"),
        yaxis2=dict(overlaying="y", side="right", title="ROAS"),
    )
    st.plotly_chart(fig_combo, use_container_width=True)
```

- [ ] **Step 2: 임포트 검증**

```bash
python -c "from tabs.trend import render; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: 커밋**

```bash
git add tabs/trend.py
git commit -m "feat: 탭2 트렌드 (채널별 주간 ROAS + 일별 지표 + 평일/주말 분리)"
```

---

## Task 5: 탭3 — 소재 분석 (tabs/creative.py)

**Files:**
- Create: `tabs/creative.py`

- [ ] **Step 1: creative.py 작성**

```python
import streamlit as st
import pandas as pd
import plotly.express as px

MIN_IMPRESSION = 100_000  # A/B 판정 최소 노출


def _ab_summary(df: pd.DataFrame) -> pd.DataFrame:
    """소재AB가 있는 행만 모아 A vs B 집계."""
    ab_df = df[df["소재AB"].notna()].copy()
    if ab_df.empty:
        return pd.DataFrame()
    grp = ab_df.groupby(["채널", "소재카테고리", "소재AB"]).agg(
        노출=("노출", "sum"),
        클릭=("클릭", "sum"),
        비용=("비용", "sum"),
        구매매출=("구매매출", "sum"),
        구매=("구매", "sum"),
    ).reset_index()
    grp["CTR(%)"] = (grp["클릭"] / grp["노출"] * 100).round(2)
    grp["CVR(%)"] = (grp["구매"] / grp["클릭"] * 100).round(2)
    grp["ROAS"] = (grp["구매매출"] / grp["비용"]).round(2)
    grp["샘플"] = grp["노출"].apply(lambda x: "✅ 충분" if x >= MIN_IMPRESSION else "⚠️ 부족")
    return grp


def render(df: pd.DataFrame):
    # 필터
    col1, col2, col3 = st.columns(3)
    with col1:
        channels = ["전체"] + sorted(df["채널"].dropna().unique().tolist())
        sel_ch = st.selectbox("채널", channels, key="cr_ch")
    with col2:
        seasons = ["전체"] + sorted(df["소재시즌"].dropna().unique().tolist())
        sel_season = st.selectbox("시즌", seasons, key="cr_season")
    with col3:
        cats = ["전체"] + sorted(df["소재카테고리"].dropna().unique().tolist())
        sel_cat = st.selectbox("카테고리", cats, key="cr_cat")

    cdf = df.copy()
    if sel_ch != "전체":
        cdf = cdf[cdf["채널"] == sel_ch]
    if sel_season != "전체":
        cdf = cdf[cdf["소재시즌"] == sel_season]
    if sel_cat != "전체":
        cdf = cdf[cdf["소재카테고리"] == sel_cat]

    # 소재 타입별 성과
    st.subheader("소재 타입별 성과")
    type_grp = cdf.groupby("소재유형").agg(
        노출=("노출", "sum"), 클릭=("클릭", "sum"),
        비용=("비용", "sum"), 구매매출=("구매매출", "sum"), 구매=("구매", "sum"),
    ).reset_index()
    type_grp["CTR(%)"] = (type_grp["클릭"] / type_grp["노출"] * 100).round(2)
    type_grp["CVR(%)"] = (type_grp["구매"] / type_grp["클릭"] * 100).round(2)
    type_grp["ROAS"] = (type_grp["구매매출"] / type_grp["비용"]).round(2)

    col_l, col_r = st.columns(2)
    with col_l:
        fig_roas = px.bar(
            type_grp.sort_values("ROAS", ascending=True),
            x="ROAS", y="소재유형", orientation="h",
            color="ROAS", color_continuous_scale="Blues",
            title="소재 타입별 ROAS"
        )
        st.plotly_chart(fig_roas, use_container_width=True)
    with col_r:
        fig_ctr = px.bar(
            type_grp.sort_values("CTR(%)", ascending=True),
            x="CTR(%)", y="소재유형", orientation="h",
            color="CTR(%)", color_continuous_scale="Greens",
            title="소재 타입별 CTR"
        )
        st.plotly_chart(fig_ctr, use_container_width=True)

    # A/B 판정
    st.subheader("A/B 소재 비교")
    ab = _ab_summary(cdf)
    if ab.empty:
        st.info("선택 조건에서 A/B 소재 데이터가 없습니다.")
    else:
        st.dataframe(
            ab[["채널", "소재카테고리", "소재AB", "노출", "CTR(%)", "CVR(%)", "ROAS", "샘플"]],
            use_container_width=True, hide_index=True,
        )

    # 전체 소재 랭킹
    st.subheader("소재 전체 랭킹 (ROAS 기준)")
    rank = cdf.groupby(["채널", "캠페인", "소재유형", "소재카테고리", "소재시즌", "소재AB", "소재"]).agg(
        노출=("노출", "sum"), 클릭=("클릭", "sum"),
        비용=("비용", "sum"), 구매매출=("구매매출", "sum"), 구매=("구매", "sum"),
    ).reset_index()
    rank["CTR(%)"] = (rank["클릭"] / rank["노출"] * 100).round(2)
    rank["CVR(%)"] = (rank["구매"] / rank["클릭"] * 100).round(2)
    rank["ROAS"] = (rank["구매매출"] / rank["비용"]).round(2)
    rank["CPA"] = (rank["비용"] / rank["구매"]).round(0)
    st.dataframe(
        rank[["채널", "소재유형", "소재카테고리", "소재시즌", "소재AB", "노출", "CTR(%)", "CVR(%)", "ROAS", "CPA"]]
        .sort_values("ROAS", ascending=False),
        use_container_width=True, hide_index=True,
    )
```

- [ ] **Step 2: 임포트 검증**

```bash
python -c "from tabs.creative import render; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: 커밋**

```bash
git add tabs/creative.py
git commit -m "feat: 탭3 소재 분석 (타입별 성과 + A/B 판정 + 전체 랭킹)"
```

---

## Task 6: 탭4 — 보고서 (tabs/report.py)

**Files:**
- Create: `tabs/report.py`

- [ ] **Step 1: report.py 작성**

```python
import streamlit as st
import pandas as pd
import io
from data_loader import ROAS_GOOD, ROAS_WATCH


def _build_summary(df: pd.DataFrame, group_by: str) -> pd.DataFrame:
    grp = df.groupby(group_by).agg(
        비용=("비용", "sum"),
        매출=("구매매출", "sum"),
        노출=("노출", "sum"),
        클릭=("클릭", "sum"),
        구매=("구매", "sum"),
        가입=("af_회원가입", "sum"),
    ).reset_index()
    grp["ROAS"] = (grp["매출"] / grp["비용"]).round(2)
    grp["CPA"] = (grp["비용"] / grp["구매"]).round(0)
    grp["가입_CPA"] = (grp["비용"] / grp["가입"]).round(0)
    grp["CTR(%)"] = (grp["클릭"] / grp["노출"] * 100).round(2)
    return grp.sort_values("ROAS", ascending=False)


def _auto_comment(df: pd.DataFrame, group_by: str) -> str:
    summary = _build_summary(df, group_by)
    lines = []

    best = summary.iloc[0]
    lines.append(f"✅ 최상위 {group_by}: {best[group_by]} — ROAS {best['ROAS']:.2f}")

    warn = summary[summary["ROAS"] < ROAS_WATCH]
    for _, row in warn.iterrows():
        lines.append(f"🔴 {row[group_by]} ROAS {row['ROAS']:.2f} — 개선 필요")

    watch = summary[(summary["ROAS"] >= ROAS_WATCH) & (summary["ROAS"] < ROAS_GOOD)]
    for _, row in watch.iterrows():
        lines.append(f"🟡 {row[group_by]} ROAS {row['ROAS']:.2f} — 관찰 필요")

    total_cost = df["비용"].sum()
    total_rev = df["구매매출"].sum()
    total_roas = total_rev / total_cost if total_cost else 0
    lines.append(f"\n📊 전체 ROAS: {total_roas:.2f} | 총 비용: ₩{total_cost/1e4:.0f}만 | 총 매출: ₩{total_rev/1e4:.0f}만")

    return "\n".join(lines)


def _to_csv(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")
    return buf.getvalue()


def render(df: pd.DataFrame):
    col1, col2 = st.columns(2)
    with col1:
        group_by = st.selectbox("집계 기준", ["채널", "캠페인", "캠페인목적", "소재유형"], key="rpt_group")
    with col2:
        purposes = ["전체"] + sorted(df["캠페인목적"].dropna().unique().tolist()) if "캠페인목적" in df.columns else ["전체"]
        sel_purpose = st.selectbox("캠페인 목적 필터", purposes, key="rpt_purpose")

    rdf = df.copy()
    if sel_purpose != "전체" and "캠페인목적" in rdf.columns:
        rdf = rdf[rdf["캠페인목적"] == sel_purpose]

    summary = _build_summary(rdf, group_by)
    st.subheader("집계 테이블")
    st.dataframe(summary, use_container_width=True, hide_index=True)

    st.subheader("자동 성과 코멘트")
    comment = _auto_comment(rdf, group_by)
    st.code(comment, language=None)
    st.button("📋 코멘트 복사", on_click=lambda: st.write("복사됨"), key="copy_btn")

    st.markdown("---")
    csv_bytes = _to_csv(summary)
    st.download_button(
        label="📥 CSV 다운로드 (엑셀용)",
        data=csv_bytes,
        file_name=f"report_{group_by}.csv",
        mime="text/csv",
    )
```

- [ ] **Step 2: 임포트 검증**

```bash
python -c "from tabs.report import render; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: 커밋**

```bash
git add tabs/report.py
git commit -m "feat: 탭4 보고서 (집계 테이블 + 자동 코멘트 + CSV 다운로드)"
```

---

## Task 7: 탭5 — AF 검증 (tabs/af_verify.py)

**Files:**
- Create: `tabs/af_verify.py`

- [ ] **Step 1: af_verify.py 작성**

```python
import streamlit as st
import pandas as pd
import plotly.express as px


_COVERAGE_OK = (70, 90)  # CLAUDE.md §5-1 정상 범위


def _coverage_status(pct: float) -> tuple[str, str]:
    if _COVERAGE_OK[0] <= pct <= _COVERAGE_OK[1]:
        return "✅ 정상", "#2ecc71"
    elif pct < _COVERAGE_OK[0]:
        return "⚠️ 낮음", "#e74c3c"
    else:
        return "⚠️ 높음 (오버카운팅?)", "#f39c12"


def _quality_checks(df: pd.DataFrame) -> list[tuple[str, str, str]]:
    """CLAUDE.md §7-3 품질 체크리스트. (항목, 상태, 설명) 리스트 반환."""
    checks = []

    # 결측치
    zero_cost = (df["비용"] == 0).sum()
    checks.append((
        "비용/노출 0인 행",
        "✅ OK" if zero_cost == 0 else f"⚠️ {zero_cost}행",
        f"비용=0 행 {zero_cost}개",
    ))

    # 중복
    key_cols = ["일", "채널", "캠페인", "그룹", "소재"]
    dupes = df.duplicated(subset=key_cols).sum()
    checks.append((
        "키 중복",
        "✅ OK" if dupes == 0 else f"⚠️ {dupes}건",
        f"(일·채널·캠페인·그룹·소재) 중복 {dupes}건",
    ))

    # 음수 매출
    neg_rev = (df["구매매출"] < 0).sum()
    checks.append((
        "음수 매출",
        "✅ OK" if neg_rev == 0 else f"⚠️ {neg_rev}행",
        f"환불 포함 가능성 {neg_rev}건",
    ))

    # 이상치 비용 (평균 + 3σ)
    mean, std = df["비용"].mean(), df["비용"].std()
    outliers = (df["비용"] > mean + 3 * std).sum()
    checks.append((
        "비용 이상치 (3σ)",
        "✅ OK" if outliers == 0 else f"⚠️ {outliers}행",
        f"평균 {mean:,.0f} + 3σ 초과 {outliers}건",
    ))

    return checks


def render(df: pd.DataFrame):
    if "af_회원가입" not in df.columns or df["af_회원가입"].isna().all():
        st.info("AppsFlyer 데이터가 없습니다. data/raw/appsflyer/ 폴더에 파일을 추가하세요.")
        return

    # 커버리지
    st.subheader("채널별 AF 커버리지")
    ch_cov = df.groupby("채널").agg(
        채널_가입=("회원가입", "sum"),
        af_가입=("af_회원가입", "sum"),
        채널_클릭=("클릭", "sum"),
        af_클릭=("af_클릭", "sum"),
        채널_구매=("구매", "sum"),
        af_구매=("af_구매", "sum"),
        채널_ROAS=("ROAS", "mean"),
        af_ROAS=("AF_ROAS", "mean"),
        비용=("비용", "sum"),
    ).reset_index()
    ch_cov["커버리지(%)"] = (ch_cov["af_가입"] / ch_cov["채널_가입"] * 100).round(1)
    ch_cov["가입갭(%)"] = ((ch_cov["af_가입"] - ch_cov["채널_가입"]) / ch_cov["채널_가입"] * 100).round(1)

    for _, row in ch_cov.iterrows():
        cov = row["커버리지(%)"]
        status, color = _coverage_status(cov)
        st.markdown(
            f"<div style='background:{color}11;border-left:4px solid {color};"
            f"padding:10px 16px;border-radius:6px;margin:4px 0'>"
            f"<b>{row['채널']}</b> — 커버리지 {cov:.1f}% {status}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.subheader("채널 보고 vs AF 비교")
    disp = ch_cov[["채널", "채널_가입", "af_가입", "커버리지(%)", "가입갭(%)",
                    "채널_구매", "af_구매", "채널_ROAS", "af_ROAS"]]
    st.dataframe(disp.rename(columns={"채널_ROAS": "채널_ROAS(avg)", "af_ROAS": "AF_ROAS(avg)"}),
                 use_container_width=True, hide_index=True)

    fig = px.bar(
        ch_cov, x="채널", y=["채널_가입", "af_가입"], barmode="group",
        title="채널 보고 가입 vs AF 가입",
        color_discrete_sequence=["#3498db", "#e67e22"],
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("데이터 품질 체크리스트 (CLAUDE.md §7-3)")
    checks = _quality_checks(df)
    for item, status, desc in checks:
        color = "#2ecc71" if "OK" in status else "#e74c3c"
        st.markdown(
            f"<div style='display:flex;gap:12px;padding:8px 0;border-bottom:1px solid #2d3748'>"
            f"<span style='color:{color};font-weight:700;min-width:120px'>{status}</span>"
            f"<span><b>{item}</b> — {desc}</span></div>",
            unsafe_allow_html=True,
        )
```

- [ ] **Step 2: 임포트 검증**

```bash
python -c "from tabs.af_verify import render; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: 커밋**

```bash
git add tabs/af_verify.py
git commit -m "feat: 탭5 AF 검증 (커버리지 + 갭 비교 + 품질 체크리스트)"
```

---

## Task 8: dashboard.py 5탭 구조로 교체

**Files:**
- Modify: `dashboard.py`

- [ ] **Step 1: dashboard.py 전체 교체**

```python
import streamlit as st
from data_loader import load_merged, BRAND_KW_CAMPAIGN
from tabs import summary, trend, creative, report, af_verify

st.set_page_config(page_title="퍼포먼스 마케팅 대시보드", layout="wide")
st.title("📊 퍼포먼스 마케팅 대시보드")


@st.cache_data(ttl=0)
def get_data():
    return load_merged()


df = get_data()

if df.empty:
    st.error("데이터 없음 — data/raw/channel/ 에 CSV를 추가하세요.")
    st.stop()

# ── 공통 사이드바 필터 ─────────────────────────────────────────────
with st.sidebar:
    st.header("필터")

    date_min = df["일"].min().date()
    date_max = df["일"].max().date()
    date_range = st.date_input("날짜 범위", value=(date_min, date_max),
                               min_value=date_min, max_value=date_max)
    start, end = (date_range[0], date_range[1]) if len(date_range) == 2 else (date_min, date_max)

    channels = ["전체"] + sorted(df["채널"].dropna().unique().tolist())
    sel_ch = st.multiselect("채널", channels[1:], default=channels[1:])

    exclude_brand_kw = st.toggle("브랜드KW 제외 (NVR_CMP_01)", value=False)
    exclude_naver = st.toggle("자체매체(네이버) 제외", value=False)

# ── 필터 적용 ─────────────────────────────────────────────────────
mask = (df["일"].dt.date >= start) & (df["일"].dt.date <= end)
if sel_ch:
    mask &= df["채널"].isin(sel_ch)
if exclude_brand_kw:
    mask &= df["캠페인"] != BRAND_KW_CAMPAIGN
if exclude_naver:
    mask &= df["채널"] != "네이버"

fdf = df[mask]

if fdf.empty:
    st.warning("필터 조건에 맞는 데이터가 없습니다.")
    st.stop()

# ── 탭 라우팅 ─────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 오늘 요약", "📈 트렌드", "🎨 소재 분석", "📋 보고서", "🔗 AF 검증"
])

with tab1:
    summary.render(fdf)
with tab2:
    trend.render(fdf)
with tab3:
    creative.render(fdf)
with tab4:
    report.render(fdf)
with tab5:
    af_verify.render(fdf)
```

- [ ] **Step 2: 앱 실행 확인**

```bash
streamlit run dashboard.py --server.port 8502
```

브라우저에서 `http://localhost:8502` 열어서 5개 탭이 모두 표시되는지 확인.

- [ ] **Step 3: 각 탭 기능 점검**

- [ ] 탭1: KPI 카드 4개 + 채널 신호등 + 주의 캠페인 표시
- [ ] 탭2: 주간 ROAS 라인 차트 + 일별 콤보 차트 렌더링
- [ ] 탭3: 소재 타입별 바차트 + 랭킹 테이블
- [ ] 탭4: 집계 테이블 + 코멘트 텍스트 + CSV 다운로드 버튼
- [ ] 탭5: 커버리지 표시 (AF 데이터 없으면 안내 메시지)

- [ ] **Step 4: 커밋**

```bash
git add dashboard.py
git commit -m "feat: dashboard 5탭 구조 완성 (오늘 요약/트렌드/소재/보고서/AF 검증)"
```
