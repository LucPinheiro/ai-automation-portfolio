# 0010. Configuration through environment variables

- Status: Accepted
- Date: 2026-10-07

## Context

Configuration differs per environment (local, test, future Docker/production) and includes secrets such as the OpenAI API key, which must never be committed.

## Decision

`app/config/settings.py` defines `Settings` with **pydantic-settings**. It reads environment variables and an optional `.env` file, which is git-ignored. `get_settings()` is cached.

| Variable | Default | Notes |
| -------- | ------- | ----- |
| `APP_NAME` | `AI Sales Assistant` | |
| `APP_VERSION` | `0.1.0` | |
| `ENVIRONMENT` | `development` | `development`, `testing` or `production` |
| `LOG_LEVEL` | `INFO` | |
| `DATABASE_URL` | `sqlite:///./ai_sales_assistant.db` | Also used by Alembic |
| `AI_PROVIDER` | `openai` | `openai` or `ollama`; unknown values fail at startup |
| `OPENAI_API_KEY` | none | `SecretStr`; blank means not configured |
| `OPENAI_MODEL` | `gpt-4o-mini` | |
| `OPENAI_TIMEOUT_SECONDS` | `30` | Must be > 0 |
| `OPENAI_MAX_OUTPUT_TOKENS` | `1200` | Must be > 0 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama server |
| `OLLAMA_MODEL` | `llama3.2:3b` | Must be installed with `ollama pull` |
| `OLLAMA_TIMEOUT_SECONDS` | `120` | Must be > 0; local models are slower |
| `OLLAMA_MAX_OUTPUT_TOKENS` | `1200` | Must be > 0; sent as `num_predict` |

**API key protection:**

- It is never hardcoded. `.env.example` ships an empty value.
- `SecretStr` hides it from `repr`, `str` and serialisation.
- Only the provider factory reads the raw value.
- Provider error messages, which may contain key fragments, are never logged or returned.

**Optional key.** The application starts without a key. With `AI_PROVIDER=openai`, only `POST /api/v1/generate` returns 503 until one is set. `AI_PROVIDER=ollama` needs no key.

## Consequences

- Positive: the same code runs in every environment, and Docker (Version 2) can inject variables directly.
- Positive: invalid configuration fails fast at startup.
- Negative: settings are cached, so changes require a restart.
