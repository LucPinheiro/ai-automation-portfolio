# 0005. SQLAlchemy 2.0 ORM (synchronous)

- Status: Accepted
- Date: 2026-10-07

## Context

The application needs an ORM that works with SQLite now and PostgreSQL later, integrates with a migration tool, and keeps models typed.

## Decision

- Use **SQLAlchemy 2.0** with typed declarative models (`Mapped[...]`, `mapped_column`).
- Use the **synchronous** engine and session, and synchronous FastAPI endpoints.
- `app/database/base.py` defines `Base` with a **constraint naming convention**, so Alembic generates deterministic names on every database.
- `app/database/session.py` builds the engine from `DATABASE_URL`. `check_same_thread=False` is applied only for SQLite, and `pool_pre_ping` is enabled.
- `get_db()` yields one session per request and always closes it.
- `expire_on_commit=False`, so objects stay readable after the service commits.

## Consequences

- Positive: simple, predictable code. The OpenAI SDK client used is synchronous too, so there is no mixing of sync and async code.
- Positive: SQLite, Alembic and pytest work without async drivers or event loop handling.
- Negative: each in-flight request occupies a thread-pool worker while waiting for OpenAI. This is acceptable for Version 1 traffic. Async (`AsyncSession`, `AsyncOpenAI`) can be adopted later if concurrency requires it, without changing routers' contracts.

## Alternatives considered

- **Async SQLAlchemy**: more complex for little benefit at this scale.
- **SQLModel**: couples ORM models to API schemas, which this architecture keeps separate.
