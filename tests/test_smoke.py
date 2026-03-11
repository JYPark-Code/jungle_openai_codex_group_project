from app.models.db import get_table_names


def test_app_starts_and_returns_health(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["database"]["connected"] is True


def test_database_tables_are_initialized(app):
    with app.app_context():
        table_names = get_table_names()

    assert "users" in table_names
    assert "repositories" in table_names
    assert "analysis_reports" in table_names


def test_not_found_returns_common_error_format(client):
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "NOT_FOUND"
