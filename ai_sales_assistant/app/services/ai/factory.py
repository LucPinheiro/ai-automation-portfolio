from collections.abc import Callable

import httpx
from openai import OpenAI

from app.config import Settings
from app.core.exceptions import AIProviderNotConfiguredError
from app.services.ai.base import AIProvider
from app.services.ai.ollama_provider import OllamaProvider
from app.services.ai.openai_provider import OpenAIProvider


def _build_openai_provider(settings: Settings) -> AIProvider:
    if settings.openai_api_key is None:
        raise AIProviderNotConfiguredError()
    client = OpenAI(
        api_key=settings.openai_api_key.get_secret_value(),
        timeout=settings.openai_timeout_seconds,
    )
    return OpenAIProvider(
        client=client,
        model=settings.openai_model,
        max_output_tokens=settings.openai_max_output_tokens,
    )


def _build_ollama_provider(settings: Settings) -> AIProvider:
    # Ollama runs locally and needs no credentials.
    client = httpx.Client(
        base_url=settings.ollama_base_url,
        timeout=settings.ollama_timeout_seconds,
    )
    return OllamaProvider(
        client=client,
        model=settings.ollama_model,
        max_output_tokens=settings.ollama_max_output_tokens,
    )


# New providers are added here and in Settings.ai_provider.
_PROVIDER_BUILDERS: dict[str, Callable[[Settings], AIProvider]] = {
    "openai": _build_openai_provider,
    "ollama": _build_ollama_provider,
}


def create_ai_provider(settings: Settings) -> AIProvider:
    """Build the AI provider selected by the `AI_PROVIDER` setting.

    Raises `AIProviderNotConfiguredError` when the provider lacks its credentials.
    """
    builder = _PROVIDER_BUILDERS.get(settings.ai_provider)
    if builder is None:
        raise AIProviderNotConfiguredError(f"Unsupported AI provider: {settings.ai_provider}.")
    return builder(settings)
