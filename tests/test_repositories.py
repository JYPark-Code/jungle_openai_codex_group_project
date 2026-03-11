from app.models.db import get_repository_by_id, upsert_repository_for_user


def login_session(client):
    with client.session_transaction() as session:
        session["auth_user_id"] = 1
        session["oauth_access_token"] = "oauth-session-token"


def ensure_logged_in_user(app):
    from app.models.db import upsert_user

    with app.app_context():
        upsert_user("3003", "repo-user", "레포 사용자")


def test_fetch_user_repositories_api_returns_list(client, app, monkeypatch):
    ensure_logged_in_user(app)
    login_session(client)

    def fake_fetch_user_repositories(access_token):
        assert access_token == "oauth-session-token"
        return [
            {
                "github_repo_id": "123",
                "owner": "JYPark-Code",
                "name": "SW-AI-W02-05",
                "full_name": "JYPark-Code/SW-AI-W02-05",
                "default_branch": "main",
                "private": False,
            }
        ]

    monkeypatch.setattr(
        "app.routes.repositories.fetch_user_repositories",
        fake_fetch_user_repositories,
    )

    response = client.get("/api/repositories")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["data"]["repositories"][0]["full_name"] == "JYPark-Code/SW-AI-W02-05"


def test_select_repository_saves_to_db_and_session(client, app):
    ensure_logged_in_user(app)
    login_session(client)

    response = client.post(
        "/api/repositories/select",
        json={
            "github_repo_id": "123",
            "owner": "JYPark-Code",
            "name": "SW-AI-W02-05",
            "full_name": "JYPark-Code/SW-AI-W02-05",
            "default_branch": "main",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["data"]["repository"]["full_name"] == "JYPark-Code/SW-AI-W02-05"

    with client.session_transaction() as session:
        repository_id = session["current_repository_id"]
        assert session["current_repository_full_name"] == "JYPark-Code/SW-AI-W02-05"

    with app.app_context():
        saved_repository = get_repository_by_id(repository_id)

    assert saved_repository["user_id"] == 1
    assert saved_repository["name"] == "SW-AI-W02-05"
    assert saved_repository["last_synced_at"] is None


def test_select_repository_does_not_create_duplicate(app):
    with app.app_context():
        from app.models.db import upsert_user

        upsert_user("3003", "repo-user", "레포 사용자")
        first_id = upsert_repository_for_user(
            user_id=1,
            owner="JYPark-Code",
            name="SW-AI-W02-05",
            full_name="JYPark-Code/SW-AI-W02-05",
            github_repo_id="123",
            default_branch="main",
        )
        second_id = upsert_repository_for_user(
            user_id=1,
            owner="JYPark-Code",
            name="SW-AI-W02-05",
            full_name="JYPark-Code/SW-AI-W02-05",
            github_repo_id="123",
            default_branch="main",
        )

    assert first_id == second_id


def test_select_repository_reuses_existing_row_from_another_user(app):
    with app.app_context():
        from app.models.db import upsert_user

        first_user_id = upsert_user("3003", "repo-user", "레포 사용자")
        second_user_id = upsert_user("3004", "repo-user-2", "두번째 사용자")

        first_repository_id = upsert_repository_for_user(
            user_id=first_user_id,
            owner="JYPark-Code",
            name="SW-AI-W02-05",
            full_name="JYPark-Code/SW-AI-W02-05",
            github_repo_id="123",
            default_branch="main",
        )
        second_repository_id = upsert_repository_for_user(
            user_id=second_user_id,
            owner="JYPark-Code",
            name="SW-AI-W02-05",
            full_name="JYPark-Code/SW-AI-W02-05",
            github_repo_id="123",
            default_branch="main",
        )
        saved_repository = get_repository_by_id(second_repository_id)

    assert first_repository_id == second_repository_id
    assert saved_repository["user_id"] == second_user_id


def test_current_repository_returns_selected_repository(client, app):
    ensure_logged_in_user(app)
    login_session(client)

    with app.app_context():
        repository_id = upsert_repository_for_user(
            user_id=1,
            owner="JYPark-Code",
            name="SW-AI-W02-05",
            full_name="JYPark-Code/SW-AI-W02-05",
            github_repo_id="123",
            default_branch="main",
        )

    with client.session_transaction() as session:
        session["current_repository_id"] = repository_id
        session["current_repository_full_name"] = "JYPark-Code/SW-AI-W02-05"

    response = client.get("/api/repositories/current")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["data"]["repository"]["full_name"] == "JYPark-Code/SW-AI-W02-05"
