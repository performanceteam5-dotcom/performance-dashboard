# 무신사 리포트 대시보드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** RD CSV를 사이드바에서 업로드하면 무탠유입 탭의 세그먼트×상세구분 KPI를 자동 집계하고, 버튼 하나로 슬랙용 코멘트 초안을 생성하는 Streamlit 대시보드를 만든다.

**Architecture:** `musinsa_report.py` (Streamlit 진입점) → `rd_loader.py` (CSV 파싱·KPI 계산 순수 함수) → `comment_generator.py` (코멘트 텍스트 생성 순수 함수) → `tabs/mutandard.py`, `tabs/active_customer.py` (탭별 UI). 기존 `dashboard.py`·`data_loader.py`는 건드리지 않는다.

**Tech Stack:** Python 3.11+, Streamlit ≥ 1.30, pandas ≥ 2.0, pytest

---

## File Map

| 파일 | 역할 |
|---|---|
| `rd_loader.py` | CSV 로딩, KPI(광고비·활성CPU·고활성CPU·저활성CPU) 계산 순수 함수 |
| `comment_generator.py` | 파트별 코멘트 텍스트 조립 순수 함수 |
| `tabs/mutandard.py` | 📦 무탠유입 탭 UI |
| `tabs/active_customer.py` | 🎯 활성고객 탭 UI |
| `musinsa_report.py` | Streamlit 앱 진입점 (사이드바·탭 라우팅) |
| `tests/test_rd_loader.py` | rd_loader 단위 테스트 |
| `tests/test_comment_generator.py` | comment_generator 단위 테스트 |

---

## Task 1: rd_loader.py — 데이터 로딩 및 KPI 계산

**Files:**
- Create: `rd_loader.py`
- Create: `tests/test_rd_loader.py`

### 컬럼 상수 (실제 CSV 기준)

| 상수 | 실제 컬럼명 |
|---|---|
| `COL_DATE` | `일` |
| `COL_PART` | `종료일자` |
| `COL_SEG` | `캠페인/구분` |
| `COL_DETAIL` | `상세구분` |
| `COL_MEDIA` | `매체` |
| `COL_COST` | `광고비_Fee포함` |
| `COL_ACTIVE` | `GA_활성사용자수` |
| `COL_HIGH` | `GA_고활성사용자수` |
| `COL_LOW` | `GA_저활성사용자수` |

- [ ] **Step 1: 테스트 먼저 작성**

```python
# tests/test_rd_loader.py
import pandas as pd
import pytest
from rd_loader import load_rd, calc_cpu, agg_kpi, get_prev_date, COL_DATE

def _make_df(rows):
    """테스트용 미니 DataFrame 생성 헬퍼."""
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
```

- [ ] **Step 2: 테스트 실행 — FAIL 확인**

```
cd C:\Users\MADUP\Desktop\clade_0514
pytest tests/test_rd_loader.py -v
```
Expected: `ModuleNotFoundError: No module named 'rd_loader'`

- [ ] **Step 3: rd_loader.py 구현**

```python
# rd_loader.py
from __future__ import annotations
import glob
import os
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
    'Facebook': '메타',
    'Kakao':    '카카오',
    'KAKAO':    '카카오',
    'tiktok':   '틱톡',
    'moloco':   '몰로코',
    'appier':   '에피어',
    'cauly_int':'카울리',
    'carrot':   '당근',
    'toss_rw':  '토스',
    'adisonofferwall_rw': '애디슨',
    'cookieoven_rw':      '쿠키오븐',
}

PART_MUTANDARD  = '무탠다드유입'
PART_ACTIVE_CUS = '활성고객'

# 기획전+상시를 합산해서 보여줄 세그먼트
MERGED_DETAIL_SEGS = {'무탠다드맨', '무탠다드우먼'}
MERGED_LABELS      = ('기획전', '상시')


def load_rd(path: str) -> pd.DataFrame:
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


def delta_pct(curr: int | None, prev: int | None) -> float | None:
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
```

- [ ] **Step 4: 테스트 실행 — PASS 확인**

```
pytest tests/test_rd_loader.py -v
```
Expected: 모두 PASSED

- [ ] **Step 5: 커밋**

```
git add rd_loader.py tests/test_rd_loader.py
git commit -m "feat: rd_loader — RD CSV 로딩 및 KPI 계산"
```

---

## Task 2: comment_generator.py — 무탠유입 코멘트 생성

**Files:**
- Create: `comment_generator.py`
- Create: `tests/test_comment_generator.py`

- [ ] **Step 1: 테스트 먼저 작성**

```python
# tests/test_comment_generator.py
import pandas as pd
from comment_generator import (
    format_won, format_cpu, build_mutandard_comment,
)

def test_format_won_man():
    assert format_won(16_900_000) == '1,690만원'

def test_format_won_eok():
    assert format_won(100_000_000) == '1억원'

def test_format_won_mixed():
    assert format_won(176_170_000) == '1억 7,617만원'

def test_format_cpu():
    assert format_cpu(112) == '112원'
    assert format_cpu(None) == '—'

def _make_part_df():
    rows = []
    # 무탠다드맨 — 기획전
    rows.append({'일': '2026-05-14', '캠페인/구분': '무탠다드맨', '상세구분': '기획전',
                 '광고비_Fee포함': 2_000_000, 'GA_활성사용자수': 20000,
                 'GA_고활성사용자수': 16000, 'GA_저활성사용자수': 4000, '매체_표기': '메타'})
    # 무탠다드맨 — 상시
    rows.append({'일': '2026-05-14', '캠페인/구분': '무탠다드맨', '상세구분': '상시',
                 '광고비_Fee포함': 1_000_000, 'GA_활성사용자수': 10000,
                 'GA_고활성사용자수': 8000, 'GA_저활성사용자수': 2000, '매체_표기': '카카오'})
    # 무탠다드맨 — 캠페인
    rows.append({'일': '2026-05-14', '캠페인/구분': '무탠다드맨', '상세구분': '캠페인',
                 '광고비_Fee포함': 3_000_000, 'GA_활성사용자수': 10000,
                 'GA_고활성사용자수': 8000, 'GA_저활성사용자수': 2000, '매체_표기': '메타'})
    # 무탠다드통합 — 카탈로그
    rows.append({'일': '2026-05-14', '캠페인/구분': '무탠다드통합', '상세구분': '카탈로그',
                 '광고비_Fee포함': 6_000_000, 'GA_활성사용자수': 54000,
                 'GA_고활성사용자수': 43000, 'GA_저활성사용자수': 11000, '매체_표기': '카카오'})
    df = pd.DataFrame(rows)
    df['일'] = pd.to_datetime(df['일'])
    return df

def test_build_mutandard_comment_contains_header():
    df = _make_part_df()
    month_df = df.copy()
    comment = build_mutandard_comment(df, pd.Timestamp('2026-05-14'), month_df)
    assert '#무탠유입' in comment

def test_build_mutandard_comment_segment_headers():
    df = _make_part_df()
    month_df = df.copy()
    comment = build_mutandard_comment(df, pd.Timestamp('2026-05-14'), month_df)
    assert '[무탠다드맨]' in comment
    assert '[무탠다드통합]' in comment

def test_build_mutandard_comment_detail_headers():
    df = _make_part_df()
    month_df = df.copy()
    comment = build_mutandard_comment(df, pd.Timestamp('2026-05-14'), month_df)
    assert '기획전+상시' in comment
    assert '캠페인' in comment
    assert '카탈로그' in comment

def test_build_mutandard_comment_no_split_for_integrated():
    """무탠다드통합은 '기획전+상시' 항목이 코멘트에 없어야 한다."""
    df = _make_part_df()
    month_df = df.copy()
    comment = build_mutandard_comment(df, pd.Timestamp('2026-05-14'), month_df)
    # 통합 섹션 이후 기획전+상시 없어야 함
    integrated_pos = comment.index('[무탠다드통합]')
    after_integrated = comment[integrated_pos:]
    assert '기획전+상시' not in after_integrated
```

- [ ] **Step 2: 테스트 실행 — FAIL 확인**

```
pytest tests/test_comment_generator.py -v
```
Expected: `ModuleNotFoundError: No module named 'comment_generator'`

- [ ] **Step 3: comment_generator.py 구현**

```python
# comment_generator.py
from __future__ import annotations
import pandas as pd
from rd_loader import (
    agg_kpi, COL_SEG, COL_DETAIL, COL_DATE,
    MERGED_DETAIL_SEGS, MERGED_LABELS,
    COL_COST, COL_ACTIVE, COL_HIGH, COL_LOW,
)

SEGMENT_ORDER = ['무탠다드맨', '무탠다드우먼', '무탠다드통합']


def format_won(amount: float) -> str:
    eok  = int(amount) // 100_000_000
    man  = (int(amount) % 100_000_000) // 10_000
    if eok > 0 and man > 0:
        return f'{eok}억 {man:,}만원'
    if eok > 0:
        return f'{eok}억원'
    return f'{man:,}만원'


def format_cpu(cpu: int | None) -> str:
    if cpu is None:
        return '—'
    return f'{cpu:,}원'


def _kpi_line(kpi: dict) -> str:
    cost = format_won(kpi['광도비']) if kpi.get('광도비') else format_won(kpi['광고비'])
    return (
        f"- 전일 광고비 {format_won(kpi['광고비'])}, "
        f"활성CPU {format_cpu(kpi['활성CPU'])}, "
        f"고활성CPU {format_cpu(kpi['고활성CPU'])}, "
        f"저활성CPU {format_cpu(kpi['저활성CPU'])}"
    )


def _month_kpi_line(kpi: dict) -> str:
    month_name = '5월'  # 기준월은 데이터 최신 날짜에서 추출하는 게 이상적이나, 호출측에서 넘김
    return (
        f"- {month_name} 누적 광고비 {format_won(kpi['광고비'])}, "
        f"활성CPU {format_cpu(kpi['활성CPU'])}, "
        f"고활성CPU {format_cpu(kpi['고활성CPU'])}, "
        f"저활성CPU {format_cpu(kpi['저활성CPU'])}"
    )


def build_mutandard_comment(
    day_df: pd.DataFrame,
    target_date: pd.Timestamp,
    month_df: pd.DataFrame,
) -> str:
    """
    day_df   : 기준일 무탠유입 전체 행
    month_df : 당월 누적 무탠유입 전체 행
    """
    lines: list[str] = []

    # ── 파트 헤더 ──────────────────────────────────────────
    month_kpi = agg_kpi(month_df)
    day_kpi   = agg_kpi(day_df)
    month_name = target_date.strftime('%-m월') if hasattr(target_date, 'strftime') else '5월'

    lines.append('#무탠유입')
    lines.append(
        f"- {month_name} 누적 광고비 {format_won(month_kpi['광고비'])}, "
        f"활성CPU {format_cpu(month_kpi['활성CPU'])}, "
        f"고활성CPU {format_cpu(month_kpi['고활성CPU'])}, "
        f"저활성CPU {format_cpu(month_kpi['저활성CPU'])}"
    )
    lines.append(
        f"- 전일 광고비 {format_won(day_kpi['광고비'])}, "
        f"활성CPU {format_cpu(day_kpi['활성CPU'])}, "
        f"고활성CPU {format_cpu(day_kpi['고활성CPU'])}, "
        f"저활성CPU {format_cpu(day_kpi['저활성CPU'])}"
    )

    # ── 세그먼트별 ────────────────────────────────────────
    for seg in SEGMENT_ORDER:
        seg_df = day_df[day_df[COL_SEG] == seg]
        if seg_df.empty:
            continue

        lines.append('')
        lines.append(f'[{seg}]')

        if seg in MERGED_DETAIL_SEGS:
            # 기획전+상시 합산
            merged_df = seg_df[seg_df[COL_DETAIL].isin(MERGED_LABELS)]
            if not merged_df.empty:
                kpi = agg_kpi(merged_df)
                lines.append('기획전+상시')
                lines.append(
                    f"- 전일 광고비 {format_won(kpi['광고비'])}, "
                    f"활성CPU {format_cpu(kpi['활성CPU'])}, "
                    f"고활성CPU {format_cpu(kpi['고활성CPU'])}, "
                    f"저활성CPU {format_cpu(kpi['저활성CPU'])}"
                )

            # 캠페인
            camp_df = seg_df[seg_df[COL_DETAIL] == '캠페인']
            if not camp_df.empty:
                kpi = agg_kpi(camp_df)
                lines.append('캠페인')
                lines.append(
                    f"- 전일 광고비 {format_won(kpi['광고비'])}, "
                    f"활성CPU {format_cpu(kpi['활성CPU'])}, "
                    f"고활성CPU {format_cpu(kpi['고활성CPU'])}, "
                    f"저활성CPU {format_cpu(kpi['저활성CPU'])}"
                )
        else:
            # 무탠다드통합: 카탈로그
            cat_df = seg_df[seg_df[COL_DETAIL] == '카탈로그']
            if not cat_df.empty:
                kpi = agg_kpi(cat_df)
                lines.append('카탈로그')
                lines.append(
                    f"- 전일 광고비 {format_won(kpi['광고비'])}, "
                    f"활성CPU {format_cpu(kpi['활성CPU'])}, "
                    f"고활성CPU {format_cpu(kpi['고활성CPU'])}, "
                    f"저활성CPU {format_cpu(kpi['저활성CPU'])}"
                )

    return '\n'.join(lines)
```

> **버그 주의**: `_kpi_line` 함수 내 `광도비` 오타 있음. 실제 구현 시 그대로 쓰지 말고 `build_mutandard_comment` 내 인라인 방식처럼 `kpi['광고비']`로 직접 사용할 것. `_kpi_line` 헬퍼는 삭제해도 됨.

- [ ] **Step 4: 테스트 실행 — PASS 확인**

```
pytest tests/test_comment_generator.py -v
```
Expected: 모두 PASSED

- [ ] **Step 5: 커밋**

```
git add comment_generator.py tests/test_comment_generator.py
git commit -m "feat: comment_generator — 무탠유입 코멘트 조립"
```

---

## Task 3: tabs/mutandard.py — 무탠유입 탭 UI

**Files:**
- Create: `tabs/mutandard.py`

- [ ] **Step 1: tabs/mutandard.py 작성**

```python
# tabs/mutandard.py
from __future__ import annotations
import pandas as pd
import streamlit as st

from rd_loader import (
    agg_kpi, delta_pct, delta_label, delta_status,
    get_prev_date, format_won_alias,
    COL_DATE, COL_SEG, COL_DETAIL, COL_PART,
    PART_MUTANDARD, MERGED_DETAIL_SEGS, MERGED_LABELS,
)
from comment_generator import build_mutandard_comment, format_won, format_cpu

SEGMENT_ORDER  = ['무탠다드맨', '무탠다드우먼', '무탠다드통합']
SEGMENT_EMOJI  = {'무탠다드맨': '🔵', '무탠다드우먼': '🔴', '무탠다드통합': '🟢'}
SEGMENT_BG     = {'무탠다드맨': '#eef3fb', '무탠다드우먼': '#fdf2fb', '무탠다드통합': '#eefaf3'}

_BADGE = {
    'good': '<span style="background:#dcfce7;color:#16a34a;border-radius:8px;'
            'padding:1px 8px;font-size:11px;font-weight:700">▼ 개선</span>',
    'bad':  '<span style="background:#fee2e2;color:#e53e3e;border-radius:8px;'
            'padding:1px 8px;font-size:11px;font-weight:700">▲ 악화</span>',
    'flat': '<span style="background:#f1f5f9;color:#64748b;border-radius:8px;'
            'padding:1px 8px;font-size:11px;font-weight:700">— 동수준</span>',
}


def _badge(pct: float | None) -> str:
    return _BADGE[delta_status(pct)]


def _cpu_color(cpu: int | None, avg: int | None) -> str:
    if cpu is None or avg is None or avg == 0:
        return ''
    if cpu < avg * 0.7:
        return 'color:#38a169;font-weight:700'
    if cpu > avg * 1.3:
        return 'color:#e53e3e;font-weight:700'
    return ''


def _render_kpi_cards(kpi: dict, prev_kpi: dict | None):
    c1, c2, c3, c4 = st.columns(4)
    for col, label, key, fmt in [
        (c1, '광고비',    '광고비',    'won'),
        (c2, '활성CPU',   '활성CPU',   'cpu'),
        (c3, '고활성CPU', '고활성CPU', 'cpu'),
        (c4, '저활성CPU', '저활성CPU', 'cpu'),
    ]:
        val  = kpi.get(key)
        prev = prev_kpi.get(key) if prev_kpi else None
        pct  = delta_pct(val, prev)
        display = format_won(val) if fmt == 'won' else format_cpu(val)
        col.metric(label, display, delta_label(pct))


def render(full_df: pd.DataFrame):
    mt_df = full_df[full_df[COL_PART] == PART_MUTANDARD].copy()
    if mt_df.empty:
        st.info("무탠다드유입 데이터가 없습니다.")
        return

    dates        = mt_df[COL_DATE].drop_duplicates().sort_values()
    target_date  = dates.max()
    prev_date    = get_prev_date(dates, target_date)

    day_df  = mt_df[mt_df[COL_DATE] == target_date]
    prev_df = mt_df[mt_df[COL_DATE] == prev_date] if prev_date is not None else pd.DataFrame()

    month_df = mt_df[
        (mt_df[COL_DATE].dt.year  == target_date.year) &
        (mt_df[COL_DATE].dt.month == target_date.month)
    ]

    # ── 날짜 헤더 ──────────────────────────────────────────
    st.markdown(
        f"<div style='font-size:18px;font-weight:700;margin-bottom:16px'>"
        f"📅 {target_date.strftime('%Y-%m-%d')} 기준 (전일 성과)</div>",
        unsafe_allow_html=True,
    )

    # ── TOTAL KPI 카드 ────────────────────────────────────
    day_kpi  = agg_kpi(day_df)
    prev_kpi = agg_kpi(prev_df) if not prev_df.empty else None
    _render_kpi_cards(day_kpi, prev_kpi)

    # ── 세그먼트 × 상세구분 테이블 ────────────────────────
    st.markdown("**📂 세그먼트 × 상세구분 성과**")

    header = (
        "<table style='width:100%;border-collapse:collapse;font-size:12px'>"
        "<thead><tr style='background:#f8f9fa'>"
        "<th style='padding:9px 14px;text-align:left;border-bottom:1px solid #e8e8e8'>세그먼트 / 상세구분</th>"
        "<th style='padding:9px 14px;text-align:right;border-bottom:1px solid #e8e8e8'>광고비</th>"
        "<th style='padding:9px 14px;text-align:right;border-bottom:1px solid #e8e8e8'>활성CPU</th>"
        "<th style='padding:9px 14px;text-align:right;border-bottom:1px solid #e8e8e8'>고활성CPU</th>"
        "<th style='padding:9px 14px;text-align:right;border-bottom:1px solid #e8e8e8'>저활성CPU</th>"
        "<th style='padding:9px 14px;text-align:right;border-bottom:1px solid #e8e8e8'>전일比</th>"
        "</tr></thead><tbody>"
    )
    rows_html = []

    for seg in SEGMENT_ORDER:
        seg_day  = day_df[day_df[COL_SEG] == seg]
        seg_prev = prev_df[prev_df[COL_SEG] == seg] if not prev_df.empty else pd.DataFrame()
        if seg_day.empty:
            continue

        seg_kpi  = agg_kpi(seg_day)
        prev_seg_kpi = agg_kpi(seg_prev) if not seg_prev.empty else None
        pct = delta_pct(seg_kpi['활성CPU'], prev_seg_kpi['활성CPU'] if prev_seg_kpi else None)
        bg  = SEGMENT_BG[seg]
        emoji = SEGMENT_EMOJI[seg]

        rows_html.append(
            f"<tr style='background:{bg}'>"
            f"<td style='padding:8px 14px;font-weight:700'>{emoji} {seg}</td>"
            f"<td style='padding:8px 14px;text-align:right'>{format_won(seg_kpi['광고비'])}</td>"
            f"<td style='padding:8px 14px;text-align:right'>—</td>"
            f"<td style='padding:8px 14px;text-align:right'>—</td>"
            f"<td style='padding:8px 14px;text-align:right'>—</td>"
            f"<td style='padding:8px 14px;text-align:right'>—</td>"
            f"</tr>"
        )

        # 상세구분 행
        detail_rows = _get_detail_rows(seg, seg_day, seg_prev)
        rows_html.extend(detail_rows)

    table_html = header + ''.join(rows_html) + "</tbody></table>"
    st.markdown(table_html, unsafe_allow_html=True)
    st.markdown("")

    # ── 코멘트 생성 ──────────────────────────────────────
    st.markdown("---")
    col_left, col_right = st.columns([3, 1])
    with col_left:
        st.markdown("**✍️ 무탠유입 코멘트 생성**")
        st.caption("세그먼트 3개 × 기획전+상시·캠페인 구분 · 전일 데이터 기준")
    with col_right:
        generate = st.button("코멘트 생성", type="primary", key="gen_mutandard")

    if generate or st.session_state.get('mutandard_comment'):
        if generate:
            comment = build_mutandard_comment(day_df, target_date, month_df)
            st.session_state['mutandard_comment'] = comment
        edited = st.text_area(
            "💬 무탠유입 코멘트",
            value=st.session_state['mutandard_comment'],
            height=400,
            key="mutandard_comment_area",
        )
        st.caption("✏️ 수정 후 복사해서 슬랙에 붙여넣으세요")


def _get_detail_rows(
    seg: str,
    seg_day: pd.DataFrame,
    seg_prev: pd.DataFrame,
) -> list[str]:
    rows = []

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
```

> `rd_loader.py`에 `format_won_alias` export가 없으면 import 라인에서 제거할 것 (tabs/mutandard.py는 `format_won`/`format_cpu`를 `comment_generator`에서만 import하면 됨).

- [ ] **Step 2: import 정리 — rd_loader에 없는 심볼 제거**

`tabs/mutandard.py` 상단 import에서 `format_won_alias` 제거:
```python
from rd_loader import (
    agg_kpi, delta_pct, delta_label, delta_status,
    get_prev_date,
    COL_DATE, COL_SEG, COL_DETAIL, COL_PART,
    PART_MUTANDARD, MERGED_DETAIL_SEGS, MERGED_LABELS,
)
```

- [ ] **Step 3: 커밋**

```
git add tabs/mutandard.py
git commit -m "feat: tabs/mutandard — 무탠유입 탭 UI"
```

---

## Task 4: tabs/active_customer.py — 활성고객 탭 (기본 KPI)

**Files:**
- Create: `tabs/active_customer.py`

- [ ] **Step 1: tabs/active_customer.py 작성**

```python
# tabs/active_customer.py
from __future__ import annotations
import pandas as pd
import streamlit as st

from rd_loader import (
    agg_kpi, delta_pct, delta_label, get_prev_date,
    COL_DATE, COL_SEG, COL_DETAIL, COL_PART,
    PART_ACTIVE_CUS,
)
from comment_generator import format_won, format_cpu


def render(full_df: pd.DataFrame):
    ac_df = full_df[full_df[COL_PART] == PART_ACTIVE_CUS].copy()
    if ac_df.empty:
        st.info("활성고객 데이터가 없습니다.")
        return

    dates       = ac_df[COL_DATE].drop_duplicates().sort_values()
    target_date = dates.max()
    prev_date   = get_prev_date(dates, target_date)

    day_df  = ac_df[ac_df[COL_DATE] == target_date]
    prev_df = ac_df[ac_df[COL_DATE] == prev_date] if prev_date is not None else pd.DataFrame()

    st.markdown(
        f"<div style='font-size:18px;font-weight:700;margin-bottom:16px'>"
        f"📅 {target_date.strftime('%Y-%m-%d')} 기준 (전일 성과)</div>",
        unsafe_allow_html=True,
    )

    day_kpi  = agg_kpi(day_df)
    prev_kpi = agg_kpi(prev_df) if not prev_df.empty else None

    c1, c2, c3, c4 = st.columns(4)
    for col, label, key in [
        (c1, '광고비',    '광고비'),
        (c2, '활성CPU',   '활성CPU'),
        (c3, '고활성CPU', '고활성CPU'),
        (c4, '저활성CPU', '저활성CPU'),
    ]:
        val  = day_kpi.get(key)
        prev = prev_kpi.get(key) if prev_kpi else None
        pct  = delta_pct(val, prev)
        display = format_won(val) if key == '광고비' else format_cpu(val)
        col.metric(label, display, delta_label(pct))

    st.markdown("---")

    # 상세구분별 카드
    st.markdown("**📂 상세구분별 성과**")
    details = day_df[COL_DETAIL].dropna().unique()
    if len(details) > 0:
        cols = st.columns(min(len(details), 3))
        for i, detail in enumerate(details):
            d_df = day_df[day_df[COL_DETAIL] == detail]
            kpi  = agg_kpi(d_df)
            with cols[i % 3]:
                st.markdown(
                    f"<div style='background:#fff;border:1px solid #e8e8e8;border-radius:8px;padding:12px 14px;margin-bottom:8px'>"
                    f"<div style='font-weight:700;margin-bottom:6px'>{detail}</div>"
                    f"<div style='font-size:12px;color:#555'>광고비: {format_won(kpi['광고비'])}</div>"
                    f"<div style='font-size:12px;color:#555'>활성CPU: {format_cpu(kpi['활성CPU'])}</div>"
                    f"<div style='font-size:12px;color:#555'>고활성CPU: {format_cpu(kpi['고활성CPU'])}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # 코멘트 생성 (간단 수치 나열)
    st.markdown("---")
    col_left, col_right = st.columns([3, 1])
    with col_left:
        st.markdown("**✍️ 활성고객 코멘트 생성**")
        st.caption("전일 데이터 기준 · TOTAL + 상세구분별")
    with col_right:
        generate = st.button("코멘트 생성", type="primary", key="gen_active")

    if generate or st.session_state.get('active_comment'):
        if generate:
            month_df = ac_df[
                (ac_df[COL_DATE].dt.year  == target_date.year) &
                (ac_df[COL_DATE].dt.month == target_date.month)
            ]
            month_kpi = agg_kpi(month_df)
            month_name = target_date.strftime('%-m월')

            lines = [
                '#활성고객',
                (f"- {month_name} 누적 광고비 {format_won(month_kpi['광고비'])}, "
                 f"활성CPU {format_cpu(month_kpi['활성CPU'])}, "
                 f"고활성CPU {format_cpu(month_kpi['고활성CPU'])}, "
                 f"저활성CPU {format_cpu(month_kpi['저활성CPU'])}"),
                (f"- 전일 광고비 {format_won(day_kpi['광고비'])}, "
                 f"활성CPU {format_cpu(day_kpi['활성CPU'])}, "
                 f"고활성CPU {format_cpu(day_kpi['고활성CPU'])}, "
                 f"저활성CPU {format_cpu(day_kpi['저활성CPU'])}"),
            ]
            for detail in details:
                d_df = day_df[day_df[COL_DETAIL] == detail]
                kpi  = agg_kpi(d_df)
                lines.append(f'\n{detail}')
                lines.append(
                    f"- 전일 광고비 {format_won(kpi['광고비'])}, "
                    f"활성CPU {format_cpu(kpi['활성CPU'])}, "
                    f"고활성CPU {format_cpu(kpi['고활성CPU'])}, "
                    f"저활성CPU {format_cpu(kpi['저활성CPU'])}"
                )
            st.session_state['active_comment'] = '\n'.join(lines)

        st.text_area(
            "💬 활성고객 코멘트",
            value=st.session_state['active_comment'],
            height=300,
            key="active_comment_area",
        )
        st.caption("✏️ 수정 후 복사해서 슬랙에 붙여넣으세요")
```

- [ ] **Step 2: 커밋**

```
git add tabs/active_customer.py
git commit -m "feat: tabs/active_customer — 활성고객 탭 기본 KPI"
```

---

## Task 5: musinsa_report.py — 메인 앱

**Files:**
- Create: `musinsa_report.py`

- [ ] **Step 1: musinsa_report.py 작성**

```python
# musinsa_report.py
from __future__ import annotations
import streamlit as st
import pandas as pd
from rd_loader import load_rd, COL_PART, COL_DATE, COL_MEDIA
from tabs import mutandard, active_customer

st.set_page_config(
    page_title="무신사 리포트 대시보드",
    layout="wide",
    page_icon="📦",
)

# ── 사이드바 ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 무신사 리포트")
    uploaded = st.file_uploader(
        "RD CSV 업로드",
        type=['csv'],
        help="musinsa_Total_*.csv 파일을 업로드하세요",
    )

    if uploaded is None:
        st.info("RD CSV를 업로드하면 대시보드가 표시됩니다.")
        st.stop()

    @st.cache_data(show_spinner="데이터 로딩 중...")
    def _load(file_bytes: bytes, name: str) -> pd.DataFrame:
        import io
        return load_rd(io.BytesIO(file_bytes))

    df = _load(uploaded.read(), uploaded.name)
    st.success(f"✅ {uploaded.name}")

    # 날짜 필터
    date_min = df[COL_DATE].min().date()
    date_max = df[COL_DATE].max().date()
    date_range = st.date_input(
        "날짜 범위",
        value=(date_max, date_max),
        min_value=date_min,
        max_value=date_max,
    )
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start, end = date_range
    else:
        start = end = date_max

    # 매체 필터
    all_media = sorted(df['매체_표기'].dropna().unique().tolist())
    sel_media = st.multiselect("매체", all_media, default=all_media)

# ── 필터 적용 ────────────────────────────────────────────
mask = (df[COL_DATE].dt.date >= start) & (df[COL_DATE].dt.date <= end)
if sel_media:
    mask &= df['매체_표기'].isin(sel_media)
fdf = df[mask]

if fdf.empty:
    st.warning("필터 조건에 맞는 데이터가 없습니다.")
    st.stop()

# ── 헤더 ────────────────────────────────────────────────
st.title("📊 무신사 퍼포먼스 대시보드")

# ── 탭 라우팅 ────────────────────────────────────────────
tab_active, tab_churn, tab_youth, tab_mt, tab_beauty, tab_foot = st.tabs([
    "🎯 활성고객",
    "↩️ 이탈고객",
    "👟 20대유입",
    "📦 무탠유입",
    "💄 뷰티",
    "👠 풋웨어",
])

with tab_active:
    active_customer.render(fdf)

with tab_mt:
    mutandard.render(fdf)

for tab, name in [
    (tab_churn,  "이탈고객"),
    (tab_youth,  "20대유입"),
    (tab_beauty, "뷰티"),
    (tab_foot,   "풋웨어"),
]:
    with tab:
        st.info(f"'{name}' 탭은 추후 구현 예정입니다.")
```

- [ ] **Step 2: rd_loader.py에 BytesIO 지원 추가**

`rd_loader.py`의 `load_rd` 함수를 BytesIO도 받을 수 있게 수정:

```python
import io

def load_rd(path: str | io.BytesIO) -> pd.DataFrame:
    df = pd.read_csv(path, encoding='utf-8')
    df[COL_DATE] = pd.to_datetime(df[COL_DATE])
    df['매체_표기'] = df[COL_MEDIA].map(MEDIA_MAP).fillna(df[COL_MEDIA])
    return df
```

- [ ] **Step 3: 앱 실행 확인**

```
cd C:\Users\MADUP\Desktop\clade_0514
streamlit run musinsa_report.py --server.port 8503
```

브라우저에서 `http://localhost:8503` 열기 → RD CSV 업로드 → 무탠유입 탭 클릭 → KPI 확인  
Expected: 광고비 1,690만원, 활성CPU 112원 (2026-05-14 기준)

- [ ] **Step 4: 커밋**

```
git add musinsa_report.py
git commit -m "feat: musinsa_report — 메인 앱 (사이드바 + 6탭 라우팅)"
```

---

## Task 6: 전체 테스트 실행 및 최종 확인

- [ ] **Step 1: 전체 테스트 통과 확인**

```
pytest tests/test_rd_loader.py tests/test_comment_generator.py -v
```
Expected: 모두 PASSED, 0 failed

- [ ] **Step 2: 수동 검증 체크리스트**

브라우저에서 `http://localhost:8503`:
- [ ] CSV 업로드 → 사이드바에 파일명 표시
- [ ] 무탠유입 탭: TOTAL 광고비 1,690만원 / 활성CPU 112원 (2026-05-14)
- [ ] 무탠유입 탭: 무탠다드맨 행 존재, 기획전+상시/캠페인 하위 행
- [ ] 무탠유입 탭: 무탠다드통합 행에 카탈로그만 표시 (기획전+상시 없음)
- [ ] 코멘트 생성 버튼 클릭 → 텍스트 영역에 `#무탠유입` 포함 코멘트 생성
- [ ] 활성고객 탭: TOTAL KPI 카드 표시
- [ ] 매체 필터 해제 시 데이터 변동 확인

- [ ] **Step 3: 최종 커밋**

```
git add -A
git commit -m "feat: 무신사 리포트 대시보드 1차 구현 완료"
```

---

## 주의 사항

### comment_generator.py의 `%-m월` 포맷

Windows에서 `%-m`은 지원되지 않음. 아래로 대체:

```python
month_name = f"{target_date.month}월"
```

### 광고비 표기 임계값

`format_won`에서 억 단위 표기는 `1억` 이상일 때만:
- 1,690만원 → `1,690만원` (억 없음)
- 176,170,000원 → `1억 7,617만원`

### CPU = round(cost/users) 정수

`calc_cpu` 반환값은 `int` (원 단위 정수). `format_cpu`는 `,` 천단위 구분자 포함.
