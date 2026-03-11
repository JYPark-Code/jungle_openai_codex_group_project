from app.services.github_oauth import exchange_code_for_access_token, fetch_github_user
from app.utils.errors import ApiError


def handle_github_callback(
    code: str,
    received_state: str,
    expected_state: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict:
    if not code:
        raise ApiError("GITHUB_CODE_MISSING", "GitHub authorization code가 필요합니다.", 400)

    if not received_state or received_state != expected_state:
        raise ApiError("GITHUB_STATE_MISMATCH", "OAuth state 검증에 실패했습니다.", 400)

    if not client_id or not client_secret or not redirect_uri:
        raise ApiError("GITHUB_OAUTH_NOT_CONFIGURED", "GitHub OAuth 설정이 누락되었습니다.", 500)

    access_token = exchange_code_for_access_token(
        code=code,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )
    github_user = fetch_github_user(access_token)

    return {
        "access_token": access_token,
        "github_user": github_user,
    }
