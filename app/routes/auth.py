import secrets
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from flask import Blueprint, current_app, redirect, request, session

from app.models.db import get_latest_repository_by_user_id, get_user_by_id, upsert_user
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
        raise ApiError(
            "GITHUB_OAUTH_NOT_CONFIGURED",
            "GitHub OAuth 설정이 누락되었습니다.",
            500,
        )

    state = _generate_state()
    oauth_mode = _resolve_oauth_mode()
    next_url = _resolve_next_url()

    session["oauth_state"] = state
    session["oauth_mode"] = oauth_mode
    session["oauth_next_url"] = next_url
    session.permanent = True

    authorization_url = build_github_authorize_url(
        client_id=client_id,
        redirect_uri=redirect_uri,
        state=state,
        scope=scope,
    )

    if oauth_mode == "redirect":
        return redirect(authorization_url)

    return success_response(
        data={
            "provider": "github",
            "authorization_url": authorization_url,
            "state": state,
            "mode": oauth_mode,
            "next_url": next_url,
        },
        message="GitHub OAuth 시작 URL을 생성했습니다.",
    )


@auth_bp.get("/api/auth/github/callback")
def github_callback():
    code = request.args.get("code", "").strip()
    state = request.args.get("state", "").strip()
    session_state = session.get("oauth_state", "")
    oauth_mode = session.get("oauth_mode", "json")
    next_url = session.get("oauth_next_url") or current_app.config.get("FRONTEND_OAUTH_SUCCESS_URL", "")

    try:
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
        _restore_current_repository_session(user_id)
        _clear_oauth_session_keys()

        user = get_user_by_id(user_id)
        if oauth_mode == "redirect":
            return redirect(_append_query_params(next_url, {"status": "success"}))

        return success_response(
            data={"user": user},
            message="GitHub 로그인이 완료되었습니다.",
        )
    except ApiError as error:
        _clear_oauth_session_keys()
        if oauth_mode == "redirect":
            failure_url = current_app.config.get("FRONTEND_OAUTH_FAILURE_URL", "")
            return redirect(
                _append_query_params(
                    failure_url,
                    {
                        "status": "error",
                        "code": error.error_code,
                    },
                )
            )
        raise error


@auth_bp.get("/api/auth/me")
def get_me():
    user = require_authenticated_user()
    return success_response(
        data={"user": user},
        message="현재 로그인한 사용자 정보를 조회했습니다.",
    )


@auth_bp.post("/api/auth/logout")
def logout():
    session.clear()
    return success_response(message="로그아웃되었습니다.")


def _generate_state() -> str:
    return secrets.token_urlsafe(24)


def _resolve_oauth_mode() -> str:
    mode = (request.args.get("mode") or "").strip().lower()
    return "redirect" if mode == "redirect" else "json"


def _resolve_next_url() -> str:
    requested_next_url = (request.args.get("next") or "").strip()
    if requested_next_url and _is_allowed_frontend_url(requested_next_url):
        return requested_next_url
    return current_app.config.get("FRONTEND_OAUTH_SUCCESS_URL", "")


def _is_allowed_frontend_url(url: str) -> bool:
    if not url:
        return False

    parsed_target = urlparse(url)
    target_origin = f"{parsed_target.scheme}://{parsed_target.netloc}"
    allowed_origins = {
        origin.strip()
        for origin in str(current_app.config.get("CORS_ALLOWED_ORIGINS", "")).split(",")
        if origin.strip()
    }
    success_origin = _extract_origin(current_app.config.get("FRONTEND_OAUTH_SUCCESS_URL", ""))
    failure_origin = _extract_origin(current_app.config.get("FRONTEND_OAUTH_FAILURE_URL", ""))

    if success_origin:
        allowed_origins.add(success_origin)
    if failure_origin:
        allowed_origins.add(failure_origin)

    return target_origin in allowed_origins


def _extract_origin(url: str) -> str:
    if not url:
        return ""
    parsed_url = urlparse(url)
    if not parsed_url.scheme or not parsed_url.netloc:
        return ""
    return f"{parsed_url.scheme}://{parsed_url.netloc}"


def _clear_oauth_session_keys():
    session.pop("oauth_state", None)
    session.pop("oauth_next_url", None)
    session.pop("oauth_mode", None)


def _restore_current_repository_session(user_id: int):
    repository = get_latest_repository_by_user_id(user_id)
    if not repository:
        session.pop("current_repository_id", None)
        session.pop("current_repository_full_name", None)
        return

    session["current_repository_id"] = repository["id"]
    session["current_repository_full_name"] = repository["full_name"]


def _append_query_params(url: str, params: dict[str, str]) -> str:
    if not url:
        return "/"

    parsed_url = urlparse(url)
    query = dict(parse_qsl(parsed_url.query))
    query.update({key: value for key, value in params.items() if value is not None})
    return urlunparse(parsed_url._replace(query=urlencode(query)))
