import logging
import time

import openai
from openai import OpenAI

from app.core.exceptions import AIProviderError
from app.prompts.base import Prompt
from app.services.ai.base import AIResult

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """AI provider adapter backed by the OpenAI Responses API."""

    name = "openai"

    def __init__(self, client: OpenAI, model: str, max_output_tokens: int) -> None:
        self._client = client
        self._model = model
        self._max_output_tokens = max_output_tokens

    def generate(self, prompt: Prompt) -> AIResult:
        started = time.perf_counter()
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=prompt.system,
                input=prompt.user,
                max_output_tokens=self._max_output_tokens,
                store=False,
            )
        except openai.OpenAIError as exc:
            self._log_failure(exc)
            raise AIProviderError() from exc

        content = (response.output_text or "").strip()
        if not content:
            logger.error("OpenAI returned an empty response (model=%s, status=%s)", self._model, response.status)
            raise AIProviderError()

        usage = response.usage
        result = AIResult(
            content=content,
            provider=self.name,
            model=response.model or self._model,
            prompt_tokens=usage.input_tokens if usage else None,
            completion_tokens=usage.output_tokens if usage else None,
        )
        self._log_success(result, response.status, started)
        return result

    def _log_failure(self, exc: openai.OpenAIError) -> None:
        # Only the error class, HTTP status and request id are logged: provider error
        # messages may include fragments of credentials or of the prompt.
        logger.error(
            "OpenAI request failed (model=%s, error=%s, status_code=%s, request_id=%s)",
            self._model,
            type(exc).__name__,
            getattr(exc, "status_code", None),
            getattr(exc, "request_id", None),
        )

    def _log_success(self, result: AIResult, status: str | None, started: float) -> None:
        # Prompt and generated content contain customer data and are never logged.
        logger.info(
            "OpenAI generation completed (model=%s, status=%s, input_tokens=%s, output_tokens=%s, duration_ms=%d)",
            result.model,
            status,
            result.prompt_tokens,
            result.completion_tokens,
            (time.perf_counter() - started) * 1000,
        )
