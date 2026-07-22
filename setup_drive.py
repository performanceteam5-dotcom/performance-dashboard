"""최초 1회 실행: Google Drive OAuth 인증 → google-token.json 저장

Usage:
    python setup_drive.py
"""
from pathlib import Path

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
CREDS_PATH = 'google-oauth-credentials.json'
TOKEN_PATH = 'google-token.json'

if not Path(CREDS_PATH).exists():
    print(f"❌ {CREDS_PATH} 파일이 없습니다.")
    print("Google Cloud Console → API 및 서비스 → 사용자 인증 정보에서")
    print("OAuth 2.0 클라이언트 ID를 생성 후 JSON 다운로드하세요.")
    raise SystemExit(1)

from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
creds = flow.run_local_server(port=0)
Path(TOKEN_PATH).write_text(creds.to_json())
print(f"✅ Drive 인증 완료: {TOKEN_PATH} 저장됨")
print("이제 musinsa_report.py를 실행하면 Drive 연동이 활성화됩니다.")
