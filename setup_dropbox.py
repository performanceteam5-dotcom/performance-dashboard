"""Dropbox OAuth2 인증 → refresh token 발급 스크립트 (최초 1회만 실행)

Usage:
    python setup_dropbox.py

출력된 DROPBOX_REFRESH_TOKEN을 .env 또는 Streamlit Cloud Secrets에 저장하세요.
"""
import os
import webbrowser
import urllib.parse
import urllib.request
import json
import base64

APP_KEY    = input("Dropbox App Key를 입력하세요: ").strip()
APP_SECRET = input("Dropbox App Secret를 입력하세요: ").strip()

# 인증 URL 열기
auth_url = (
    "https://www.dropbox.com/oauth2/authorize"
    f"?client_id={APP_KEY}"
    "&response_type=code"
    "&token_access_type=offline"
)
print(f"\n브라우저에서 아래 URL을 열어 Dropbox 로그인 후 코드를 복사하세요:\n{auth_url}\n")
webbrowser.open(auth_url)

code = input("인증 코드를 붙여넣으세요: ").strip()

# refresh token 발급
credentials = base64.b64encode(f"{APP_KEY}:{APP_SECRET}".encode()).decode()
data = urllib.parse.urlencode({"code": code, "grant_type": "authorization_code"}).encode()
req = urllib.request.Request(
    "https://api.dropboxapi.com/oauth2/token",
    data=data,
    headers={"Authorization": f"Basic {credentials}"},
)
with urllib.request.urlopen(req) as resp:
    token_data = json.loads(resp.read())

refresh_token = token_data.get("refresh_token", "")
print("\n✅ 인증 완료! 아래 값을 .env 또는 Streamlit Cloud Secrets에 추가하세요:\n")
print(f"DROPBOX_APP_KEY={APP_KEY}")
print(f"DROPBOX_APP_SECRET={APP_SECRET}")
print(f"DROPBOX_REFRESH_TOKEN={refresh_token}")
print(f'DROPBOX_FOLDER_PATH=/광고사업부/4. 광고주/무신사/★ 무신사 통합/통합리포트RD')
