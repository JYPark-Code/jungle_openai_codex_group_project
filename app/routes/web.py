from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from app.models.db import get_repository_by_id, get_user_by_id, upsert_repository_for_user, upsert_user
from app.services.auth_service import handle_github_callback
from app.services.code_review import create_commit_review
from app.services.commit_judge_service import judge_commit_files
from app.services.demo_service import ensure_demo_workspace
from app.services.github_oauth import build_github_authorize_url
from app.services.issue_template_service import create_missing_issues
from app.services.repositories_service import fetch_user_repositories
from app.services.sync_service import sync_repository_issues_and_commits
from app.services.web_app_service import (
    build_dashboard_page_data,
    build_profile_page_data,
    build_reviews_page_data,
)


web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def home():
    if _get_authenticated_user():
        return redirect(url_for("web.dashboard_page"))
    return redirect(url_for("web.login_page"))


@web_bp.get("/login")
@web_bp.get("/signup")
def login_page():
    return render_template(
        "web_login.html",
        oauth_configured=_web_oauth_is_configured(),
        error_message=request.args.get("error", "").strip(),
        demo_mode=False,
    )


@web_bp.get("/auth/github/start")
def github_start():
    client_id = current_app.config.get("GITHUB_CLIENT_ID", "")
    redirect_uri = current_app.config.get("GITHUB_WEB_REDIRECT_URI", "")
    scope = current_app.config.get("GITHUB_OAUTH_SCOPE", "read:user")

    if not client_id or not redirect_uri:
        return redirect(url_for("web.login_page"))

    state = _handle_state_generation()
    session["oauth_state"] = state
    session.permanent = True

    return redirect(
        build_github_authorize_url(
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=state,
            scope=scope,
        )
    )


@web_bp.get("/auth/github/callback")
def github_callback_web():
    try:
        oauth_result = handle_github_callback(
            code=request.args.get("code", "").strip(),
            received_state=request.args.get("state", "").strip(),
            expected_state=session.get("oauth_state", ""),
            client_id=current_app.config.get("GITHUB_CLIENT_ID", ""),
            client_secret=current_app.config.get("GITHUB_CLIENT_SECRET", ""),
            redirect_uri=current_app.config.get("GITHUB_WEB_REDIRECT_URI", ""),
        )
    except Exception as error:
        session.pop("oauth_state", None)
        message = getattr(error, "message", "GitHub 로그인 중 오류가 발생했습니다.")
        return redirect(url_for("web.login_page", error=message))

    user_id = upsert_user(
        github_user_id=str(oauth_result["github_user"]["id"]),
        github_login=oauth_result["github_user"]["login"],
        github_name=oauth_result["github_user"].get("name") or "",
    )

    session["oauth_access_token"] = oauth_result["access_token"]
    session["auth_user_id"] = user_id
    session.pop("oauth_state", None)
    flash("GitHub 로그인에 성공했습니다.", "success")

    return redirect(url_for("web.dashboard_page"))


@web_bp.post("/auth/logout")
def logout_web():
    session.clear()
    flash("로그아웃되었습니다.", "success")
    return redirect(url_for("web.login_page"))


@web_bp.post("/auth/demo-login")
def demo_login():
    workspace = ensure_demo_workspace()
    session["auth_user_id"] = workspace["user_id"]
    session["oauth_access_token"] = "demo-token"
    session["current_repository_id"] = workspace["repository_id"]
    session["current_repository_full_name"] = workspace["full_name"]
    flash("데모 작업공간으로 진입했습니다.", "success")
    return redirect(url_for("web.dashboard_page"))


@web_bp.get("/app/dashboard")
def dashboard_page():
    user = _require_web_user()
    if not user:
        return redirect(url_for("web.login_page"))
    repository = _get_current_repository()
    repositories = _fetch_repositories_for_sidebar()
    activity_sort = request.args.get("activity_sort", "issue_asc").strip()
    dashboard_data = build_dashboard_page_data(repository, activity_sort=activity_sort) if repository else None

    return render_template(
        "web_dashboard.html",
        screen="dashboard",
        current_user=user,
        current_repository=repository,
        repositories=repositories,
        dashboard=dashboard_data,
    )


@web_bp.post("/app/repositories/select")
def select_repository_web():
    user = _require_web_user()
    if not user:
        return redirect(url_for("web.login_page"))
    owner = request.form.get("owner", "").strip()
    name = request.form.get("name", "").strip()
    full_name = request.form.get("full_name", "").strip()
    github_repo_id = request.form.get("github_repo_id", "").strip()
    default_branch = request.form.get("default_branch", "").strip()

    if not owner and full_name and "/" in full_name:
        owner, name = full_name.split("/", 1)

    repository_id = upsert_repository_for_user(
        user_id=user["id"],
        owner=owner,
        name=name,
        full_name=full_name or f"{owner}/{name}",
        github_repo_id=github_repo_id,
        default_branch=default_branch,
    )

    session["current_repository_id"] = repository_id
    session["current_repository_full_name"] = full_name or f"{owner}/{name}"
    flash("저장소를 변경했습니다.", "success")
    return redirect(url_for("web.dashboard_page"))


@web_bp.post("/app/repositories/sync")
def sync_repository_web():
    user = _require_web_user()
    if not user:
        return redirect(url_for("web.login_page"))
    repository = _require_current_repository_for_web()
    if not repository:
        return redirect(url_for("web.dashboard_page"))
    try:
        sync_repository_issues_and_commits(repository, session.get("oauth_access_token", ""))
    except Exception as error:
        flash(getattr(error, "message", "저장소 동기화 중 오류가 발생했습니다."), "error")
        return redirect(url_for("web.dashboard_page"))
    flash("저장소 동기화가 완료되었습니다.", "success")
    return redirect(url_for("web.dashboard_page"))


@web_bp.post("/app/issues/create-missing")
def create_missing_issues_web():
    user = _require_web_user()
    if not user:
        return redirect(url_for("web.login_page"))
    repository = _require_current_repository_for_web()
    if not repository:
        return redirect(url_for("web.dashboard_page"))
    access_token = session.get("oauth_access_token", "")
    try:
        if access_token != "demo-token":
            create_missing_issues(repository, access_token)
    except Exception as error:
        flash(getattr(error, "message", "누락 이슈 생성 중 오류가 발생했습니다."), "error")
        return redirect(url_for("web.dashboard_page"))
    flash("누락 이슈 생성을 완료했습니다.", "success")
    return redirect(url_for("web.dashboard_page"))


@web_bp.get("/app/reviews")
def reviews_page():
    user = _require_web_user()
    if not user:
        return redirect(url_for("web.login_page"))
    repository = _require_current_repository_for_web()
    if not repository:
        return redirect(url_for("web.dashboard_page"))
    selected_sha = request.args.get("sha", "").strip()

    return render_template(
        "web_reviews.html",
        screen="reviews",
        current_user=user,
        current_repository=repository,
        repositories=_fetch_repositories_for_sidebar(),
        review_page=build_reviews_page_data(repository, session.get("oauth_access_token", ""), selected_sha),
    )


@web_bp.post("/app/reviews/<sha>/generate")
def generate_review_web(sha: str):
    user = _require_web_user()
    if not user:
        return redirect(url_for("web.login_page"))
    repository = _require_current_repository_for_web()
    if not repository:
        return redirect(url_for("web.dashboard_page"))
    access_token = session.get("oauth_access_token", "")
    try:
        judge_commit_files(repository, sha, access_token)
        create_commit_review(repository, sha, access_token)
    except Exception as error:
        flash(getattr(error, "message", "커밋 리뷰 생성 중 오류가 발생했습니다."), "error")
        return redirect(url_for("web.reviews_page", sha=sha))
    flash("커밋 리뷰를 생성했습니다.", "success")
    return redirect(url_for("web.reviews_page", sha=sha))


@web_bp.get("/app/profile")
def profile_page():
    user = _require_web_user()
    if not user:
        return redirect(url_for("web.login_page"))
    repository = _require_current_repository_for_web()
    if not repository:
        return redirect(url_for("web.dashboard_page"))

    return render_template(
        "web_profile.html",
        screen="profile",
        current_user=user,
        current_repository=repository,
        repositories=_fetch_repositories_for_sidebar(),
        profile=build_profile_page_data(repository),
    )


def _require_web_user() -> dict:
    user = _get_authenticated_user()
    return user


def _get_authenticated_user() -> dict | None:
    user_id = session.get("auth_user_id")
    access_token = session.get("oauth_access_token")
    if not user_id or not access_token:
        return None
    return get_user_by_id(int(user_id))


def _get_current_repository() -> dict | None:
    repository_id = session.get("current_repository_id")
    if not repository_id:
        return None
    return get_repository_by_id(int(repository_id))


def _require_current_repository_for_web() -> dict:
    repository = _get_current_repository()
    return repository


def _fetch_repositories_for_sidebar() -> list[dict]:
    access_token = session.get("oauth_access_token", "")
    if not access_token:
        return []
    try:
        return fetch_user_repositories(access_token)
    except Exception:
        return []


def _web_oauth_is_configured() -> bool:
    return bool(
        current_app.config.get("GITHUB_CLIENT_ID", "")
        and current_app.config.get("GITHUB_CLIENT_SECRET", "")
        and current_app.config.get("GITHUB_WEB_REDIRECT_URI", "")
    )


def _handle_state_generation() -> str:
    import secrets

    return secrets.token_urlsafe(24)
