# 🤖 AI Sales Assistant – Intelligent Commercial Assistant


<p align="center">

<a href="./README.md">
    <img src="https://img.shields.io/badge/🇬🇧-English-blue?style=for-the-badge" alt="English">
</a>

<a href="./README.es.md">
    <img src="https://img.shields.io/badge/🇪🇸-Español-red?style=for-the-badge" alt="Español">
</a>

<a href="./README.pt.md">
    <img src="https://img.shields.io/badge/🇵🇹-Português-green?style=for-the-badge" alt="Português">
</a>

<a href="./README.fr.md">
    <img src="https://img.shields.io/badge/🇫🇷-Français-purple?style=for-the-badge" alt="Français">
</a>

</p>

<p align="center">

![](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge\&logo=python\&logoColor=white)
![](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge\&logo=fastapi\&logoColor=white)
![](https://img.shields.io/badge/SQLAlchemy-ORM-red?style=for-the-badge)
![](https://img.shields.io/badge/Pydantic-v2-E92063?style=for-the-badge)
![](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge\&logo=postgresql\&logoColor=white)
![](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge\&logo=docker\&logoColor=white)
![](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge)
![](https://img.shields.io/badge/Ollama-000000?style=for-the-badge)
![](https://img.shields.io/badge/RAG-Future-orange?style=for-the-badge)
![](https://img.shields.io/badge/MCP-Future-success?style=for-the-badge)
![](https://img.shields.io/badge/SDD-Spec--Driven_Development-darkgreen?style=for-the-badge)

</p>

---

# 📖 Description

**AI Sales Assistant** is an AI-powered web application built with **FastAPI** that helps sales teams generate professional business communications quickly and consistently.

The project follows modern software engineering practices including:

* Spec-Driven Development (SDD)
* Clean Architecture
* Repository Pattern
* Service Layer
* REST APIs
* AI-first development

The objective is to build a production-ready AI application capable of evolving into a complete enterprise commercial assistant.

---

# ✨ Features

Generate automatically:

* 📧 Commercial emails
* 📄 Sales proposals
* 🔄 Follow-up emails
* 💬 WhatsApp messages
* 📝 Customer summaries

With user accounts:

* 🔐 Registration, login and logout (HttpOnly session cookie)
* 👤 My account and password change
* ✉️ Password recovery with single-use, expiring links
* 🛡️ Each user only sees and manages their own generations
* 📌 Commercial terms you provide (price, discount, scales, dates...) are mandatory: the app verifies the generated text, retries once and warns about anything still missing
* 👤 Guest mode ("Entrar sin iniciar sesión", or the demo credentials `demo` / `demo123` pre-filled on the login page): try it without an account; guest data is deleted on logout

Using:

* Customer
* Company
* Industry
* Product or Service
* Customer Needs
* Language
* Tone of Voice

---

# 🏗 Architecture

```
Frontend (planned) / API clients
     │
     ▼
FastAPI Routers
     │
     ▼
Service Layer ──────────► AI Provider (OpenAI | Ollama) + Prompts
     │
     ▼
Repository Layer
     │
     ▼
SQLAlchemy ORM
     │
     ▼
SQLite (Version 1) / PostgreSQL (Version 2)
```

* Routers only receive, validate, call a service and respond.
* `GenerationService` builds the prompt, calls the AI provider and persists the result. Nothing is stored if the provider fails.
* OpenAI and Ollama sit behind an `AIProvider` abstraction. `AI_PROVIDER` selects one at startup, and new providers can be added without touching business logic.

See [Architecture](docs/specs/08-architecture.md) and the [ADRs](docs/adr/README.md).

---

# 📂 Project Structure

```text
ai-sales-assistant/

├── app/
│   ├── api/            # /api/v1 router, dependency injection, OpenAPI error docs
│   ├── routers/        # endpoints (system, generations)
│   ├── services/       # GenerationService, health check, ai/ (AIProvider, OpenAI, Ollama, factory)
│   ├── repositories/   # GenerationRepository
│   ├── prompts/        # system prompt + one template per content type
│   ├── models/         # SQLAlchemy models
│   ├── schemas/        # Pydantic schemas
│   ├── database/       # Base, engine/session, UTCDateTime
│   ├── config/         # settings from environment variables
│   ├── core/           # enums, constants, exceptions, error handlers, logging
│   ├── templates/      # reserved for the Bootstrap UI
│   ├── static/         # reserved for the Bootstrap UI
│   ├── utils/
│   └── main.py
│
├── alembic/            # database migrations
├── docs/
│   ├── specs/
│   ├── adr/
│   ├── diagrams/
│   └── images/
│
├── tests/
├── docker/             # reserved for Version 2
├── .env.example
├── alembic.ini
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── LICENSE
└── .gitignore
```

---

# ⚙ Technology Stack

## Backend

* Python 3.12+
* FastAPI
* SQLAlchemy 2.0
* Pydantic v2 + pydantic-settings
* Alembic

## Frontend

* HTML5
* Bootstrap 5 (served locally from `app/static/vendor`, works offline)
* Vanilla JavaScript (ES modules)
* Jinja2

## Database

* SQLite (Version 1)
* PostgreSQL (Version 2)

## Artificial Intelligence

* OpenAI API (Responses API)
* Ollama (local models, e.g. `llama3.2:3b`)
* Prompt Engineering
* Future RAG integration
* Future MCP integration

## Infrastructure

* Git
* GitHub
* Docker and Docker Compose (Version 2)

---

# ▶ How to Run

Requirements: **Python 3.12+** and one AI provider to generate content: an **OpenAI API key** or a local **[Ollama](https://ollama.com)** installation.

### 1. Create and activate a virtual environment

```bash
# Windows (PowerShell)
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
python3.12 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements-dev.txt     # runtime + test dependencies
# or, runtime only:
pip install -r requirements.txt
```

### 3. Configure `.env`

```bash
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env
```

### 4. Choose the AI provider

`AI_PROVIDER` in `.env` selects the provider. Prompts, endpoints and error handling are the same for both.

**Option A: OpenAI**

```dotenv
AI_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini
```

* `.env` is git-ignored: **never commit it**, and never put a real key in `.env.example`.
* Without a key the API still starts. `POST /api/v1/generate` returns `503 ai_provider_not_configured`, and the other endpoints keep working.

**Option B: Ollama (local, no API key)**

```bash
ollama pull llama3.2:3b
```

```dotenv
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

* Ollama must be running (`ollama serve`, or the desktop app) before calling `POST /api/v1/generate`.
* If Ollama is unreachable, times out or the model is not installed, the endpoint returns `502 ai_provider_error`.
* Local models are slower than hosted APIs; increase `OLLAMA_TIMEOUT_SECONDS` if generations time out.

### 5. Run the database migrations

```bash
alembic upgrade head
```

This creates `ai_sales_assistant.db`, or the database set in `DATABASE_URL`.

**Upgrading a database created before user accounts:** generations that already exist are kept, without an owner, and are invisible to every user. Register your account in the web UI, then assign them:

```bash
python -m app.cli assign-orphan-generations --email you@example.com --dry-run   # how many
python -m app.cli assign-orphan-generations --email you@example.com             # assign
```

### 6. Start FastAPI

```bash
uvicorn app.main:app --reload
```

### 7. Open the web UI and Swagger

* Web UI: http://127.0.0.1:8000/app (redirects to `/login`; press **Entrar** with the pre-filled demo values, use **Probar sin registrarse**, or create an account at `/register`)
* Public pages: `/contacto` (support details and contact form, both in **demo mode**: the form validates but sends nothing), `/legal`, `/privacidad`
* Swagger UI: http://127.0.0.1:8000/docs
* ReDoc: http://127.0.0.1:8000/redoc
* Health check: http://127.0.0.1:8000/health

### 8. Run the tests

```bash
pytest
```

The tests use an in-memory SQLite database and a fake AI provider, so they **never call OpenAI or Ollama** and need no API key or local model.

### Configuration reference

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `DATABASE_URL` | `sqlite:///./ai_sales_assistant.db` | Database connection URL |
| `AI_PROVIDER` | `openai` | AI provider: `openai` or `ollama` |
| `OPENAI_API_KEY` | (empty) | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model used for generation |
| `OPENAI_TIMEOUT_SECONDS` | `30` | OpenAI request timeout |
| `OPENAI_MAX_OUTPUT_TOKENS` | `1200` | OpenAI maximum output length |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2:3b` | Ollama model used for generation |
| `OLLAMA_TIMEOUT_SECONDS` | `120` | Ollama request timeout |
| `OLLAMA_MAX_OUTPUT_TOKENS` | `1200` | Ollama maximum output length (`num_predict`) |
| `LOG_LEVEL` | `INFO` | Logging level |

---

# 🔌 API

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/` | API information |
| GET | `/health` | Application and database status |
| POST | `/api/v1/generate` | Generate commercial content with AI and store it |
| GET | `/api/v1/generations` | List generations (`limit`, `offset`, `content_type`) |
| POST | `/api/v1/auth/register` | Create an account and log in |
| POST | `/api/v1/auth/login` | Log in with username or email (sets the HttpOnly session cookie) |
| POST | `/api/v1/auth/logout` | Log out (closes the session on the server) |
| GET | `/api/v1/auth/me` | Current user |
| POST | `/api/v1/auth/change-password` | Change the password |
| POST | `/api/v1/auth/guest` | Start a temporary guest session (limited, deleted on logout) |
| POST | `/api/v1/auth/forgot-password` | Request a password reset link (same answer for any email) |
| POST | `/api/v1/auth/reset-password` | Set a new password with the reset token |
| GET | `/api/v1/generations/{id}` | Get a generation |
| PUT | `/api/v1/generations/{id}` | Regenerate a generation with AI from new input (same record) |
| DELETE | `/api/v1/generations/{id}` | Delete a generation |
| GET | `/api/v1/pricing/discount` | Discount breakdown calculated by the backend (Decimal) |

Example request:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "content_type": "commercial_email",
    "customer": "María López",
    "company": "Logística Norte S.L.",
    "industry": "Logistics",
    "product_or_service": "Fleet management software",
    "customer_needs": "Reduce fuel costs and track deliveries in real time.",
    "language": "es",
    "tone": "professional"
  }'
```

* Content types: `commercial_email`, `sales_proposal`, `follow_up`, `whatsapp`, `customer_summary`
* Languages: `es`, `en`, `pt`, `fr`
* Tones: `professional`, `formal`, `friendly`, `persuasive`, `concise`

All generation endpoints require a session and only see the current user's generations (another user's id returns 404). In Swagger, call `POST /api/v1/auth/login` first: the browser keeps the cookie.

All errors share one format: `{"error": {"code", "message", "details"}}`. See [API Design](docs/specs/07-api-design.md).

---

# 📑 Documentation

This project follows **Spec-Driven Development (SDD)**.

## Specifications ([docs/specs](docs/specs/README.md))

* [Product Vision](docs/specs/01-product-vision.md)
* [Functional Requirements](docs/specs/02-functional-requirements.md)
* [Non-Functional Requirements](docs/specs/03-non-functional-requirements.md)
* [Use Cases](docs/specs/04-use-cases.md)
* [Domain Model](docs/specs/05-domain-model.md)
* [Database Design](docs/specs/06-database-design.md)
* [API Design](docs/specs/07-api-design.md)
* [Architecture](docs/specs/08-architecture.md)
* [Folder Structure](docs/specs/09-folder-structure.md)
* [Roadmap](docs/specs/10-roadmap.md)

## Architecture Decision Records ([docs/adr](docs/adr/README.md))

* [FastAPI](docs/adr/0001-fastapi.md)
* [Clean Architecture](docs/adr/0002-clean-architecture.md)
* [Repository Pattern](docs/adr/0003-repository-pattern.md)
* [Service Layer](docs/adr/0004-service-layer.md)
* [SQLAlchemy](docs/adr/0005-sqlalchemy.md)
* [Database Strategy](docs/adr/0006-database-strategy.md)
* [OpenAI Responses API](docs/adr/0007-openai-responses-api.md)
* [AIProvider abstraction](docs/adr/0008-ai-provider-abstraction.md)
* [Prompt Engineering](docs/adr/0009-prompt-engineering.md)
* [Configuration Management](docs/adr/0010-configuration-management.md)
* [Error Handling](docs/adr/0011-error-handling.md)
* [Ollama as a local AI provider](docs/adr/0012-ollama-provider.md)

---

# 🚀 Roadmap

## Version 1

* AI Content Generation ✅
* REST API ✅
* SQLite ✅
* Swagger ✅
* Bootstrap UI ✅

## Version 2

* PostgreSQL
* Docker
* Authentication
* User Management

## Version 3

* Customer Management
* PDF Export
* Word Export
* Dashboard

## Version 4

* RAG
* Ollama ✅ (local AI provider)
* Hugging Face
* Embeddings

## Version 5

* Odoo CRM Integration
* MCP
* AI Agents
* Enterprise Platform

---

# 📊 Project Status

| Phase          | Status |
| -------------- | ------ |
| Analysis       | ✅      |
| Specifications | ✅      |
| Architecture   | ✅      |
| Backend (V1)   | ✅      |
| Frontend (V1)  | ✅      |
| Testing        | ✅      |
| Deployment     | ⏳      |

---

# 🎓 Learning Goals

This project is focused on learning and demonstrating practical experience in:

* AI Software Engineering
* FastAPI
* SQLAlchemy
* Clean Architecture
* Prompt Engineering
* REST APIs
* Docker
* PostgreSQL
* RAG
* MCP
* AI Agents
* DevOps

---

# 👩‍💻 Author

**Luciana Pinheiro**

AI Software Engineer • Full Stack Developer • Odoo Consultant

GitHub:

https://github.com/LucPinheiro

Portfolio:

https://lucpinheiro.github.io/

LinkedIn:

https://linkedin.com/in/lucianapinheiro

---

# 📄 License

This project is licensed under the **MIT License**.

---

<p align="center">

⭐ Part of the **AI Automation Portfolio**.

</p>
