from flask import Blueprint, current_app, request, session

from app.models.db import get_user_by_id, upsert_user
from app.services.auth_service import handle_github_callback
from app.services.github_oauth import build_github_authorize_url
from app.utils.auth import require_authenticated_user
from app.utils.errors import ApiError
from app.utils.responses import success_response


auth_bp = Blueprint("auth", __name__)


@auth_bp.get("/api/auth/github/login")
def github_login():
    client_id = current_app.config.get("GITHUB_CLIENT_ID", "")
    redirect_uri = current_app.config.get("GITHUB_REDIRECT_URI", "")
    scope = current_app.config.get("GITHUB_OAUTH_SCOPE", "read:user")

    if not client_id or not redirect_uri:
        raise ApiError("GITHUB_OAUTH_NOT_CONFIGURED", "GitHub OAuth 설정이 누락되었습니다.", 500)

    state = handle_state_generation()
    session["oauth_state"] = state
    session.permanent = True

    return success_response(
        data={
            "provider": "github",
            "authorization_url": build_github_authorize_url(
                client_id=client_id,
                redirect_uri=redirect_uri,
                state=state,
                scope=scope,
            ),
            "state": state,
        },
        message="GitHub OAuth 시작 URL이 생성되었습니다.",
    )


@auth_bp.get("/api/auth/github/callback")
def github_callback():
    code = request.args.get("code", "").strip()
    state = request.args.get("state", "").strip()
    session_state = session.get("oauth_state", "")

    oauth_result = handle_github_callback(
        code=code,
        received_state=state,
        expected_state=session_state,
        client_id=current_app.config.get("GITHUB_CLIENT_ID", ""),
        client_secret=current_app.config.get("GITHUB_CLIENT_SECRET", ""),
        redirect_uri=current_app.config.get("GITHUB_REDIRECT_URI", ""),
    )

    user_id = upsert_user(
        github_user_id=str(oauth_result["github_user"]["id"]),
        github_login=oauth_result["github_user"]["login"],
        github_name=oauth_result["github_user"].get("name") or "",
    )

    session["oauth_access_token"] = oauth_result["access_token"]
    session["auth_user_id"] = user_id
    session.pop("oauth_state", None)

    user = get_user_by_id(user_id)
    return success_response(
        data={"user": user},
        message="GitHub 로그인이 완료되었습니다.",
    )


@auth_bp.get("/api/auth/me")
def get_me():
    user = require_authenticated_user()

    return success_response(
        data={"user": user},
        message="현재 로그인 사용자 정보를 조회했습니다.",
    )


@auth_bp.post("/api/auth/logout")
def logout():
    session.clear()
    return success_response(message="로그아웃되었습니다.")


def handle_state_generation() -> str:
    import secrets

    return secrets.token_urlsafe(24)
