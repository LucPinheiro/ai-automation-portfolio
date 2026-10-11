# 10. Roadmap

Status: ✅ done · 🚧 in progress · ⏳ planned

## Version 1: AI content generation 🚧

| Item | Status |
| ---- | ------ |
| AI content generation (5 content types, 4 languages, 5 tones) | ✅ |
| REST API (`/api/v1`) with uniform error handling | ✅ |
| SQLite persistence with Alembic migrations | ✅ |
| Swagger / OpenAPI documentation | ✅ |
| Automated test suite (no external calls) | ✅ |
| Specifications and ADRs | ✅ |
| Manual verification with a real OpenAI key | ⏳ |
| Bootstrap UI (Jinja2) at `/app` | ✅ |
| Ollama as a second, local AI provider (`AI_PROVIDER=ollama`) | ✅ |

## Version 2 ⏳

- PostgreSQL
- Docker and Docker Compose
- Authentication
- User Management

## Version 3 ⏳

- Customer Management
- PDF Export
- Word Export
- Dashboard

## Version 4 ⏳

- RAG
- Ollama ✅ (delivered early as a local AI provider)
- Hugging Face
- Embeddings

## Version 5 ⏳

- Odoo CRM Integration
- MCP
- AI Agents
- Enterprise Platform

## Architectural preparation already in place

Nothing below is implemented; the architecture only leaves a place for it.

| Future feature | Preparation |
| -------------- | ----------- |
| PostgreSQL | Portable column types, naming convention, `DATABASE_URL`, Alembic |
| Docker | Environment-based configuration, reserved `docker/` folder |
| Hugging Face | `AIProvider` protocol and provider factory (already used by Ollama) |
| RAG | Prompt building isolated in `app/prompts`, called from the service |
| Customer Management | Customer data stored as a snapshot; a `customer_id` can be added later |
