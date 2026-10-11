# 03. Non-Functional Requirements

| ID | Category | Requirement | How Version 1 meets it |
| -- | -------- | ----------- | ---------------------- |
| NFR-01 | Maintainability | Layered architecture, with no business logic in routers or `main.py` | Routers → services → repositories / AI providers ([ADR 0002](../adr/0002-clean-architecture.md)) |
| NFR-02 | Extensibility | New AI providers without changing business logic | `AIProvider` protocol and factory ([ADR 0008](../adr/0008-ai-provider-abstraction.md)) |
| NFR-03 | Portability | Switch SQLite → PostgreSQL by configuration | `DATABASE_URL`, portable column types, Alembic ([ADR 0006](../adr/0006-database-strategy.md)) |
| NFR-04 | Security | No hardcoded secrets | Keys only from environment / git-ignored `.env`; `SecretStr` |
| NFR-05 | Security | No sensitive data in responses | Generic messages for 5xx and provider errors; validation errors never echo input; prompts and token usage are not exposed |
| NFR-06 | Security / privacy | No customer data in logs or at the AI vendor beyond the request | Prompts and outputs are never logged; OpenAI `store=False`; Ollama keeps all data local |
| NFR-07 | Security | Mitigate prompt injection | Delimited customer data, system rule, delimiter tags stripped |
| NFR-08 | Reliability | No partial writes | The provider is called before persisting; rollback on database errors |
| NFR-09 | Reliability | Bounded waiting on the AI provider | Configurable timeouts (`OPENAI_TIMEOUT_SECONDS`, `OLLAMA_TIMEOUT_SECONDS`), OpenAI SDK retries |
| NFR-10 | Observability | Diagnosable failures | Structured log lines with error class, HTTP status, OpenAI request id, tokens and duration (OpenAI and Ollama) |
| NFR-11 | Usability (API) | Self-documented API | OpenAPI with summaries, descriptions, examples and documented errors, enforced by tests |
| NFR-12 | Consistency | Uniform error format | `{"error": {"code", "message", "details"}}` ([ADR 0011](../adr/0011-error-handling.md)) |
| NFR-13 | Testability | Automated tests without external services | pytest suite with in-memory SQLite and `FakeAIProvider`; no real OpenAI or Ollama calls |
| NFR-14 | Data integrity | Timezone-correct timestamps | `UTCDateTime` stores and returns aware UTC datetimes |
| NFR-15 | Code quality | Type hints, small functions, clear names | Applied across the codebase |

## Known limits of Version 1

- No authentication: the API must not be exposed publicly as is.
- SQLite supports a single writer and is intended for local use.
- Synchronous request handling: each generation occupies a worker thread while the provider responds.
- No rate limiting or cost limits per user.
