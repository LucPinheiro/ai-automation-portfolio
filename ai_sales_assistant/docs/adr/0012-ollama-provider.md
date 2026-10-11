# 0012. Ollama as a local AI provider

- Status: Accepted
- Date: 2026-10-07

## Context

Generating content only through OpenAI requires an API key, has a per-token cost and sends customer data to an external vendor. A local model removes all three, at the cost of quality and speed. Ollama runs open models (e.g. `llama3.2:3b`) locally and exposes an HTTP API. The `AIProvider` abstraction ([ADR 0008](0008-ai-provider-abstraction.md)) was designed for this.

## Decision

`OllamaProvider` (`app/services/ai/ollama_provider.py`) implements `AIProvider` and is registered in the factory as `"ollama"`. `AI_PROVIDER` selects it; OpenAI remains the default and is unchanged.

It calls the native chat endpoint `POST {OLLAMA_BASE_URL}/api/chat` with `httpx`:

| Field | Value |
| ----- | ----- |
| `model` | `OLLAMA_MODEL` (default `llama3.2:3b`) |
| `messages` | `system`: the shared system prompt; `user`: the rendered user prompt |
| `stream` | `false`: the whole answer is returned in one response |
| `options.num_predict` | `OLLAMA_MAX_OUTPUT_TOKENS` |

- `message.content` is the generated content. An empty or malformed answer is treated as a provider error.
- `prompt_eval_count` and `eval_count` are stored as prompt and completion tokens; the model reported by Ollama is stored as `ai_model`.
- The `httpx.Client` is created with `OLLAMA_BASE_URL` and `OLLAMA_TIMEOUT_SECONDS` (default 120, since local models are slower than hosted APIs). It is reused like the OpenAI client.
- No API key is needed, so `AIProviderNotConfiguredError` never applies to Ollama.
- Connection errors, timeouts, HTTP errors (e.g. 404 when the model is not installed) and invalid JSON become `AIProviderError` (HTTP 502). Only the error class and HTTP status are logged, never the response body, the prompt or the generated content.
- Prompts, `GenerationService`, endpoints, error format and the database schema are shared with OpenAI and did not change.

## Consequences

- Positive: content can be generated offline, at no cost and without sending customer data to a third party.
- Positive: no new dependency; `httpx` was already installed with the OpenAI SDK and is now declared explicitly.
- Positive: tests use `httpx.MockTransport`, so they never reach a real Ollama server.
- Negative: small local models produce lower-quality text and may follow the prompt rules less strictly than hosted models.
- Negative: the request is synchronous and occupies a worker thread for the whole (possibly long) generation.

## Alternatives considered

- **Official `ollama` Python package**: an extra dependency for a single HTTP call.
- **Ollama's OpenAI-compatible endpoint (`/v1`) through the OpenAI SDK**: would mix both providers in one adapter and depends on which OpenAI endpoints the installed Ollama version supports.
- **Streaming responses**: not needed while the API returns the full content in one response.
