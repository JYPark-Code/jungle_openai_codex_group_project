from urllib.parse import parse_qs, urlparse

from app.models.db import get_user_by_github_user_id, upsert_repository_for_user, upsert_user
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
            "name": "정글 사용자",
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
        first_id = upsert_user("1001", "jungle-user", "정글 사용자")
        second_id = upsert_user("1001", "jungle-user", "정글 사용자 수정")
        saved_user = get_user_by_github_user_id("1001")

    assert first_id == second_id
    assert saved_user["github_name"] == "정글 사용자 수정"


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


def test_github_login_redirect_mode_returns_github_redirect(client):
    response = client.get(
        "/api/auth/github/login",
        query_string={
            "mode": "redirect",
            "next": "http://localhost:3000/auth/callback",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].startswith("https://github.com/login/oauth/authorize")


def test_github_callback_redirect_mode_redirects_to_frontend_success(client, monkeypatch):
    def fake_exchange_code_for_access_token(code, client_id, client_secret, redirect_uri):
        return "session-token"

    def fake_fetch_github_user(access_token):
        return {
            "id": 2003,
            "login": "redirect-user",
            "name": "리다이렉트 사용자",
        }

    monkeypatch.setattr(
        "app.services.auth_service.exchange_code_for_access_token",
        fake_exchange_code_for_access_token,
    )
    monkeypatch.setattr(
        "app.services.auth_service.fetch_github_user",
        fake_fetch_github_user,
    )

    login_response = client.get(
        "/api/auth/github/login",
        query_string={
            "mode": "redirect",
            "next": "http://localhost:3000/auth/callback?from=github",
        },
    )
    state = parse_qs(urlparse(login_response.headers["Location"]).query)["state"][0]

    callback_response = client.get(
        "/api/auth/github/callback",
        query_string={"code": "valid-code", "state": state},
    )

    assert callback_response.status_code == 302
    redirected_url = urlparse(callback_response.headers["Location"])
    query = parse_qs(redirected_url.query)
    assert redirected_url.scheme == "http"
    assert redirected_url.netloc == "localhost:3000"
    assert redirected_url.path == "/auth/callback"
    assert query["status"] == ["success"]
    assert query["from"] == ["github"]


def test_github_callback_redirect_mode_redirects_to_frontend_failure(client):
    login_response = client.get(
        "/api/auth/github/login",
        query_string={
            "mode": "redirect",
            "next": "http://localhost:3000/auth/callback",
        },
    )
    state = parse_qs(urlparse(login_response.headers["Location"]).query)["state"][0]

    callback_response = client.get(
        "/api/auth/github/callback",
        query_string={"code": "", "state": state},
    )

    assert callback_response.status_code == 302
    redirected_url = urlparse(callback_response.headers["Location"])
    query = parse_qs(redirected_url.query)
    assert redirected_url.path == "/login"
    assert query["status"] == ["error"]
    assert query["code"] == ["GITHUB_CODE_MISSING"]


def test_auth_cors_allows_frontend_origin(client):
    response = client.options(
        "/api/auth/me",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert response.headers["Access-Control-Allow-Credentials"] == "true"


def test_relogin_restores_current_repository_from_db(client, app, monkeypatch):
    def fake_exchange_code_for_access_token(code, client_id, client_secret, redirect_uri):
        return "session-token"

    def fake_fetch_github_user(access_token):
        return {
            "id": 3001,
            "login": "repeat-user",
            "name": "재로그인 사용자",
        }

    monkeypatch.setattr(
        "app.services.auth_service.exchange_code_for_access_token",
        fake_exchange_code_for_access_token,
    )
    monkeypatch.setattr(
        "app.services.auth_service.fetch_github_user",
        fake_fetch_github_user,
    )

    first_login_response = client.get("/api/auth/github/login")
    first_state = first_login_response.get_json()["data"]["state"]
    first_callback_response = client.get(
        "/api/auth/github/callback",
        query_string={"code": "valid-code", "state": first_state},
    )

    assert first_callback_response.status_code == 200

    with app.app_context():
        saved_user = get_user_by_github_user_id("3001")
        upsert_repository_for_user(
            user_id=saved_user["id"],
            owner="JYPark-Code",
            name="SW-AI-W02-05",
            full_name="JYPark-Code/SW-AI-W02-05",
            github_repo_id="12345",
            default_branch="main",
        )

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 200

    second_login_response = client.get("/api/auth/github/login")
    second_state = second_login_response.get_json()["data"]["state"]
    second_callback_response = client.get(
        "/api/auth/github/callback",
        query_string={"code": "valid-code", "state": second_state},
    )

    assert second_callback_response.status_code == 200

    current_repository_response = client.get("/api/repositories/current")
    payload = current_repository_response.get_json()

    assert current_repository_response.status_code == 200
    assert payload["data"]["repository"]["full_name"] == "JYPark-Code/SW-AI-W02-05"
