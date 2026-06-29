
# 🤖 AI Sales Assistant – Intelligent Commercial Assistant

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-red)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5-7952B3?logo=bootstrap)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)
![License](https://img.shields.io/badge/License-MIT-green)

---

# 📖 Descripción

**AI Sales Assistant** es una aplicación web desarrollada con **FastAPI** e **Inteligencia Artificial** cuyo objetivo es ayudar a equipos comerciales a generar contenido profesional de forma rápida, consistente y personalizada.

El proyecto está diseñado siguiendo principios de **AI Software Engineering**, **Clean Architecture** y **Spec-Driven Development (SDD)**.

No es únicamente una aplicación funcional; es un proyecto concebido como un ejemplo de arquitectura profesional preparado para evolucionar hacia una plataforma empresarial basada en Inteligencia Artificial.

---

# 🎯 Objetivos

El sistema permite generar automáticamente:

- 📧 Emails comerciales
- 📄 Propuestas comerciales
- 🔄 Mensajes de seguimiento
- 💬 Mensajes para WhatsApp
- 📝 Resúmenes de clientes

A partir de la siguiente información:

- Cliente
- Empresa
- Sector
- Producto o servicio
- Necesidad del cliente
- Idioma
- Tono del mensaje

---

# 🏗 Arquitectura

El proyecto sigue una arquitectura basada en **Clean Architecture**, separando claramente cada responsabilidad.

```
Frontend

↓

FastAPI Routers

↓

Service Layer

↓

Repository Layer

↓

SQLAlchemy

↓

SQLite / PostgreSQL
```

---

# 📂 Estructura del Proyecto

```
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
│
├── docs/
│   ├── specs/
│   ├── adr/
│   ├── diagrams/
│   └── images/
│
├── README.md
├── LICENSE
└── .gitignore
=======

<p align="center">

<img src="https://img.shields.io/badge/Language-English-blue?style=for-the-badge" />
<img src="https://img.shields.io/badge/Idioma-Español-red?style=for-the-badge" />
<img src="https://img.shields.io/badge/Idioma-Português-green?style=for-the-badge" />
<img src="https://img.shields.io/badge/Langue-Français-purple?style=for-the-badge" />

</p>

<p align="center">

<img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
<img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" />
<img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
<img src="https://img.shields.io/badge/OpenAI-412991?style=for-the-badge" />
<img src="https://img.shields.io/badge/RAG-Retrieval--Augmented-orange?style=for-the-badge" />
<img src="https://img.shields.io/badge/MCP-Model_Context_Protocol-success?style=for-the-badge" />
<img src="https://img.shields.io/badge/SDD-Spec--Driven_Development-darkgreen?style=for-the-badge" />

</p>

<h1 align="center">
🤖 AI Automation Portfolio
</h1>

<p align="center">

Professional AI Software Engineering Portfolio built with Python, FastAPI, Large Language Models, AI Agents, RAG, MCP and Spec-Driven Development.

</p>

---

# 🚀 About

Welcome to my AI Automation Portfolio.

This repository is the central hub of my AI Software Engineering projects.

The objective is to build a collection of production-inspired applications demonstrating practical knowledge in Artificial Intelligence, Automation and Modern Software Engineering.

Every project follows a common architecture and engineering standards, allowing reusable components, scalable design and continuous evolution.

---

# 🎯 Objectives

- Build real AI applications
- Apply modern software engineering practices
- Develop enterprise-ready FastAPI services
- Integrate Large Language Models
- Build AI Agents
- Implement RAG systems
- Connect external APIs
- Automate business processes
- Showcase production-quality architecture

---

# 🏗 Development Methodology

Every project follows **Spec-Driven Development (SDD)**.

```

Requirements
│
▼
Architecture
│
▼
Planning
│
▼
Tasks
│
▼
Implementation
│
▼
Verification
│
▼
Documentation

```

Each repository contains:

```

specs/
architecture/
roadmap/
tasks/
docs/
tests/

>>>>>>> 5d74154766570dce29cc60c8015bd2b75ac0ac98
```

---

<<<<<<< HEAD
# ⚙ Tecnologías

## Backend

- Python 3.12+
- FastAPI
- SQLAlchemy
- Pydantic
- Alembic
=======
# 🧠 Technology Stack

## Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic

---
>>>>>>> 5d74154766570dce29cc60c8015bd2b75ac0ac98

## Frontend

- HTML5
<<<<<<< HEAD
- Bootstrap 5
- Jinja2
- JavaScript

## Inteligencia Artificial

- OpenAI API
- Prompt Engineering
- Arquitectura preparada para RAG

## Base de Datos

- SQLite (V1)
- PostgreSQL (V2)

## Infraestructura
=======
- Bootstrap
- JavaScript

---

## Databases

- SQLite
- PostgreSQL

---

## Artificial Intelligence

- OpenAI API
- Hugging Face
- Ollama
- Prompt Engineering
- AI Agents
- Retrieval-Augmented Generation (RAG)
- Model Context Protocol (MCP)

---

## Infrastructure
>>>>>>> 5d74154766570dce29cc60c8015bd2b75ac0ac98

- Docker
- Docker Compose
- Git
- GitHub

---

<<<<<<< HEAD
# 📑 Documentación

El proyecto sigue una metodología **Spec-Driven Development (SDD)**.

## Especificaciones (SPEC)

- Product Vision
- Functional Requirements
- Non Functional Requirements
- Use Cases
- Domain Model
- Database Design
- API Design
- Architecture
- Folder Structure
- Roadmap

## Architecture Decision Records (ADR)

- Clean Architecture
- FastAPI
- SQLAlchemy
- Repository Pattern
- Service Layer
- Prompt Engineering
- Pydantic Settings
- SQLite → PostgreSQL
- Future RAG

---

# 🚀 Roadmap

## Versión 1

- Generación de contenido mediante IA
- API REST
- Historial
- SQLite
- Swagger
- Bootstrap

## Versión 2

- PostgreSQL
- Docker
- JWT
- Usuarios
- Dashboard

## Versión 3

- Estadísticas
- Exportación PDF
- Exportación Word
- Gestión de clientes

## Versión 4

- RAG
- Ollama
- Hugging Face
- Embeddings

## Versión 5

- Odoo CRM
- MCP
- Multi-Agent Systems
- Enterprise AI Platform

---

# 📊 Estado del Proyecto

| Fase | Estado |
|------|--------|
| Análisis | ✅ |
| Especificaciones | ✅ |
| ADR | ✅ |
| Diseño | 🚧 |
| Desarrollo Backend | ⏳ |
| Frontend | ⏳ |
| Testing | ⏳ |
| Deploy | ⏳ |

---

# 🎓 Objetivos de Aprendizaje

Este proyecto tiene como finalidad profundizar en:

- AI Software Engineering
- FastAPI
- SQLAlchemy
- Clean Architecture
- Prompt Engineering
- APIs REST
- Docker
- PostgreSQL
- RAG
- MCP
- Multi-Agent Systems
- DevOps

---

# 👩‍💻 Autora

**Luciana Pinheiro**

Full Stack Developer · Odoo Consultant · AI & Automation Developer

GitHub: *(añadir enlace cuando el repositorio sea público)*

LinkedIn: *(añadir perfil)*

---

# 📄 Licencia

Este proyecto se distribuye bajo la licencia **MIT**.
=======
## Future Technologies

- Redis
- Kubernetes
- JWT Authentication
- n8n
- Power BI
- Odoo
- Vector Databases
- LangGraph

---

# 📂 Portfolio Projects

| Project | Description | Status |
|----------|-------------|--------|
| 🤖 AI Sales Assistant | Intelligent commercial assistant | 🚧 In Progress |
| 📄 AI Document Assistant | OCR + Intelligent Document Processing | 📅 Planned |
| 📚 Enterprise RAG Chatbot | Enterprise knowledge assistant | 📅 Planned |
| 📊 AI Forecast Dashboard | AI-powered analytics dashboard | 📅 Planned |
| 🗺 Smart Route Planner | Intelligent route optimization | 📅 Planned |
| 💻 AI Developer Assistant | AI assistant for developers | 📅 Planned |
| ✉ AI Email Generator | Business email generation | 📅 Planned |
| 🎙 AI Meeting Assistant | Meeting summaries & transcription | 📅 Planned |
| 📄 AI Resume Analyzer | CV analysis with LLMs | 📅 Planned |
| 🛍 AI Product Recommender | Recommendation engine | 📅 Planned |
| 📈 AI Business Assistant | Business reporting assistant | 📅 Planned |
| 🎓 AI Learning Assistant | Intelligent learning platform | 📅 Planned |

---

# 🏛 Common Architecture

```

```
            Frontend
                │
                ▼
      FastAPI REST API
                │
                ▼
     Business Services Layer
                │
                ▼
          AI Services
   OpenAI • Ollama • HF
                │
                ▼
  PostgreSQL / SQLite
```

```

---

# 📁 Repository Structure

```

ai-automation-portfolio/

│
├── docs/
├── roadmap/
├── architecture/
├── diagrams/
├── templates/
├── assets/
└── README.md

```

Each AI project lives in its own repository and follows the same engineering standards.

---

# 📚 Portfolio Roadmap

## Phase 1

- AI Sales Assistant
- AI Document Assistant
- Forecast Dashboard

---

## Phase 2

- Enterprise RAG
- Smart Route Planner
- AI Developer Assistant

---

## Phase 3

- AI Business Assistant
- AI Meeting Assistant
- AI Learning Assistant

---

## Phase 4

- MCP Integrations
- AI Agents
- Multi-Agent Systems
- Odoo AI Integration

---

# 🎯 Focus Areas

✔ AI Software Engineering

✔ Python Backend Development

✔ FastAPI

✔ REST APIs

✔ LLM Applications

✔ AI Agents

✔ Prompt Engineering

✔ RAG

✔ MCP

✔ Docker

✔ PostgreSQL

✔ Enterprise Automation

✔ Clean Architecture

✔ Spec-Driven Development

---

# 🌍 Portfolio Website

> https://lucpinheiro.github.io/

---

# 👩‍💻 Author

**Luciana Pinheiro**

AI Software Engineer

Python • FastAPI • AI • Automation • Odoo

GitHub

https://github.com/LucPinheiro

LinkedIn

https://linkedin.com/in/lucianapinheiro

---

<p align="center">

⭐ This portfolio is continuously evolving with new AI projects.

</p>


