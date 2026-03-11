from flask import Blueprint, session

from app.routes.repositories import _require_current_repository
from app.services.code_review import create_commit_review, get_commit_review
from app.services.commit_judge_service import (
    get_commit_detail,
    get_commit_judge_result,
    get_repository_problem_summary,
    judge_commit_files,
    list_repository_commits,
)
from app.services.skill_map_service import build_skill_map
from app.utils.auth import require_authenticated_user
from app.utils.responses import success_response


commits_bp = Blueprint("commits", __name__)


@commits_bp.get("/api/commits")
def list_commits():
    require_authenticated_user()
    repository = _require_current_repository()
    commits = list_repository_commits(repository["id"])
    return success_response(
        data={"commits": commits},
        message="commit 목록을 조회했습니다.",
    )


@commits_bp.get("/api/commits/<sha>")
def commit_detail(sha: str):
    require_authenticated_user()
    repository = _require_current_repository()
    commit = get_commit_detail(repository["id"], sha)
    return success_response(
        data={"commit": commit},
        message="commit 상세 정보를 조회했습니다.",
    )


@commits_bp.post("/api/commits/<sha>/analyze-files")
def analyze_commit_files(sha: str):
    require_authenticated_user()
    repository = _require_current_repository()
    access_token = session.get("oauth_access_token", "")
    result = judge_commit_files(repository, sha, access_token)
    return success_response(
        data=result,
        message="commit 파일 분석을 완료했습니다.",
    )


@commits_bp.post("/api/commits/<sha>/judge")
def judge_commit(sha: str):
    require_authenticated_user()
    repository = _require_current_repository()
    access_token = session.get("oauth_access_token", "")
    result = judge_commit_files(repository, sha, access_token)
    return success_response(
        data=result,
        message="commit 판정을 완료했습니다.",
    )


@commits_bp.get("/api/commits/<sha>/judge-result")
def commit_judge_result(sha: str):
    require_authenticated_user()
    repository = _require_current_repository()
    result = get_commit_judge_result(repository["id"], sha)
    return success_response(
        data=result,
        message="commit 판정 결과를 조회했습니다.",
    )


@commits_bp.get("/api/repositories/current/problem-summary")
def repository_problem_summary():
    require_authenticated_user()
    repository = _require_current_repository()
    summary = get_repository_problem_summary(repository["id"])
    return success_response(
        data=summary,
        message="repository 문제 판정 요약을 조회했습니다.",
    )


@commits_bp.get("/api/repositories/current/skill-map")
def repository_skill_map():
    require_authenticated_user()
    repository = _require_current_repository()
    skill_map = build_skill_map(repository["id"])
    return success_response(
        data=skill_map,
        message="repository Skill Map을 조회했습니다.",
    )


@commits_bp.post("/api/commits/<sha>/review")
def review_commit(sha: str):
    require_authenticated_user()
    repository = _require_current_repository()
    access_token = session.get("oauth_access_token", "")
    result = create_commit_review(repository, sha, access_token)
    return success_response(
        data=result,
        message="commit 코드 리뷰를 생성했습니다.",
    )


@commits_bp.get("/api/commits/<sha>/review")
def get_review(sha: str):
    require_authenticated_user()
    repository = _require_current_repository()
    result = get_commit_review(repository["id"], sha)
    return success_response(
        data=result,
        message="commit 코드 리뷰를 조회했습니다.",
    )
