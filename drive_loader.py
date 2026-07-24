from __future__ import annotations
import io
import os
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


# ── Dropbox API ────────────────────────────────────────────────────

def _get_dropbox_client():
    import dropbox
    from dropbox.common import PathRoot

    dbx = dropbox.Dropbox(
        app_key=os.environ['DROPBOX_APP_KEY'],
        app_secret=os.environ['DROPBOX_APP_SECRET'],
        oauth2_refresh_token=os.environ['DROPBOX_REFRESH_TOKEN'],
    )
    # 기업용 팀 폴더 접근: root namespace 사용
    account = dbx.users_get_current_account()
    root_ns = account.root_info.root_namespace_id
    return dbx.with_path_root(PathRoot.namespace_id(root_ns))


def load_from_dropbox(folder_path: str) -> tuple[pd.DataFrame, str]:
    """Dropbox 팀 폴더에서 최신 musinsa_Total*.csv 로드"""
    from rd_loader import load_rd
    import dropbox

    dbx = _get_dropbox_client()

    # 폴더 내 파일 목록
    result = dbx.files_list_folder(folder_path)
    entries = result.entries
    while result.has_more:
        result = dbx.files_list_folder_continue(result.cursor)
        entries += result.entries

    csv_files = [
        e for e in entries
        if isinstance(e, dropbox.files.FileMetadata)
        and e.name.startswith('musinsa_Total')
        and e.name.endswith('.csv')
    ]
    if not csv_files:
        raise FileNotFoundError(
            f"Dropbox 폴더에 musinsa_Total*.csv 파일이 없습니다.\n경로: {folder_path}"
        )

    latest = max(csv_files, key=lambda e: _end_date(e.name))
    _, response = dbx.files_download(latest.path_lower)
    df = load_rd(io.BytesIO(response.content))
    return df, latest.name


# ── 로컬 폴더 ──────────────────────────────────────────────────────

def load_from_local(folder_path: str) -> tuple[pd.DataFrame, str]:
    """로컬 폴더에서 최신 musinsa_Total*.csv 로드"""
    from rd_loader import load_rd

    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"폴더를 찾을 수 없습니다:\n{folder_path}")

    files = [
        f for f in folder.iterdir()
        if f.name.startswith('musinsa_Total') and f.suffix == '.csv'
    ]
    if not files:
        raise FileNotFoundError(
            f"폴더에 musinsa_Total*.csv 파일이 없습니다.\n경로: {folder_path}"
        )

    latest = max(files, key=lambda f: _end_date(f.stem))
    df = load_rd(str(latest))
    return df, latest.name


# ── 통합 진입점 ────────────────────────────────────────────────────

def load_latest_rd() -> tuple[pd.DataFrame, str]:
    """환경변수에 따라 Dropbox API 또는 로컬 폴더에서 자동 로드"""
    if os.environ.get('DROPBOX_APP_KEY'):
        folder = os.environ.get('DROPBOX_FOLDER_PATH', '')
        if not folder:
            raise ValueError("DROPBOX_FOLDER_PATH 환경변수가 설정되지 않았습니다.")
        return load_from_dropbox(folder)

    local_path = os.environ.get('RD_FOLDER_PATH', '')
    if local_path:
        return load_from_local(local_path)

    raise EnvironmentError("DROPBOX_APP_KEY 또는 RD_FOLDER_PATH 환경변수를 설정하세요.")
