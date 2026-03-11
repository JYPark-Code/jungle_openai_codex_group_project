from flask import session

from app.models.db import get_user_by_id
from app.utils.errors import ApiError


def require_authenticated_user() -> dict:
    user_id = session.get("auth_user_id")
    access_token = session.get("oauth_access_token")

    if not user_id or not access_token:
        raise ApiError("UNAUTHORIZED", "로그인이 필요합니다.", 401)

    user = get_user_by_id(int(user_id))
    if not user:
        session.clear()
        raise ApiError("UNAUTHORIZED", "세션 사용자 정보를 찾을 수 없습니다.", 401)

    return user
