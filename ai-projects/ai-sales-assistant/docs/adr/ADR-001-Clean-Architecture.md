# ADR-001 — Adoption of Clean Architecture

**Status:** Accepted

**Date:** 2026-06-26

**Project:** AI Sales Assistant – Intelligent Commercial Assistant

**Authors:** Luciana Pinheiro

---

# 1. Context

The AI Sales Assistant project aims to become a professional software engineering portfolio demonstrating modern backend development, Artificial Intelligence integration and scalable software architecture.

The application is expected to evolve through multiple versions, gradually incorporating authentication, PostgreSQL, Redis, Retrieval-Augmented Generation (RAG), AI Agents, external CRM integrations and enterprise features.

Without a clear architectural approach, future development could introduce tight coupling, duplicated logic and maintenance difficulties.

---

# 2. Problem

A traditional implementation often places business logic inside HTTP controllers (routers), mixes persistence with application logic and couples the application to specific technologies.

This approach creates several problems:

* Low maintainability.
* High coupling between components.
* Difficult unit testing.
* Poor scalability.
* Technology-dependent business logic.
* Difficult migration to new infrastructures.

As the project grows, these issues become increasingly expensive to solve.

---

# 3. Decision

The project will adopt **Clean Architecture** as its primary architectural style.

The system will be divided into independent layers with clearly defined responsibilities.

The main layers are:

* Presentation Layer
* API Layer
* Service Layer
* Repository Layer
* Persistence Layer

Business rules will remain independent from frameworks, databases and external services.

---

# 4. Architectural Principles

The architecture follows these principles:

* Separation of Concerns
* Single Responsibility Principle
* Dependency Inversion Principle
* High Cohesion
* Low Coupling
* Explicit Dependencies
* Testability
* Scalability

---

# 5. Layer Responsibilities

## Presentation Layer

Responsible for:

* User interface
* HTTP requests
* Rendering templates
* Displaying results

No business logic is allowed.

---

## API Layer

Responsible for:

* HTTP endpoints
* Request validation
* Response generation
* Delegating work to Services

No persistence or AI logic is allowed.

---

## Service Layer

Responsible for:

* Business rules
* Workflow orchestration
* Prompt generation coordination
* Exception handling
* Communication between repositories and AI providers

This is the core of the application.

---

## Repository Layer

Responsible for:

* Database access
* CRUD operations
* SQLAlchemy interaction

Repositories never contain business rules.

---

## Persistence Layer

Responsible for:

* SQLite
* PostgreSQL (future)
* Alembic migrations

---

# 6. Architecture Overview

```mermaid
flowchart TD

Presentation

↓

API

↓

Services

↓

Repositories

↓

Database
```

Each layer communicates only with the next lower layer.

Dependencies always point inward.

---

# 7. Benefits

The selected architecture provides:

* Clear separation of responsibilities.
* Easier maintenance.
* Improved readability.
* Independent testing of business logic.
* Easier replacement of technologies.
* Better scalability.
* Lower technical debt.

---

# 8. Consequences

Positive consequences:

* Modular codebase.
* Easier onboarding for new developers.
* Independent evolution of each layer.
* Easier testing with pytest.
* Better long-term maintainability.

Negative consequences:

* Slightly more files.
* More initial setup.
* Higher learning curve for beginners.

These disadvantages are acceptable considering the long-term benefits.

---

# 9. Alternatives Considered

## Alternative 1 — All logic inside FastAPI routers

Advantages:

* Faster initial development.
* Fewer files.

Disadvantages:

* Poor maintainability.
* Tight coupling.
* Difficult testing.

Rejected.

---

## Alternative 2 — MVC Architecture

Advantages:

* Well-known pattern.
* Simpler structure.

Disadvantages:

* Business logic often leaks into controllers.
* Less flexible for AI integrations.

Rejected.

---

## Alternative 3 — Clean Architecture (Selected)

Advantages:

* Modular.
* Testable.
* Scalable.
* Independent from frameworks.
* Suitable for enterprise software.

Accepted.

---

# 10. Future Impact

Choosing Clean Architecture prepares the project for future integrations such as:

* PostgreSQL
* Redis
* Docker
* Kubernetes
* JWT Authentication
* RAG Pipelines
* AI Agents
* MCP
* Odoo CRM
* External APIs

without requiring significant changes to the core business logic.

---

# 11. Related Specifications

This decision is directly related to:

* SPEC-08 — Software Architecture
* SPEC-09 — Folder Structure
* SPEC-10 — Project Roadmap

---

# 12. References

* Robert C. Martin — *Clean Architecture*
* Martin Fowler — *Patterns of Enterprise Application Architecture*
* FastAPI Documentation
* SOLID Principles
* Domain-Driven Design (DDD)
