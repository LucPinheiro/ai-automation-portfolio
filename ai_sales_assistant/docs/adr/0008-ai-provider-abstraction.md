# 0008. AIProvider abstraction

- Status: Accepted
- Date: 2026-10-07

## Context

Routers and services must not depend on OpenAI. The roadmap adds Ollama and Hugging Face (Version 4) and RAG. Tests must never call a real AI service.

## Decision

`app/services/ai/base.py` defines a provider-neutral contract:

```python
@dataclass(frozen=True)
class AIResult:
    content: str
    provider: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None

class AIProvider(Protocol):
    name: str
    def generate(self, prompt: Prompt) -> AIResult: ...
```

- **Adapters translate errors.** Each adapter must convert its SDK- or HTTP-specific failures into `AIProviderError`.
- **A factory selects the adapter.** `create_ai_provider(settings)` in `app/services/ai/factory.py` picks the adapter from `AI_PROVIDER` through a builder registry. It supports `"openai"` (`OpenAIProvider`, [ADR 0007](0007-openai-responses-api.md)) and `"ollama"` (`OllamaProvider`, [ADR 0012](0012-ollama-provider.md)). A missing OpenAI API key raises `AIProviderNotConfiguredError` (HTTP 503); Ollama needs no key.
- **One instance is reused.** `get_ai_provider()` in `app/api/dependencies.py` is cached with `lru_cache`, so the whole process shares one instance and its HTTP connection pool. Creation failures are not cached.
- **Tests use a fake.** `FakeAIProvider` is injected by overriding `get_ai_provider_resolver`; the shared `client` fixture always does so.

## Consequences

- Adding a provider takes three steps: write an adapter that satisfies `AIProvider`, register it in `_PROVIDER_BUILDERS`, and add its name to `Settings.ai_provider`. Services, routers and repositories do not change.
- RAG (Version 4) can be added when building the prompt, before the provider call, without changing this contract.
- The `Prompt` type is plain text (system + user). Multimodal or tool-calling features would require extending the contract.
