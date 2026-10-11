# 0011. Error handling strategy

- Status: Accepted
- Date: 2026-10-07

## Context

Clients need predictable, machine-readable errors. Internals (stack traces, SQL, provider messages, API keys, submitted data) must never leak.

## Decision

**One error format for every error response:**

```json
{"error": {"code": "validation_error", "message": "The request contains invalid data.",
           "details": [{"field": "customer", "message": "String should have at least 1 character", "type": "string_too_short"}]}}
```

**Exception hierarchy** (`app/core/exceptions.py`). The `message` of every `AppError` is safe to return to the client:

| Exception | HTTP | `code` |
| --------- | ---- | ------ |
| `BadRequestError` | 400 | `bad_request` |
| `NotFoundError` | 404 | `not_found` |
| `AIProviderError` | 502 | `ai_provider_error` |
| `AIProviderNotConfiguredError` (subclass of `AIProviderError`) | 503 | `ai_provider_not_configured` |

**Global handlers** (`app/core/error_handlers.py`):

| Handler | Behaviour |
| ------- | --------- |
| `AppError` | Returns its status, code and message. 4xx are logged at INFO, 5xx at ERROR. |
| `RequestValidationError` | 422 `validation_error` with `field`, `message` and `type` for each error. The submitted `input` is never echoed. Malformed JSON returns **400** `invalid_json`. |
| Starlette `HTTPException` | Same format; the code comes from the HTTP status phrase, e.g. `not_found`, `method_not_allowed`. |
| Unhandled `Exception` | 500 `internal_error` with a generic message. The traceback is logged server-side only. |

**Additional rules:**

- `OpenAIProvider` logs only the error class, HTTP status and OpenAI request id, never the provider's message. `OllamaProvider` logs only the error class and HTTP status. Prompts and generated content are never logged.
- `/health` is the exception to the common format: it returns `HealthResponse` with 503 when the database is down.
- `app/api/responses.py` documents each error in OpenAPI with the `ErrorResponse` schema and an example.

## Consequences

- Positive: clients branch on `error.code`, and no sensitive data leaks. This is verified by tests that place fake secrets inside errors.
- Negative: FastAPI's default 422 body (`detail` array) is replaced, which clients familiar with FastAPI must note.
