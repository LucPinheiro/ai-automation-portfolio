# 0004. Service Layer for use cases

- Status: Accepted
- Date: 2026-10-07

## Context

Generating content involves several steps: build the prompt, call the AI provider, persist the result and handle failures. These steps must not live in routers.

## Decision

Implement use cases in `GenerationService` (`app/services/generation_service.py`):

| Method | Use case |
| ------ | -------- |
| `generate(data)` | Builds the prompt, calls the provider, persists the result and commits |
| `get(id)` | Returns a generation or raises `NotFoundError` |
| `list_generations(limit, offset, content_type)` | Returns a paginated list |

- **The AI provider is called before anything is written.** If it fails, no row is created. On a database error the service rolls back.
- **The provider is injected as a resolver** (`Callable[[], AIProvider]`) and resolved only inside `generate()`. Read endpoints therefore keep working when the provider is not configured.
- The service owns the transaction: `repository.add()` flushes, then the service calls `session.commit()`.
- `app/services/health_service.py` holds the health check logic for the same reason.

## Consequences

- Positive: routers are trivial, and use cases are tested without HTTP (`tests/test_generation_service.py`).
- Positive: no partial or incomplete generations are ever stored.
- Negative: the service depends on SQLAlchemy's `Session` for transaction control. A unit-of-work abstraction can be introduced if needed.
