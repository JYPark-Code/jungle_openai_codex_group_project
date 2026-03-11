from app.models.db import get_user_by_github_user_id, upsert_user
from app.services.auth_service import handle_github_callback


def test_handle_github_callback_returns_token_and_user(monkeypatch):
    def fake_exchange_code_for_access_token(code, client_id, client_secret, redirect_uri):
        assert code == "auth-code"
        return "access-token"

    def fake_fetch_github_user(access_token):
        assert access_token == "access-token"
        return {
            "id": 1001,
            "login": "jungle-user",
            "name": "정글 유저",
        }

    monkeypatch.setattr(
        "app.services.auth_service.exchange_code_for_access_token",
        fake_exchange_code_for_access_token,
    )
    monkeypatch.setattr(
        "app.services.auth_service.fetch_github_user",
        fake_fetch_github_user,
    )

    result = handle_github_callback(
        code="auth-code",
        received_state="same-state",
        expected_state="same-state",
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="http://localhost/callback",
    )

    assert result["access_token"] == "access-token"
    assert result["github_user"]["login"] == "jungle-user"


def test_upsert_user_does_not_create_duplicate(app):
    with app.app_context():
        first_id = upsert_user("1001", "jungle-user", "정글 유저")
        second_id = upsert_user("1001", "jungle-user", "정글 유저 수정")
        saved_user = get_user_by_github_user_id("1001")

    assert first_id == second_id
    assert saved_user["github_name"] == "정글 유저 수정"


def test_auth_me_returns_logged_in_user(client, monkeypatch):
    def fake_exchange_code_for_access_token(code, client_id, client_secret, redirect_uri):
        return "session-token"

    def fake_fetch_github_user(access_token):
        return {
            "id": 2002,
            "login": "oauth-user",
            "name": "OAuth 사용자",
        }

    monkeypatch.setattr(
        "app.services.auth_service.exchange_code_for_access_token",
        fake_exchange_code_for_access_token,
    )
    monkeypatch.setattr(
        "app.services.auth_service.fetch_github_user",
        fake_fetch_github_user,
    )

    login_response = client.get("/api/auth/github/login")
    assert login_response.status_code == 200
    state = login_response.get_json()["data"]["state"]

    callback_response = client.get(
        "/api/auth/github/callback",
        query_string={"code": "valid-code", "state": state},
    )
    assert callback_response.status_code == 200

    me_response = client.get("/api/auth/me")
    payload = me_response.get_json()

    assert me_response.status_code == 200
    assert payload["data"]["user"]["github_login"] == "oauth-user"
