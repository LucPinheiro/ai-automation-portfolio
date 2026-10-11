from typing import Any

import httpx
import pytest

from app.config import Settings
from app.core.exceptions import AIProviderNotConfiguredError
from app.services.ai import create_ai_provider
from app.services.ai.ollama_provider import OllamaProvider
from app.services.ai.openai_provider import OpenAIProvider


def make_settings(**overrides: Any) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


def test_openai_provider_is_built_from_settings() -> None:
    settings = make_settings(openai_api_key="sk-test", openai_model="gpt-custom", openai_timeout_seconds=7)

    provider = create_ai_provider(settings)

    assert isinstance(provider, OpenAIProvider)
    assert provider.name == "openai"
    assert provider._model == "gpt-custom"
    assert provider._client.api_key == "sk-test"
    assert provider._client.timeout == 7


def test_missing_api_key_raises_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(AIProviderNotConfiguredError):
        create_ai_provider(make_settings(openai_api_key=None))


def test_openai_is_selected_explicitly() -> None:
    provider = create_ai_provider(make_settings(ai_provider="openai", openai_api_key="sk-test"))

    assert isinstance(provider, OpenAIProvider)


def test_ollama_provider_is_built_from_settings() -> None:
    settings = make_settings(
        ai_provider="ollama",
        ollama_base_url="http://ollama.test:11434",
        ollama_model="llama3.2:3b",
        ollama_timeout_seconds=90,
        ollama_max_output_tokens=800,
    )

    provider = create_ai_provider(settings)

    assert isinstance(provider, OllamaProvider)
    assert provider.name == "ollama"
    assert provider._model == "llama3.2:3b"
    assert provider._max_output_tokens == 800
    assert str(provider._client.base_url) == "http://ollama.test:11434"
    assert provider._client.timeout == httpx.Timeout(90)


def test_ollama_does_not_require_an_openai_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    provider = create_ai_provider(make_settings(ai_provider="ollama", openai_api_key=None))

    assert isinstance(provider, OllamaProvider)


def test_unknown_provider_raises_not_configured() -> None:
    settings = make_settings(openai_api_key="sk-test").model_copy(update={"ai_provider": "unknown"})

    with pytest.raises(AIProviderNotConfiguredError):
        create_ai_provider(settings)
