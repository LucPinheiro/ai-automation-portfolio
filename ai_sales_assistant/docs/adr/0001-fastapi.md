# 0001. FastAPI as web framework

- Status: Accepted
- Date: 2026-10-07

## Context

The application exposes a REST API that a future Bootstrap/Jinja2 frontend and other clients will consume. The API must validate input strictly, document itself and be easy to test.

## Decision

Use **FastAPI** with **Pydantic v2**.

- Request and response bodies are Pydantic models, so validation and serialisation come from the same definitions.
- OpenAPI is generated automatically and served by Swagger UI at `/docs`. Every endpoint declares `summary`, `description`, `response_model`, a success description and its documented errors with examples (enforced by `tests/test_openapi.py`).
- Dependencies (database session, AI provider, services) are wired with `Depends`, which tests replace through `app.dependency_overrides`.
- Endpoints are synchronous (`def`); FastAPI runs them in its thread pool (see [ADR 0005](0005-sqlalchemy.md)).
- Endpoints are versioned under `/api/v1`. `/` and `/health` stay unversioned.

## Consequences

- Positive: little boilerplate, accurate API documentation, first-class testing with `TestClient`.
- Positive: Jinja2 support is built in for the planned frontend.
- Negative: validation errors use FastAPI's default 422 format unless overridden, so a custom handler is required (see [ADR 0011](0011-error-handling.md)).

## Alternatives considered

- **Flask**: mature, but validation and OpenAPI need extra libraries.
- **Django + DRF**: too heavy for an API-first application of this size.
