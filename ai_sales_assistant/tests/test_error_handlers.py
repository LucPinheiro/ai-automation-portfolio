import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.core.error_handlers import register_exception_handlers
from app.core.exceptions import (
    AIProviderError,
    AIProviderNotConfiguredError,
    BadRequestError,
    NotFoundError,
)

SECRET = "sk-secret-value-that-must-not-leak"


class Payload(BaseModel):
    name: str = Field(min_length=1, max_length=10)
    quantity: int


def build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/bad-request")
    def bad_request() -> None:
        raise BadRequestError("Invalid filter combination.")

    @app.get("/not-found")
    def not_found() -> None:
        raise NotFoundError("Generation 99 was not found.")

    @app.get("/ai-provider-error")
    def ai_provider_error() -> None:
        raise AIProviderError()

    @app.get("/ai-provider-not-configured")
    def ai_provider_not_configured() -> None:
        raise AIProviderNotConfiguredError()

    @app.get("/crash")
    def crash() -> None:
        raise RuntimeError(f"database password is {SECRET}")

    @app.post("/payload")
    def payload(data: Payload) -> Payload:
        return data

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(build_app(), raise_server_exceptions=False)


def test_bad_request_error_returns_400(client: TestClient) -> None:
    response = client.get("/bad-request")

    assert response.status_code == 400
    assert response.json() == {
        "error": {"code": "bad_request", "message": "Invalid filter combination.", "details": []}
    }


def test_not_found_error_returns_404(client: TestClient) -> None:
    response = client.get("/not-found")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.json()["error"]["message"] == "Generation 99 was not found."


def test_ai_provider_error_returns_502_with_generic_message(client: TestClient) -> None:
    response = client.get("/ai-provider-error")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "ai_provider_error"
    assert response.json()["error"]["message"] == AIProviderError.default_message


def test_ai_provider_not_configured_returns_503(client: TestClient) -> None:
    response = client.get("/ai-provider-not-configured")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ai_provider_not_configured"


def test_ai_provider_not_configured_is_an_ai_provider_error() -> None:
    assert issubclass(AIProviderNotConfiguredError, AIProviderError)


def test_validation_error_returns_422_with_field_details(client: TestClient) -> None:
    response = client.post("/payload", json={"name": "", "quantity": "many"})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    fields = {detail["field"]: detail["type"] for detail in error["details"]}
    assert fields == {"name": "string_too_short", "quantity": "int_parsing"}


def test_validation_error_does_not_echo_submitted_input(client: TestClient) -> None:
    response = client.post("/payload", json={"name": SECRET, "quantity": 1})

    assert response.status_code == 422
    assert SECRET not in response.text


def test_missing_field_is_reported(client: TestClient) -> None:
    response = client.post("/payload", json={"name": "ok"})

    assert response.status_code == 422
    assert response.json()["error"]["details"][0] == {
        "field": "quantity",
        "message": "Field required",
        "type": "missing",
    }


def test_malformed_json_returns_400(client: TestClient) -> None:
    response = client.post("/payload", content=b"{not json", headers={"Content-Type": "application/json"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_json"


def test_unhandled_exception_returns_500_without_leaking_details(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR):
        response = client.get("/crash")

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "An unexpected error occurred.", "details": []}
    }
    assert SECRET not in response.text
    assert "Traceback" not in response.text
    assert "Unhandled error" in caplog.text


def test_unknown_route_uses_common_error_format(client: TestClient) -> None:
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_method_not_allowed_uses_common_error_format(client: TestClient) -> None:
    response = client.delete("/not-found")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"
