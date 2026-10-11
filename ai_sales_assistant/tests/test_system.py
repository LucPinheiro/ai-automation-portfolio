import pytest
from fastapi.testclient import TestClient

from app.config import get_settings


def test_root_returns_api_information(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == get_settings().app_name
    assert body["version"] == get_settings().app_version
    assert body["docs_url"] == "/docs"


def test_health_reports_ok_when_database_is_available(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": get_settings().app_version, "database": "ok"}


def test_health_returns_503_when_database_is_unavailable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.services.health_service.is_database_available", lambda _session: False)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["database"] == "unavailable"


def test_unknown_route_returns_common_error_format(client: TestClient) -> None:
    response = client.get("/unknown")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Not Found", "details": []}}


def test_swagger_documentation_is_available(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").json()["info"]["title"] == get_settings().app_name
