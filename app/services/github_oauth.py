from urllib.parse import urlencode

import requests

from app.utils.errors import ApiError


GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_API_URL = "https://api.github.com/user"


def build_github_authorize_url(client_id: str, redirect_uri: str, state: str, scope: str) -> str:
    return f"{GITHUB_AUTHORIZE_URL}?{urlencode({'client_id': client_id, 'redirect_uri': redirect_uri, 'scope': scope, 'state': state})}"


def exchange_code_for_access_token(code: str, client_id: str, client_secret: str, redirect_uri: str) -> str:
    response = requests.post(
        GITHUB_ACCESS_TOKEN_URL,
        headers={"Accept": "application/json"},
        json={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()

    access_token = payload.get("access_token", "")
    if not access_token:
        raise ApiError(
            "GITHUB_TOKEN_EXCHANGE_FAILED",
            "GitHub access token 교환에 실패했습니다.",
            400,
            payload,
        )

    return access_token


def fetch_github_user(access_token: str) -> dict:
    response = requests.get(
        GITHUB_USER_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()

    if not payload.get("id") or not payload.get("login"):
        raise ApiError(
            "GITHUB_USER_FETCH_FAILED",
            "GitHub 사용자 정보를 가져오지 못했습니다.",
            400,
            payload,
        )

    return payload
