# 0003. Repository Pattern for persistence

- Status: Accepted
- Date: 2026-10-07

## Context

Services need to store and query generations without building SQL queries themselves, and persistence must be testable on its own.

## Decision

Encapsulate data access in repositories. Version 1 has `GenerationRepository` with these methods:

| Method | Purpose |
| ------ | ------- |
| `add(generation)` | Adds and **flushes** (assigns the id); never commits |
| `get_by_id(id)` | Returns the generation or `None` |
| `list_paginated(limit, offset, content_type=None)` | Newest first (`created_at DESC, id DESC`) |
| `count(content_type=None)` | Total for pagination |

- Repositories receive a SQLAlchemy `Session` and **never commit**: the transaction belongs to the service, which knows where a unit of work ends.
- The repository is a concrete class with no abstract interface. Only one implementation exists.

## Consequences

- Positive: queries live in one place, and the service reads as business steps.
- Positive: repository tests run against in-memory SQLite (`tests/test_generation_repository.py`).
- Negative: no interface means a second storage technology would require extracting one. This is unlikely, since SQLAlchemy already abstracts the database engine.

## Alternatives considered

- **Queries inside services**: simpler, but mixes persistence with business logic.
- **Repository committing on `add`**: prevents grouping several writes in one transaction.
