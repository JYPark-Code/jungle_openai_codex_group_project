from pathlib import Path

from app.models.db import get_issues_by_repository_id, save_issue, upsert_repository_for_user, upsert_user
from app.services.issue_template_service import (
    build_template_status,
    classify_issue_title,
    create_missing_issues,
    infer_difficulty_level,
    load_issue_templates,
    normalize_title,
)


def ensure_user_and_repository(app):
    with app.app_context():
        user_id = upsert_user("5005", "template-user", "템플릿 사용자")
        repository_id = upsert_repository_for_user(
            user_id=user_id,
            owner="JYPark-Code",
            name="SW-AI-W02-05",
            full_name="JYPark-Code/SW-AI-W02-05",
            github_repo_id="777",
            default_branch="main",
        )
    return repository_id


def login_with_current_repository(client, repository_id):
    with client.session_transaction() as session:
        session["auth_user_id"] = 1
        session["oauth_access_token"] = "template-token"
        session["current_repository_id"] = repository_id
        session["current_repository_full_name"] = "JYPark-Code/SW-AI-W02-05"


def make_csv(tmp_path: Path, filename: str, rows: list[tuple[str, str]]) -> Path:
    csv_path = tmp_path / filename
    lines = ["title,content"]
    lines.extend([f"{title},{content}" for title, content in rows])
    csv_path.write_text("\n".join(lines), encoding="utf-8-sig")
    return csv_path


def test_load_issue_templates_reads_csv_files(tmp_path):
    make_csv(
        tmp_path,
        "week2.csv",
        [("공통 - 학습 목표 확인", "content one"), ("basic - 배열 연습", "content two")],
    )

    templates = load_issue_templates(tmp_path)

    assert len(templates) == 2
    assert templates[0]["title"] == "공통 - 학습 목표 확인"
    assert templates[0]["category"] == "common"
    assert templates[0]["requirement_level"] == "excluded"
    assert templates[1]["track_type"] == "basic"


def test_title_matching_and_missing_issue_calculation(app, tmp_path):
    repository_id = ensure_user_and_repository(app)
    make_csv(
        tmp_path,
        "week2.csv",
        [("공통 - 학습 목표 확인", "content one"), ("basic - 배열 연습", "content two")],
    )

    with app.app_context():
        save_issue(
            repository_id=repository_id,
            github_issue_id="100",
            issue_number=1,
            title="공통   -   학습 목표 확인",
            body="saved issue",
            state="open",
            github_created_at="2026-03-11T10:00:00Z",
        )
        status = build_template_status(repository_id, tmp_path)

    assert status["template_count"] == 2
    assert status["matched_count"] == 1
    assert status["missing_count"] == 1
    assert status["missing_issues"][0]["title"] == "basic - 배열 연습"


def test_create_missing_issues_creates_and_persists_to_db(app, tmp_path, monkeypatch):
    repository_id = ensure_user_and_repository(app)
    make_csv(
        tmp_path,
        "week2.csv",
        [("공통 - 학습 목표 확인", "content one"), ("basic - 배열 연습", "content two")],
    )

    with app.app_context():
        repository = {
            "id": repository_id,
            "owner": "JYPark-Code",
            "name": "SW-AI-W02-05",
        }
        created_counter = {"value": 50}

        def fake_create_issue(access_token, repo_owner, repo_name, title, body):
            created_counter["value"] += 1
            return {
                "id": str(created_counter["value"]),
                "number": created_counter["value"],
                "title": title,
                "body": body,
                "state": "open",
                "created_at": "2026-03-11T12:00:00Z",
                "html_url": f"https://github.com/{repo_owner}/{repo_name}/issues/{created_counter['value']}",
            }

        monkeypatch.setattr(
            "app.services.issue_template_service.create_issue_with_access_token",
            fake_create_issue,
        )

        result = create_missing_issues(repository, "template-token", tmp_path, active_week="week2")
        saved_issues = get_issues_by_repository_id(repository_id)

    assert result["missing_count"] == 0
    assert result["active_week"] == "week2"
    assert len(result["created_issues"]) == 2
    assert len(saved_issues) == 2


def test_template_status_api_supports_week_query(client, app, monkeypatch):
    repository_id = ensure_user_and_repository(app)
    login_with_current_repository(client, repository_id)

    monkeypatch.setattr(
        "app.routes.issues.build_template_status",
        lambda repository_id, active_week=None: {
            "template_count": 2,
            "matched_count": 1,
            "missing_count": 1,
            "active_week": active_week,
            "active_week_template_count": 1,
            "required_template_count": 1,
            "required_matched_count": 1,
            "required_progress": 1.0,
            "matched_issues": [],
            "missing_issues": [],
        },
    )

    response = client.get("/api/issues/template-status", query_string={"week": "week3"})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["data"]["active_week"] == "week3"


def test_create_missing_api_uses_mocked_github_issue_creation(client, app, monkeypatch):
    repository_id = ensure_user_and_repository(app)
    login_with_current_repository(client, repository_id)

    monkeypatch.setattr(
        "app.routes.issues.create_missing_issues",
        lambda repository, access_token, active_week=None: {
            "template_count": 3,
            "matched_count": 2,
            "missing_count": 0,
            "active_week": active_week or "week2",
            "required_template_count": 2,
            "required_matched_count": 2,
            "required_progress": 1.0,
            "missing_issues": [],
            "created_issues": [
                {
                    "title": "week2 - 테스트 문제",
                    "category": "weekly",
                    "track_type": "problem-solving",
                    "difficulty_level": "low",
                    "requirement_level": "required",
                    "week_label": "week2",
                    "issue_number": 99,
                    "issue_url": "https://github.com/example/issues/99",
                    "state": "open",
                }
            ],
        },
    )

    response = client.post("/api/issues/create-missing", json={"week": "week2"})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["data"]["active_week"] == "week2"
    assert payload["data"]["created_issues"][0]["issue_number"] == 99


def test_title_helpers():
    assert normalize_title("  공통   -   학습 목표 확인 ") == "공통 - 학습 목표 확인".casefold()
    assert classify_issue_title("공통 - 학습 목표 확인") == "common"
    assert classify_issue_title("basic - 배열 연습") == "basic"
    assert infer_difficulty_level("problem-solving 하 - 그래프", "") == "low"
    assert infer_difficulty_level("problem-solving 중 - 문자열", "") == "medium"
    assert infer_difficulty_level("problem-solving 상 - 최단경로", "") == "high"
