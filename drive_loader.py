from __future__ import annotations
import re
from pathlib import Path
from datetime import datetime
import pandas as pd


def _end_date(filename: str) -> datetime:
    """musinsa_Total_YYYYMMDD~YYYY-MM-DD 에서 끝 날짜 파싱."""
    m = re.search(r'~(\d{4}-\d{2}-\d{2})', filename)
    if m:
        return datetime.strptime(m.group(1), '%Y-%m-%d')
    return datetime.min


def load_latest_rd(folder_path: str) -> tuple[pd.DataFrame, str]:
    """로컬 폴더에서 끝 날짜가 가장 최근인 musinsa_Total_*.csv 로드 → (DataFrame, 파일명)"""
    from rd_loader import load_rd

    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"폴더를 찾을 수 없습니다:\n{folder_path}")

    files = [f for f in folder.iterdir() if f.name.startswith('musinsa_Total') and f.suffix == '.csv']
    if not files:
        raise FileNotFoundError(
            f"폴더에 musinsa_Total*.csv 파일이 없습니다.\n경로: {folder_path}"
        )

    latest = max(files, key=lambda f: _end_date(f.stem))
    df = load_rd(str(latest))
    return df, latest.name
