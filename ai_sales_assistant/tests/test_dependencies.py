from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api import dependencies
from app.config import get_settings
from app.core.exceptions import AIProviderNotConfiguredError
from app.database import get_db
from app.main import app
from app.services.ai import factory
from app.services.ai.ollama_provider import OllamaProvider
from tests.factories import generation_payload, register
from tests.fakes import FakeAIProvider

OLLAMA_URL = "http://ollama.test:11434"


@pytest.fixture(autouse=True)
def clear_provider_cache() -> Iterator[None]:
    get_settings.cache_clear()
    dependencies.get_ai_provider.cache_clear()
    yield
    get_settings.cache_clear()
    dependencies.get_ai_provider.cache_clear()


@pytest.fixture
def ollama_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A throwaway .env in the working directory, as `uvicorn` would read it.
    (tmp_path / ".env").write_text(
        f"AI_PROVIDER=ollama\nOLLAMA_BASE_URL={OLLAMA_URL}\nOLLAMA_MODEL=llama3.2:3b\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    for name in ("AI_PROVIDER", "OLLAMA_BASE_URL", "OLLAMA_MODEL", "OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def test_ai_provider_instance_is_reused(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[FakeAIProvider] = []

    def fake_factory(_settings: object) -> FakeAIProvider:
        created.append(FakeAIProvider())
        return created[-1]

    monkeypatch.setattr(dependencies, "create_ai_provider", fake_factory)

    first = dependencies.get_ai_provider()
    second = dependencies.get_ai_provider()

    assert first is second
    assert len(created) == 1


def test_provider_creation_failure_is_not_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[int] = []

    def failing_factory(_settings: object) -> FakeAIProvider:
        attempts.append(1)
        raise AIProviderNotConfiguredError()

    monkeypatch.setattr(dependencies, "create_ai_provider", failing_factory)

    for _ in range(2):
        with pytest.raises(AIProviderNotConfiguredError):
            dependencies.get_ai_provider()

    assert len(attempts) == 2


def test_resolver_returns_the_cached_provider_getter() -> None:
    assert dependencies.get_ai_provider_resolver() is dependencies.get_ai_provider


def test_ai_provider_env_file_selects_ollama_at_runtime(ollama_env_file: None) -> None:
    provider = dependencies.get_ai_provider()

    assert isinstance(provider, OllamaProvider)
    assert str(provider._client.base_url) == OLLAMA_URL


def test_generate_endpoint_calls_ollama_when_selected(
    ollama_env_file: None, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "model": "llama3.2:3b",
                "message": {"role": "assistant", "content": "Estimada María, ..."},
                "done": True,
                "prompt_eval_count": 10,
                "eval_count": 5,
            },
        )

    real_client = httpx.Client

    def mocked_client(**kwargs: Any) -> httpx.Client:
        # MockTransport keeps the request in-process: no real Ollama or OpenAI call.
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(factory.httpx, "Client", mocked_client)
    # Only the database is overridden; the AI provider comes from the real dependency chain.
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        with TestClient(app) as client:
            register(client)  # generation requires a logged-in user
            response = client.post("/api/v1/generate", json=generation_payload())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201, response.text
    assert response.json()["ai_provider"] == "ollama"
    assert [str(r.url) for r in requests] == [f"{OLLAMA_URL}/api/chat"]
