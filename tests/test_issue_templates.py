from pathlib import Path

from app.models.db import get_issues_by_repository_id, save_issue, upsert_repository_for_user, upsert_user
from app.services.issue_template_service import (
    build_template_status,
    classify_issue_title,
    create_missing_issues,
    load_issue_templates,
    normalize_title,
)


def ensure_user_and_repository(app):
    with app.app_context():
        upsert_user("5005", "template-user", "템플릿 사용자")
        repository_id = upsert_repository_for_user(
            user_id=1,
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

        result = create_missing_issues(repository, "template-token", tmp_path)
        saved_issues = get_issues_by_repository_id(repository_id)

    assert result["missing_count"] == 0
    assert len(result["created_issues"]) == 2
    assert len(saved_issues) == 2


def test_template_status_api_returns_counts(client, app, tmp_path, monkeypatch):
    repository_id = ensure_user_and_repository(app)
    login_with_current_repository(client, repository_id)
    make_csv(
        tmp_path,
        "week2.csv",
        [("공통 - 학습 목표 확인", "content one"), ("basic - 배열 연습", "content two")],
    )

    monkeypatch.setattr(
        "app.routes.issues.build_template_status",
        lambda repository_id: {
            "template_count": 2,
            "matched_count": 1,
            "missing_count": 1,
            "matched_issues": [],
            "missing_issues": [{"title": "basic - 배열 연습", "content": "content two", "category": "basic"}],
        },
    )

    response = client.get("/api/issues/template-status")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["data"]["template_count"] == 2
    assert payload["data"]["missing_count"] == 1


def test_create_missing_api_uses_mocked_github_issue_creation(client, app, monkeypatch):
    repository_id = ensure_user_and_repository(app)
    login_with_current_repository(client, repository_id)

    monkeypatch.setattr(
        "app.routes.issues.create_missing_issues",
        lambda repository, access_token: {
            "template_count": 3,
            "matched_count": 2,
            "missing_count": 0,
            "missing_issues": [],
            "created_issues": [
                {
                    "title": "week2 - 새 문제",
                    "category": "weekly",
                    "issue_number": 99,
                    "issue_url": "https://github.com/example/issues/99",
                    "state": "open",
                }
            ],
        },
    )

    response = client.post("/api/issues/create-missing")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["data"]["created_issues"][0]["issue_number"] == 99


def test_title_helpers():
    assert normalize_title("  공통   -   학습 목표 확인 ") == "공통 - 학습 목표 확인".casefold()
    assert classify_issue_title("공통 - 학습 목표 확인") == "common"
    assert classify_issue_title("basic - 배열 연습") == "basic"
