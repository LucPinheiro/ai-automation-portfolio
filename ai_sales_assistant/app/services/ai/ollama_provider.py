import logging
import time

import httpx

from app.core.exceptions import AIProviderError
from app.prompts.base import Prompt
from app.services.ai.base import AIResult

logger = logging.getLogger(__name__)


class OllamaProvider:
    """AI provider adapter backed by the local Ollama chat API (`POST /api/chat`)."""

    name = "ollama"

    def __init__(self, client: httpx.Client, model: str, max_output_tokens: int) -> None:
        # The client carries the base URL and timeout, so the adapter only builds requests.
        self._client = client
        self._model = model
        self._max_output_tokens = max_output_tokens

    def generate(self, prompt: Prompt) -> AIResult:
        started = time.perf_counter()
        try:
            response = self._client.post(
                "/api/chat",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": prompt.system},
                        {"role": "user", "content": prompt.user},
                    ],
                    "stream": False,
                    "options": {"num_predict": self._max_output_tokens},
                },
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            self._log_failure(exc, exc.response.status_code)
            raise AIProviderError() from exc
        except (httpx.HTTPError, ValueError) as exc:
            # ValueError covers a body that is not valid JSON.
            self._log_failure(exc, None)
            raise AIProviderError() from exc

        message = data.get("message") if isinstance(data, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        content = content.strip() if isinstance(content, str) else ""
        if not content:
            logger.error("Ollama returned an empty response (model=%s)", self._model)
            raise AIProviderError()

        result = AIResult(
            content=content,
            provider=self.name,
            model=data.get("model") or self._model,
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
        )
        self._log_success(result, data.get("done_reason"), started)
        return result

    def _log_failure(self, exc: Exception, status_code: int | None) -> None:
        # Only the error class and HTTP status are logged: error bodies may echo the prompt.
        logger.error(
            "Ollama request failed (model=%s, error=%s, status_code=%s)",
            self._model,
            type(exc).__name__,
            status_code,
        )

    def _log_success(self, result: AIResult, done_reason: str | None, started: float) -> None:
        # Prompt and generated content contain customer data and are never logged.
        logger.info(
            "Ollama generation completed (model=%s, done_reason=%s, input_tokens=%s, output_tokens=%s, duration_ms=%d)",
            result.model,
            done_reason,
            result.prompt_tokens,
            result.completion_tokens,
            (time.perf_counter() - started) * 1000,
        )
