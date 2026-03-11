def ensure_user_and_repository(app):
    from app.models.db import upsert_repository_for_user, upsert_user

    with app.app_context():
        upsert_user("4004", "sync-user", "동기화 사용자")
        repository_id = upsert_repository_for_user(
            user_id=1,
            owner="JYPark-Code",
            name="SW-AI-W02-05",
            full_name="JYPark-Code/SW-AI-W02-05",
            github_repo_id="999",
            default_branch="main",
        )
    return repository_id


def login_with_current_repository(client, repository_id):
    with client.session_transaction() as session:
        session["auth_user_id"] = 1
        session["oauth_access_token"] = "sync-token"
        session["current_repository_id"] = repository_id
        session["current_repository_full_name"] = "JYPark-Code/SW-AI-W02-05"


def test_repository_sync_saves_issues_and_commits(client, app, monkeypatch):
    repository_id = ensure_user_and_repository(app)
    login_with_current_repository(client, repository_id)

    monkeypatch.setattr(
        "app.services.sync_service.fetch_repository_issues",
        lambda owner, name, access_token: [
            {
                "github_issue_id": "100",
                "issue_number": 11,
                "title": "week2 문제",
                "body": "week2 content",
                "state": "open",
                "created_at": "2026-03-11T10:00:00Z",
            }
        ],
    )
    monkeypatch.setattr(
        "app.services.sync_service.fetch_repository_commits",
        lambda owner, name, access_token: [
            {
                "sha": "abc123",
                "message": "week2 solution",
                "author_name": "JYPark",
                "committed_at": "2026-03-11T11:00:00Z",
                "analyzed_at": None,
            }
        ],
    )

    response = client.post("/api/repositories/current/sync")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["data"]["new_issue_count"] == 1
    assert payload["data"]["new_commit_count"] == 1
    assert payload["data"]["last_synced_at"] is not None


def test_repository_sync_does_not_duplicate_existing_records(client, app, monkeypatch):
    repository_id = ensure_user_and_repository(app)
    login_with_current_repository(client, repository_id)

    issues = [
        {
            "github_issue_id": "100",
            "issue_number": 11,
            "title": "week2 문제",
            "body": "week2 content",
            "state": "open",
            "created_at": "2026-03-11T10:00:00Z",
        }
    ]
    commits = [
        {
            "sha": "abc123",
            "message": "week2 solution",
            "author_name": "JYPark",
            "committed_at": "2026-03-11T11:00:00Z",
            "analyzed_at": None,
        }
    ]

    monkeypatch.setattr("app.services.sync_service.fetch_repository_issues", lambda owner, name, access_token: issues)
    monkeypatch.setattr("app.services.sync_service.fetch_repository_commits", lambda owner, name, access_token: commits)

    first_response = client.post("/api/repositories/current/sync")
    second_response = client.post("/api/repositories/current/sync")

    assert first_response.get_json()["data"]["new_issue_count"] == 1
    assert first_response.get_json()["data"]["new_commit_count"] == 1
    assert second_response.get_json()["data"]["new_issue_count"] == 0
    assert second_response.get_json()["data"]["new_commit_count"] == 0


def test_sync_status_returns_cached_counts(client, app, monkeypatch):
    repository_id = ensure_user_and_repository(app)
    login_with_current_repository(client, repository_id)

    monkeypatch.setattr(
        "app.services.sync_service.fetch_repository_issues",
        lambda owner, name, access_token: [
            {
                "github_issue_id": "100",
                "issue_number": 11,
                "title": "week2 문제",
                "body": "week2 content",
                "state": "open",
                "created_at": "2026-03-11T10:00:00Z",
            }
        ],
    )
    monkeypatch.setattr(
        "app.services.sync_service.fetch_repository_commits",
        lambda owner, name, access_token: [
            {
                "sha": "abc123",
                "message": "week2 solution",
                "author_name": "JYPark",
                "committed_at": "2026-03-11T11:00:00Z",
                "analyzed_at": None,
            }
        ],
    )

    client.post("/api/repositories/current/sync")
    response = client.get("/api/repositories/current/sync-status")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["data"]["issue_count"] == 1
    assert payload["data"]["commit_count"] == 1
    assert payload["data"]["last_synced_at"] is not None


def test_sync_service_uses_mocked_github_api(app, monkeypatch):
    from app.models.db import get_sync_status
    from app.services.sync_service import sync_repository_issues_and_commits

    repository_id = ensure_user_and_repository(app)

    monkeypatch.setattr(
        "app.services.sync_service.fetch_repository_issues",
        lambda owner, name, access_token: [],
    )
    monkeypatch.setattr(
        "app.services.sync_service.fetch_repository_commits",
        lambda owner, name, access_token: [],
    )

    with app.app_context():
        result = sync_repository_issues_and_commits(
            {
                "id": repository_id,
                "owner": "JYPark-Code",
                "name": "SW-AI-W02-05",
            },
            "sync-token",
        )
        status = get_sync_status(repository_id)

    assert result["new_issue_count"] == 0
    assert result["new_commit_count"] == 0
    assert status["issue_count"] == 0
    assert status["commit_count"] == 0


def test_repository_sync_saves_project_status_from_tracked_project(client, app, monkeypatch):
    from app.models.db import get_issues_by_repository_id, save_github_project_tracking

    repository_id = ensure_user_and_repository(app)
    login_with_current_repository(client, repository_id)

    with app.app_context():
        save_github_project_tracking(
            repository_id=repository_id,
            week_label="week2",
            project_title="Week 2 Tracking",
            project_url="https://github.com/orgs/JYPark-Code/projects/3",
            project_number="3",
            is_active=True,
        )

    monkeypatch.setattr(
        "app.services.sync_service.fetch_repository_issues",
        lambda owner, name, access_token: [
            {
                "github_issue_id": "100",
                "issue_number": 11,
                "title": "week2 문제",
                "body": "week2 content",
                "state": "open",
                "project_status": "",
                "created_at": "2026-03-11T10:00:00Z",
            }
        ],
    )
    monkeypatch.setattr(
        "app.services.sync_service.fetch_repository_commits",
        lambda owner, name, access_token: [],
    )
    monkeypatch.setattr(
        "app.services.sync_service.fetch_project_item_statuses",
        lambda project_owner, project_number, repo_owner, repo_name, access_token: {11: "Done"},
    )

    response = client.post("/api/repositories/current/sync")

    assert response.status_code == 200

    with app.app_context():
        issues = get_issues_by_repository_id(repository_id)

    assert issues[0]["project_status"] == "Done"
