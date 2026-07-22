from __future__ import annotations
import io
from pathlib import Path
import pandas as pd

_SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
_CREDS_PATH = Path('google-oauth-credentials.json')
_TOKEN_PATH = Path('google-token.json')


def _get_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    if not _TOKEN_PATH.exists():
        raise FileNotFoundError(
            "google-token.json이 없습니다. "
            "터미널에서 `python setup_drive.py`를 실행해 Drive 인증을 완료하세요."
        )

    creds = Credentials.from_authorized_user_file(str(_TOKEN_PATH), _SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _TOKEN_PATH.write_text(creds.to_json())

    return build('drive', 'v3', credentials=creds)


def list_rd_files(folder_id: str) -> list[dict]:
    """폴더에서 musinsa_Total_*.csv 파일 목록 반환 (최신순)"""
    service = _get_service()
    query = (
        f"'{folder_id}' in parents "
        f"and name contains 'musinsa_Total' "
        f"and mimeType='text/csv' "
        f"and trashed=false"
    )
    result = service.files().list(
        q=query,
        orderBy='modifiedTime desc',
        fields='files(id, name, modifiedTime)',
        pageSize=10,
    ).execute()
    return result.get('files', [])


def download_rd_file(file_id: str) -> io.BytesIO:
    """Drive 파일 다운로드 → BytesIO"""
    from googleapiclient.http import MediaIoBaseDownload
    service = _get_service()
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buf.seek(0)
    return buf


def load_latest_rd(folder_id: str) -> tuple[pd.DataFrame, str]:
    """최신 RD 파일 로드 → (DataFrame, 파일명)"""
    from rd_loader import load_rd
    files = list_rd_files(folder_id)
    if not files:
        raise FileNotFoundError(
            "폴더에 musinsa_Total_*.csv 파일이 없습니다. "
            "GDRIVE_FOLDER_ID를 확인하세요."
        )
    latest = files[0]
    buf = download_rd_file(latest['id'])
    df = load_rd(buf)
    return df, latest['name']
