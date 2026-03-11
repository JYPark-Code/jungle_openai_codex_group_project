from pathlib import Path

from app.models.db import (
    get_active_github_project,
    save_commit,
    save_problem_judgement,
    save_issue,
    upsert_repository_for_user,
    upsert_user,
)
from app.services.issue_template_service import build_template_status, load_issue_templates
from app.services.report_service import build_user_report


def ensure_ops_context(app):
    with app.app_context():
        user_id = upsert_user("9100", "ops-user", "운영 사용자")
        repository_id = upsert_repository_for_user(
            user_id=user_id,
            owner="JYPark-Code",
            name="SW-AI-W02-05",
            full_name="JYPark-Code/SW-AI-W02-05",
            github_repo_id="9100",
            default_branch="main",
        )
        commit_id, _ = save_commit(
            repository_id=repository_id,
            sha="ops123",
            message="주차 문제 풀이",
            author_name="JYPark",
            committed_at="2026-03-11T12:00:00Z",
        )
    return repository_id, commit_id


def login_ops(client, repository_id):
    with client.session_transaction() as session:
        session["auth_user_id"] = 1
        session["oauth_access_token"] = "ops-token"
        session["current_repository_id"] = repository_id
        session["current_repository_full_name"] = "JYPark-Code/SW-AI-W02-05"


def make_csv(tmp_path: Path, filename: str, rows: list[tuple[str, str]]) -> Path:
    csv_path = tmp_path / filename
    lines = ["title,content"]
    lines.extend([f"{title},{content}" for title, content in rows])
    csv_path.write_text("\n".join(lines), encoding="utf-8-sig")
    return csv_path


def test_template_metadata_supports_required_and_optional_rules(tmp_path):
    make_csv(
        tmp_path,
        "week2_issues_complete.csv",
        [
            ("basic - 배열 연습", ""),
            ("problem-solving 하 - 그래프", ""),
            ("problem-solving 상 - 최단경로", ""),
            ("Extra - LeetCode 연습", ""),
        ],
    )

    templates = load_issue_templates(tmp_path)
    info = {item["title"]: item for item in templates}

    assert info["basic - 배열 연습"]["requirement_level"] == "required"
    assert info["problem-solving 하 - 그래프"]["requirement_level"] == "required"
    assert info["problem-solving 상 - 최단경로"]["requirement_level"] == "optional"
    assert info["Extra - LeetCode 연습"]["requirement_level"] == "optional"
    assert info["basic - 배열 연습"]["week_label"] == "week2"


def test_required_progress_uses_active_week_only(app, tmp_path):
    repository_id, _commit_id = ensure_ops_context(app)
    make_csv(
        tmp_path,
        "week2_issues_complete.csv",
        [("basic - 배열 연습", ""), ("problem-solving 하 - 그래프", "")],
    )
    make_csv(
        tmp_path,
        "week3_issues_complete.csv",
        [("basic - 큐 연습", ""), ("problem-solving 상 - 최단경로", "")],
    )

    with app.app_context():
        save_issue(
            repository_id=repository_id,
            github_issue_id="100",
            issue_number=1,
            title="basic - 배열 연습",
            body="",
            state="open",
            github_created_at="2026-03-11T10:00:00Z",
        )
        save_issue(
            repository_id=repository_id,
            github_issue_id="101",
            issue_number=2,
            title="problem-solving 하 - 그래프",
            body="",
            state="open",
            github_created_at="2026-03-11T10:10:00Z",
        )
        status = build_template_status(repository_id, tmp_path, active_week="week2")

    assert status["active_week"] == "week2"
    assert status["required_template_count"] == 2
    assert status["required_matched_count"] == 2
    assert status["required_progress"] == 1.0


def test_report_excludes_unmatched_extra_commits_from_progress(app, monkeypatch):
    repository_id, commit_id = ensure_ops_context(app)

    with app.app_context():
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=10,
            problem_key="basic - 배열 연습",
            file_path="week2/array.py",
            judgement_status="solved",
            match_score=1.0,
            matched_by_filename=True,
        )
        save_problem_judgement(
            repository_id=repository_id,
            commit_id=commit_id,
            issue_number=None,
            problem_key="sandbox_example.py",
            file_path="playground/sandbox_example.py",
            judgement_status="attempted",
            match_score=0.1,
        )

    monkeypatch.setattr(
        "app.services.report_service.build_template_status",
        lambda repository_id: {
            "active_week": "week2",
            "template_count": 4,
            "matched_count": 2,
            "missing_count": 2,
            "required_template_count": 2,
            "required_matched_count": 1,
            "required_progress": 0.5,
            "matched_issues": [],
            "missing_issues": [],
        },
    )
    monkeypatch.setattr(
        "app.services.report_service.get_recommendations",
        lambda repository_id: {"weak_topics": [], "recommendations": []},
    )
    monkeypatch.setattr(
        "app.services.report_service.rank_weak_topics",
        lambda repository_id, limit=5: [],
    )

    with app.app_context():
        report = build_user_report(repository_id)

    assert report["solved_count"] == 1
    assert report["attempted_count"] == 0
    assert report["extra_practice_count"] == 1
    assert report["week_progress"] == 0.5


def test_current_week_project_tracking_api(client, app):
    repository_id, _commit_id = ensure_ops_context(app)
    login_ops(client, repository_id)

    create_response = client.post(
        "/api/repositories/current/projects/track",
        json={
            "week_label": "week3",
            "project_title": "Week 3 Tracking",
            "project_url": "https://github.com/orgs/example/projects/3",
            "project_number": "3",
        },
    )
    current_response = client.get("/api/repositories/current/projects/current")

    assert create_response.status_code == 200
    assert current_response.status_code == 200
    assert current_response.get_json()["data"]["project"]["week_label"] == "week3"

    with app.app_context():
        project = get_active_github_project(repository_id)

    assert project is not None
    assert project["project_title"] == "Week 3 Tracking"
