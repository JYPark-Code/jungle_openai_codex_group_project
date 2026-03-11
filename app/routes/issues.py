from flask import Blueprint, session

from app.routes.repositories import _require_current_repository
from app.services.issue_template_service import build_template_status, create_missing_issues
from app.utils.auth import require_authenticated_user
from app.utils.responses import success_response


issues_bp = Blueprint("issues", __name__)


@issues_bp.get("/api/issues/template-status")
def issue_template_status():
    require_authenticated_user()
    repository = _require_current_repository()
    status = build_template_status(repository["id"])

    return success_response(
        data=status,
        message="CSV 템플릿 기준 이슈 상태를 조회했습니다.",
    )


@issues_bp.post("/api/issues/create-missing")
def create_template_missing_issues():
    require_authenticated_user()
    repository = _require_current_repository()
    access_token = session.get("oauth_access_token", "")

    result = create_missing_issues(repository, access_token)
    return success_response(
        data=result,
        message="누락 이슈 생성을 완료했습니다.",
    )
