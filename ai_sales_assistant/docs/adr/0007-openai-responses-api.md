# 0007. OpenAI Responses API

- Status: Accepted
- Date: 2026-10-07

## Context

Version 1 generates content with OpenAI. The official SDK (`openai` 2.x) offers the Chat Completions API and the newer Responses API.

## Decision

`OpenAIProvider` (`app/services/ai/openai_provider.py`) uses `client.responses.create` with these parameters:

| Parameter | Value |
| --------- | ----- |
| `model` | `OPENAI_MODEL` (default `gpt-4o-mini`) |
| `instructions` | The shared system prompt |
| `input` | The rendered user prompt |
| `max_output_tokens` | `OPENAI_MAX_OUTPUT_TOKENS` |
| `store` | `False`, so OpenAI does not keep responses containing customer data |

- `response.output_text` is the generated content. An empty output is treated as a provider error.
- Usage (`input_tokens`, `output_tokens`) and the exact model version are stored with each generation for cost tracking.
- No temperature is sent. Some recent models reject it, and the default is adequate.
- The client is created with `OPENAI_TIMEOUT_SECONDS` and the SDK's default retries.

## Consequences

- Positive: it is the API OpenAI recommends for new projects, with a simple `instructions` + `input` shape.
- Positive: `store=False` reduces data retention of customer information.
- Negative: the integration has been verified with SDK mocks only. A manual test with a real key is still pending.

## Alternatives considered

- **Chat Completions API**: still supported, but legacy for new development.
