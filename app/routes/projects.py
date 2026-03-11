from flask import Blueprint, request

from app.models.db import get_active_github_project, save_github_project_tracking
from app.routes.repositories import _require_current_repository
from app.utils.auth import require_authenticated_user
from app.utils.errors import ApiError
from app.utils.responses import success_response


projects_bp = Blueprint("projects", __name__)


@projects_bp.post("/api/repositories/current/projects/track")
def track_current_week_project():
    require_authenticated_user()
    repository = _require_current_repository()
    payload = request.get_json(silent=True) or {}

    week_label = str(payload.get("week_label", "")).strip().casefold()
    project_title = str(payload.get("project_title", "")).strip()
    project_url = str(payload.get("project_url", "")).strip()
    project_number = str(payload.get("project_number", "")).strip()

    if not week_label or not project_title:
        raise ApiError("INVALID_PROJECT_PAYLOAD", "week_label과 project_title은 필수입니다.", 400)

    project_id = save_github_project_tracking(
        repository_id=repository["id"],
        week_label=week_label,
        project_title=project_title,
        project_url=project_url,
        project_number=project_number,
        is_active=True,
    )
    project = get_active_github_project(repository["id"])

    return success_response(
        data={"project_id": project_id, "project": project},
        message="현재 주차 GitHub Project 추적 대상을 저장했습니다.",
    )


@projects_bp.get("/api/repositories/current/projects/current")
def get_current_tracked_project():
    require_authenticated_user()
    repository = _require_current_repository()
    project = get_active_github_project(repository["id"])
    return success_response(
        data={"project": project},
        message="현재 추적 중인 GitHub Project를 조회했습니다.",
    )
