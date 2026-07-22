from __future__ import annotations
import os
import requests


def send_to_slack(text: str, webhook_url: str | None = None) -> tuple[bool, str]:
    """슬랙 Incoming Webhook으로 메시지 발송.

    Returns:
        (success, error_message)
    """
    url = webhook_url or os.environ.get('SLACK_WEBHOOK_URL', '')
    if not url:
        return False, "SLACK_WEBHOOK_URL이 설정되지 않았습니다."
    try:
        resp = requests.post(url, json={'text': text}, timeout=10)
        if resp.status_code == 200:
            return True, ''
        return False, f"슬랙 응답 오류: {resp.status_code} {resp.text}"
    except requests.RequestException as e:
        return False, f"네트워크 오류: {e}"
