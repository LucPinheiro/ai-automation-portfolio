# 🤖 AI Sales Assistant - Intelligent Commercial Assistant

## 📝 Description



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

Using input filters:
* Customer, Company, and Industry details
* Product or Service features
* Customer Needs & Pain points
* Target Language & Tone of Voice

---

# 🏗 Architecture

```text
Frontend
     │
     ▼
FastAPI Routers
     │
     ▼
Service Layer
     │
     ▼
Repository Layer
     │
     ▼
SQLAlchemy ORM
     │
     ▼
SQLite / PostgreSQL
```

---

# 📂 Project Structure

```text
ai-sales-assistant/
├── app/
│   ├── api/
│   ├── routers/
│   ├── services/
│   ├── repositories/
│   ├── prompts/
│   ├── models/
│   ├── schemas/
│   ├── database/
│   ├── config/
│   ├── core/
│   ├── templates/
│   ├── static/
│   ├── utils/
│   └── main.py
├── docs/
│   ├── specs/
│   ├── adr/
│   ├── diagrams/
│   └── images/
├── tests/
├── docker/
├── README.md
├── LICENSE
└── .gitignore
```

---

# ⚙ Technology Stack

* **Backend:** Python 3.12+, FastAPI, SQLAlchemy, Pydantic, Alembic
* **Frontend:** HTML5, Bootstrap 5, JavaScript, Jinja2 Templates
* **Database:** SQLite (Development) / PostgreSQL (Production)
* **AI & Core:** OpenAI API, Advanced Prompt Engineering, Vector Embeddings
* **Infrastructure:** Docker, Docker Compose, Git, GitHub Actions

---

# 📑 Documentation & Specs

This project strictly adheres to **Spec-Driven Development (SDD)**.

* **Specifications:** Product Vision, Functional & Non-Functional Requirements, Use Cases, Domain Model, Database Strategy, API Contracts, and System Architecture Design.
* **Architecture Decision Records (ADR):** Documented patterns for Clean Architecture adoption, Repository & Service patterns separation, Configuration Strategy, and Future Knowledge-base Retrieval (RAG).

---

# 🚀 Roadmap

### 📦 Portfolio Overview

| Project | Description | Status |
| :--- | :--- | :--- |
| [🤖 AI Sales Assistant](./ai_sales_assistant/) | Intelligent commercial assistant | ✅ Done |
| 📄 AI Document Assistant | OCR + Intelligent Document Processing | 📅 Planned |
| 📚 Enterprise RAG Chatbot | Enterprise knowledge assistant | 📅 Planned |
| 📊 AI Forecast Dashboard | AI-powered analytics dashboard | 📅 Planned |
| 🗺 Smart Route Planner | Intelligent route optimization | 📅 Planned |

### 🛠 Product Versioning
* **Version 1 (Core):** AI Content Generation engine, REST API layout, SQLite infrastructure, Bootstrap web UI, Swagger baseline.
* **Version 2 (Security):** PostgreSQL migration, Dockerization, JWT Authentication workflow, User management roles.
* **Version 3 (Enterprise Features):** Customer lifecycle logs, PDF/Word document generation, Sales performance analytics.
* **Version 4 (Intelligence):** RAG systems, local LLM architectures via Ollama, Custom embedding spaces.
* **Version 5 (Integrations):** Native Odoo CRM integration, Model Context Protocol (MCP) toolkits, Multi-agent collaboration frameworks.

---

# 📊 Project Status

| Phase | Status |
| :--- | :--- |
| Analysis | ✅ Done |
| Specifications | ✅ Done |
| Architecture | ✅ Done |
| Backend | 🚧 In Progress |
| Frontend | ⏳ Pending |
| Testing | ⏳ Pending |
| Deployment | ⏳ Pending |

---

# 🎓 Focus & Learning Goals

* Real-world AI Software Engineering workflows.
* Advanced FastAPI framework design and REST API design.
* Scalable relational models using SQLAlchemy ORM.
* Implementations of Prompt Engineering, Retrieval-Augmented Generation (RAG), and Model Context Protocol (MCP).
* Production-grade infrastructure pipelines via Docker and PostgreSQL.

***

**Luciana Pinheiro**  
*AI Software Engineer • Full Stack Developer • Odoo Consultant*

Encuéntrame en:
* [GitHub](https://github.com)
* [Portfolio](https://lucpinheiro.github.io/)
* [LinkedIn](https://linkedin.com)

***

# 📄 License

This project is licensed under the **MIT License**.

<p align="center">
  ⭐ Part of the <b><a href="https://github.com/ai-automation-portfolio">AI Automation Portfolio</a></b>.
</p>
