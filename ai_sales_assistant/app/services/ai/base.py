from dataclasses import dataclass
from typing import Protocol

from app.prompts.base import Prompt


@dataclass(frozen=True)
class AIResult:
    content: str
    provider: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class AIProvider(Protocol):
    """Contract every AI provider adapter must fulfil.

    Implementations must raise `AIProviderError` (or a subclass) for any provider
    failure, so callers never depend on provider-specific exceptions.
    """

    name: str

    def generate(self, prompt: Prompt) -> AIResult: ...
