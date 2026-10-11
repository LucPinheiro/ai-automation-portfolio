import json
import logging
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from app.core.exceptions import AIProviderError
from app.prompts.base import Prompt
from app.services.ai.ollama_provider import OllamaProvider

PROMPT = Prompt(system="System rules", user="Customer: María López, confidential needs")
BASE_URL = "http://ollama.test"


def chat_response(
    content: Any = "Estimada María, ...",
    model: str = "llama3.2:3b",
    prompt_eval_count: int | None = 120,
    eval_count: int | None = 80,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "message": {"role": "assistant", "content": content},
        "done": True,
        "done_reason": "stop",
    }
    if prompt_eval_count is not None:
        body["prompt_eval_count"] = prompt_eval_count
    if eval_count is not None:
        body["eval_count"] = eval_count
    return body


def make_provider(handler: Callable[[httpx.Request], httpx.Response]) -> OllamaProvider:
    # MockTransport answers in-process: no request ever reaches a real Ollama server.
    client = httpx.Client(base_url=BASE_URL, transport=httpx.MockTransport(handler))
    return OllamaProvider(client=client, model="llama3.2:3b", max_output_tokens=500)


def respond_with(body: Any, status_code: int = 200) -> Callable[[httpx.Request], httpx.Response]:
    return lambda request: httpx.Response(status_code, json=body)


def raise_error(error: Exception) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error

    return handler


def test_generate_sends_prompt_to_chat_api() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=chat_response())

    make_provider(handler).generate(PROMPT)

    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert str(requests[0].url) == f"{BASE_URL}/api/chat"
    assert json.loads(requests[0].content) == {
        "model": "llama3.2:3b",
        "messages": [
            {"role": "system", "content": "System rules"},
            {"role": "user", "content": PROMPT.user},
        ],
        "stream": False,
        "options": {"num_predict": 500},
    }


def test_generate_returns_content_model_and_usage() -> None:
    result = make_provider(respond_with(chat_response(model="llama3.2:3b-instruct"))).generate(PROMPT)

    assert result.content == "Estimada María, ..."
    assert result.provider == "ollama"
    assert result.model == "llama3.2:3b-instruct"
    assert (result.prompt_tokens, result.completion_tokens) == (120, 80)


def test_generate_strips_surrounding_whitespace() -> None:
    provider = make_provider(respond_with(chat_response(content="\n  Hola  \n")))

    assert provider.generate(PROMPT).content == "Hola"


def test_missing_usage_is_reported_as_none() -> None:
    provider = make_provider(respond_with(chat_response(prompt_eval_count=None, eval_count=None)))

    result = provider.generate(PROMPT)

    assert (result.prompt_tokens, result.completion_tokens) == (None, None)


def test_missing_model_falls_back_to_configured_model() -> None:
    body = chat_response()
    del body["model"]

    assert make_provider(respond_with(body)).generate(PROMPT).model == "llama3.2:3b"


@pytest.mark.parametrize(
    "body",
    [
        chat_response(content=""),
        chat_response(content="   "),
        chat_response(content=None),
        {"model": "llama3.2:3b", "done": True},
        ["not", "an", "object"],
    ],
    ids=["empty", "blank", "null", "no_message", "not_an_object"],
)
def test_empty_or_malformed_output_raises_provider_error(body: Any) -> None:
    with pytest.raises(AIProviderError):
        make_provider(respond_with(body)).generate(PROMPT)


@pytest.mark.parametrize(
    "handler",
    [
        raise_error(httpx.ConnectError("Connection refused")),
        raise_error(httpx.ReadTimeout("Timed out")),
        respond_with({"error": "model 'llama3.2:3b' not found"}, status_code=404),
        respond_with({"error": "Internal error"}, status_code=500),
        lambda request: httpx.Response(200, content=b"not json"),
    ],
    ids=["connection", "timeout", "model_not_found", "server_error", "invalid_json"],
)
def test_request_failures_become_generic_provider_errors(
    handler: Callable[[httpx.Request], httpx.Response],
) -> None:
    with pytest.raises(AIProviderError) as exc_info:
        make_provider(handler).generate(PROMPT)

    assert exc_info.value.message == AIProviderError.default_message


def test_failure_log_has_diagnostics_but_no_customer_data(caplog: pytest.LogCaptureFixture) -> None:
    provider = make_provider(respond_with({"error": f"bad input: {PROMPT.user}"}, status_code=500))

    with caplog.at_level(logging.INFO), pytest.raises(AIProviderError):
        provider.generate(PROMPT)

    assert "HTTPStatusError" in caplog.text
    assert "status_code=500" in caplog.text
    assert "María" not in caplog.text


def test_success_log_never_contains_prompt_or_content(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        make_provider(respond_with(chat_response())).generate(PROMPT)

    assert "input_tokens=120" in caplog.text
    assert "María" not in caplog.text
    assert "confidential" not in caplog.text
