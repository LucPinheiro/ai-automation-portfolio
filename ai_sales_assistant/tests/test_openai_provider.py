import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import openai
import pytest

from app.core.exceptions import AIProviderError
from app.prompts.base import Prompt
from app.services.ai.openai_provider import OpenAIProvider

SECRET_KEY = "sk-proj-super-secret-key"
PROMPT = Prompt(system="System rules", user="Customer: María López, confidential needs")
REQUEST = httpx.Request("POST", "https://api.openai.com/v1/responses")
DEFAULT_USAGE = SimpleNamespace(input_tokens=120, output_tokens=80)


def fake_response(
    output_text: str = "Estimada María, ...",
    usage: SimpleNamespace | None = DEFAULT_USAGE,
    model: str = "gpt-test-2026-01-01",
) -> SimpleNamespace:
    return SimpleNamespace(output_text=output_text, usage=usage, model=model, status="completed")


def status_error(error_class: type[openai.APIStatusError], status_code: int, message: str) -> Exception:
    response = httpx.Response(status_code, request=REQUEST, headers={"x-request-id": "req_123"})
    return error_class(message, response=response, body=None)


@pytest.fixture
def client() -> MagicMock:
    mock = MagicMock()
    mock.responses.create.return_value = fake_response()
    return mock


@pytest.fixture
def provider(client: MagicMock) -> OpenAIProvider:
    return OpenAIProvider(client=client, model="gpt-test", max_output_tokens=500)


def test_generate_sends_prompt_to_responses_api(provider: OpenAIProvider, client: MagicMock) -> None:
    provider.generate(PROMPT)

    client.responses.create.assert_called_once_with(
        model="gpt-test",
        instructions="System rules",
        input=PROMPT.user,
        max_output_tokens=500,
        store=False,
    )


def test_generate_returns_content_model_and_usage(provider: OpenAIProvider) -> None:
    result = provider.generate(PROMPT)

    assert result.content == "Estimada María, ..."
    assert result.provider == "openai"
    assert result.model == "gpt-test-2026-01-01"
    assert (result.prompt_tokens, result.completion_tokens) == (120, 80)


def test_generate_strips_surrounding_whitespace(provider: OpenAIProvider, client: MagicMock) -> None:
    client.responses.create.return_value = fake_response(output_text="\n  Hola  \n")

    assert provider.generate(PROMPT).content == "Hola"


def test_missing_usage_is_reported_as_none(provider: OpenAIProvider, client: MagicMock) -> None:
    client.responses.create.return_value = fake_response(usage=None)

    result = provider.generate(PROMPT)

    assert (result.prompt_tokens, result.completion_tokens) == (None, None)


@pytest.mark.parametrize("output_text", ["", "   ", None])
def test_empty_output_raises_provider_error(
    provider: OpenAIProvider, client: MagicMock, output_text: str | None
) -> None:
    client.responses.create.return_value = fake_response(output_text=output_text)  # type: ignore[arg-type]

    with pytest.raises(AIProviderError):
        provider.generate(PROMPT)


@pytest.mark.parametrize(
    "error",
    [
        openai.APITimeoutError(request=REQUEST),
        openai.APIConnectionError(request=REQUEST),
        status_error(openai.RateLimitError, 429, "Rate limit reached"),
        status_error(openai.AuthenticationError, 401, f"Incorrect API key provided: {SECRET_KEY}"),
        status_error(openai.BadRequestError, 400, "Invalid model"),
        status_error(openai.InternalServerError, 500, "Server error"),
    ],
    ids=["timeout", "connection", "rate_limit", "authentication", "bad_request", "server_error"],
)
def test_sdk_errors_become_generic_provider_errors(
    provider: OpenAIProvider, client: MagicMock, error: Exception
) -> None:
    client.responses.create.side_effect = error

    with pytest.raises(AIProviderError) as exc_info:
        provider.generate(PROMPT)

    assert exc_info.value.message == AIProviderError.default_message
    assert SECRET_KEY not in str(exc_info.value)


def test_failure_log_has_diagnostics_but_no_secrets(
    provider: OpenAIProvider, client: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    client.responses.create.side_effect = status_error(
        openai.AuthenticationError, 401, f"Incorrect API key provided: {SECRET_KEY}"
    )

    with caplog.at_level(logging.INFO), pytest.raises(AIProviderError):
        provider.generate(PROMPT)

    assert "AuthenticationError" in caplog.text
    assert "status_code=401" in caplog.text
    assert "request_id=req_123" in caplog.text
    assert SECRET_KEY not in caplog.text
    assert "María" not in caplog.text


def test_success_log_never_contains_prompt_or_content(
    provider: OpenAIProvider, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO):
        provider.generate(PROMPT)

    assert "input_tokens=120" in caplog.text
    assert "María" not in caplog.text
    assert "confidential" not in caplog.text
