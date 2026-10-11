# 0006. SQLite for Version 1, PostgreSQL in Version 2, Alembic migrations

- Status: Accepted
- Date: 2026-10-07

## Context

The roadmap starts with SQLite (Version 1) and moves to PostgreSQL (Version 2). The switch must not require changes to business logic.

## Decision

1. **The database URL is configuration.** It comes from `DATABASE_URL`. The default is `sqlite:///./ai_sales_assistant.db`.
2. **The schema is managed only with Alembic.** The application never calls `create_all`; only the test fixtures do, against in-memory SQLite.
   - `alembic/env.py` takes the URL from the settings, so `DATABASE_URL` is the single source of truth.
   - `render_as_batch` is enabled for SQLite, and type comparison is on.
   - Migration files are named `NNNN_slug.py` with sequential revision ids.
3. **Column types are portable:**
   - Enums are stored as `VARCHAR` holding their *values* (`native_enum=False`, no `CHECK` constraint). Adding a value needs no migration, and both databases behave the same. Validation is done by Pydantic and SQLAlchemy.
   - Dates use `UTCDateTime`, a `TypeDecorator` over `DateTime(timezone=True)`. It rejects naive datetimes and always returns aware UTC values, even on SQLite, which drops the offset.
   - Lengths are shared constants (`app/core/constants.py`) used by both the columns and the schemas.
4. **Migrations are tested.** `tests/test_migrations.py` runs `upgrade head`, verifies the schema matches the models with no differences, and runs `downgrade base`.

## Consequences

- Moving to PostgreSQL in Version 2 requires changing `DATABASE_URL`, adding a driver (e.g. `psycopg`) and running `alembic upgrade head`.
- SQLite is single-writer. This is fine for Version 1 (local, single user) but not for multi-user production, which is why PostgreSQL is planned.

## Alternatives considered

- **Native database enums**: stricter, but they need a migration for every new value and behave differently between databases.
- **`create_all` at startup**: rejected because it cannot evolve an existing schema.
