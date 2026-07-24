from __future__ import annotations
import os
import requests


def send_to_slack(text: str) -> tuple[bool, str]:
    """Slack Bot Token으로 chat.postMessage API 발송.

    환경변수:
        SLACK_BOT_TOKEN  : xoxb-... 봇 토큰
        SLACK_CHANNEL_ID : C... 채널 ID

    Returns:
        (success, error_message)
    """
    token = os.environ.get('SLACK_BOT_TOKEN', '')
    channel = os.environ.get('SLACK_CHANNEL_ID', '')

    if not token:
        return False, "SLACK_BOT_TOKEN이 설정되지 않았습니다."
    if not channel:
        return False, "SLACK_CHANNEL_ID가 설정되지 않았습니다."

    try:
        resp = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers={'Authorization': f'Bearer {token}'},
            json={'channel': channel, 'text': text},
            timeout=10,
        )
        data = resp.json()
        if data.get('ok'):
            return True, ''
        return False, f"슬랙 오류: {data.get('error', '알 수 없는 오류')}"
    except requests.RequestException as e:
        return False, f"네트워크 오류: {e}"
