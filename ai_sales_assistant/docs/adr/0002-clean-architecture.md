# 0002. Clean Architecture with layered modules

- Status: Accepted
- Date: 2026-10-07

## Context

The project starts as a content generator (Version 1) and is planned to grow into authentication, customer management, exports, RAG, CRM integration and agents. Business logic must stay independent of the web framework, the database and the AI vendor so it survives those changes.

## Decision

Organise the code in layers. Each layer depends only on the layers below it:

```
Routers (app/routers)          HTTP only: receive, validate, call a service, respond
   ↓
Services (app/services)        Use cases and transactions
   ↓                    ↘
Repositories               AI providers (app/services/ai) + prompts (app/prompts)
(app/repositories)
   ↓
ORM models (app/models) → database (app/database) → SQLite / PostgreSQL
```

Cross-cutting modules:

- `app/core`: enums, constants, exceptions, error handlers, logging
- `app/config`: settings
- `app/schemas`: API DTOs
- `app/api`: version router, dependency wiring, OpenAPI error docs

Rules:

- Routers contain no business logic; each endpoint body is a single service call.
- Services return Pydantic schemas, never ORM objects, so routers never touch SQLAlchemy.
- Domain enums live in `app/core/enums.py` because models, schemas and prompts all use them. Putting them in `schemas/` would make the ORM depend on the API layer.
- `app/main.py` only assembles the application.

## Consequences

- Positive: each layer can be tested in isolation (repository with in-memory SQLite, service with a fake provider, API with dependency overrides).
- Positive: replacing SQLite with PostgreSQL, or OpenAI with another provider, does not touch the services or routers.
- Negative: more files and indirection than a single-module app. This is acceptable given the roadmap.

## Alternatives considered

- **Strict hexagonal architecture**: repository interfaces as ports, separate domain entities and mappers. Rejected for Version 1 as over-engineering; the ORM model doubles as the domain entity.
