from flask import Blueprint, request, session

from app.models.db import get_repository_by_id, get_sync_status, upsert_repository_for_user
from app.services.repositories_service import fetch_user_repositories
from app.services.sync_service import sync_repository_issues_and_commits
from app.utils.auth import require_authenticated_user
from app.utils.errors import ApiError
from app.utils.responses import success_response


repositories_bp = Blueprint("repositories", __name__)


@repositories_bp.get("/api/repositories")
def list_repositories():
    _user = require_authenticated_user()
    access_token = session.get("oauth_access_token", "")

    repositories = fetch_user_repositories(access_token)
    return success_response(
        data={"repositories": repositories},
        message="저장소 목록을 조회했습니다.",
    )


@repositories_bp.post("/api/repositories/select")
def select_repository():
    user = require_authenticated_user()
    payload = request.get_json(silent=True) or {}

    owner = str(payload.get("owner", "")).strip()
    name = str(payload.get("name", "")).strip()
    full_name = str(payload.get("full_name", "")).strip()
    github_repo_id = str(payload.get("github_repo_id", "")).strip()
    default_branch = str(payload.get("default_branch", "")).strip()

    if not owner and full_name and "/" in full_name:
        owner, name = full_name.split("/", 1)

    if not full_name and owner and name:
        full_name = f"{owner}/{name}"

    if not owner or not name or not full_name:
        raise ApiError("INVALID_REPOSITORY_PAYLOAD", "repository 선택 정보가 올바르지 않습니다.", 400)

    repository_id = upsert_repository_for_user(
        user_id=user["id"],
        owner=owner,
        name=name,
        full_name=full_name,
        github_repo_id=github_repo_id,
        default_branch=default_branch,
    )
    repository = get_repository_by_id(repository_id)

    session["current_repository_id"] = repository_id
    session["current_repository_full_name"] = full_name

    return success_response(
        data={"repository": repository},
        message="분석 대상 저장소가 선택되었습니다.",
    )


@repositories_bp.get("/api/repositories/current")
def current_repository():
    require_authenticated_user()

    repository_id = session.get("current_repository_id")
    if not repository_id:
        raise ApiError("REPOSITORY_NOT_SELECTED", "현재 선택된 저장소가 없습니다.", 404)

    repository = get_repository_by_id(int(repository_id))
    if not repository:
        session.pop("current_repository_id", None)
        session.pop("current_repository_full_name", None)
        raise ApiError("REPOSITORY_NOT_FOUND", "선택된 저장소 정보를 찾을 수 없습니다.", 404)

    return success_response(
        data={"repository": repository},
        message="현재 선택된 저장소를 조회했습니다.",
    )


@repositories_bp.post("/api/repositories/current/sync")
def sync_current_repository():
    require_authenticated_user()
    repository = _require_current_repository()
    access_token = session.get("oauth_access_token", "")

    result = sync_repository_issues_and_commits(repository, access_token)
    return success_response(
        data=result,
        message="저장소 동기화가 완료되었습니다.",
    )


@repositories_bp.get("/api/repositories/current/sync-status")
def current_repository_sync_status():
    require_authenticated_user()
    repository = _require_current_repository()
    status = get_sync_status(repository["id"])

    return success_response(
        data={
            "repository_id": repository["id"],
            "issue_count": status["issue_count"],
            "commit_count": status["commit_count"],
            "last_synced_at": status["last_synced_at"],
        },
        message="저장소 동기화 상태를 조회했습니다.",
    )


def _require_current_repository() -> dict:
    repository_id = session.get("current_repository_id")
    if not repository_id:
        raise ApiError("REPOSITORY_NOT_SELECTED", "현재 선택된 저장소가 없습니다.", 404)

    repository = get_repository_by_id(int(repository_id))
    if not repository:
        session.pop("current_repository_id", None)
        session.pop("current_repository_full_name", None)
        raise ApiError("REPOSITORY_NOT_FOUND", "선택된 저장소 정보를 찾을 수 없습니다.", 404)

    return repository
