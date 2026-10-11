# Architecture Decision Records

Each ADR records one significant architectural decision: its context, the decision itself and its consequences.

| ADR | Title | Status |
| --- | ----- | ------ |
| [0001](0001-fastapi.md) | FastAPI as web framework | Accepted |
| [0002](0002-clean-architecture.md) | Clean Architecture with layered modules | Accepted |
| [0003](0003-repository-pattern.md) | Repository Pattern for persistence | Accepted |
| [0004](0004-service-layer.md) | Service Layer for use cases | Accepted |
| [0005](0005-sqlalchemy.md) | SQLAlchemy 2.0 ORM (synchronous) | Accepted |
| [0006](0006-database-strategy.md) | SQLite for Version 1, PostgreSQL in Version 2, Alembic migrations | Accepted |
| [0007](0007-openai-responses-api.md) | OpenAI Responses API | Accepted |
| [0008](0008-ai-provider-abstraction.md) | AIProvider abstraction | Accepted |
| [0009](0009-prompt-engineering.md) | Prompt engineering strategy | Accepted |
| [0010](0010-configuration-management.md) | Configuration through environment variables | Accepted |
| [0011](0011-error-handling.md) | Error handling strategy | Accepted |
| [0012](0012-ollama-provider.md) | Ollama as a local AI provider | Accepted |
| [0013](0013-authentication.md) | User authentication with server-side sessions | Accepted |
| [0014](0014-guest-mode.md) | Guest mode and usernames | Accepted |
| [0015](0015-pricing-calculation.md) | Discount calculation in the backend | Accepted |
| [0016](0016-mandatory-commercial-terms.md) | Mandatory commercial terms: prompt, verification and retry | Accepted |
| [0017](0017-visual-identity-and-interface-languages.md) | Visual identity, access screens and interface languages | Accepted · languages part superseded by [SDD 12](../specs/12-sdd.md) |

## Template

```markdown
# NNNN. Title

- Status: Proposed | Accepted | Superseded by NNNN
- Date: YYYY-MM-DD

## Context
## Decision
## Consequences
## Alternatives considered
```
