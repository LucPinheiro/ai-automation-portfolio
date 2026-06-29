# 🤖 AI Sales Assistant – Asistente Comercial Inteligente


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
![](https://img.shields.io/badge/RAG-Futuro-orange?style=for-the-badge)
![](https://img.shields.io/badge/MCP-Futuro-success?style=for-the-badge)
![](https://img.shields.io/badge/SDD-Spec--Driven_Development-darkgreen?style=for-the-badge)

</p>

---

# 📖 Descripción

**AI Sales Assistant** es una aplicación web impulsada por Inteligencia Artificial, desarrollada con **FastAPI**, cuyo objetivo es ayudar a los equipos comerciales a generar comunicaciones profesionales de forma rápida, coherente y personalizada.

El proyecto sigue prácticas modernas de ingeniería de software, entre ellas:

* Spec-Driven Development (SDD)
* Clean Architecture
* Repository Pattern
* Service Layer
* APIs REST
* Desarrollo AI-First

El objetivo es construir una aplicación preparada para producción que pueda evolucionar hasta convertirse en una plataforma empresarial de asistencia comercial basada en Inteligencia Artificial.

---

# ✨ Funcionalidades

Permite generar automáticamente:

* 📧 Correos comerciales
* 📄 Propuestas comerciales
* 🔄 Correos de seguimiento
* 💬 Mensajes para WhatsApp
* 📝 Resúmenes de clientes

A partir de la siguiente información:

* Cliente
* Empresa
* Sector
* Producto o servicio
* Necesidad del cliente
* Idioma
* Tono del mensaje

---

# 🏗 Arquitectura

```text
Frontend
     │
     ▼
Routers FastAPI
     │
     ▼
Capa de Servicios
     │
     ▼
Capa de Repositorios
     │
     ▼
SQLAlchemy ORM
     │
     ▼
SQLite / PostgreSQL
```

---

# 📂 Estructura del Proyecto

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
│
├── docs/
│   ├── specs/
│   ├── adr/
│   ├── diagrams/
│   └── images/
│
├── tests/
├── docker/
├── README.md
├── LICENSE
└── .gitignore
```

---

# ⚙ Tecnologías

## Backend

* Python 3.12+
* FastAPI
* SQLAlchemy
* Pydantic
* Alembic

## Frontend

* HTML5
* Bootstrap 5
* JavaScript
* Jinja2

## Base de Datos

* SQLite
* PostgreSQL

## Inteligencia Artificial

* OpenAI API
* Prompt Engineering
* Integración futura con RAG
* Integración futura con MCP

## Infraestructura

* Docker
* Docker Compose
* Git
* GitHub

---

# 📑 Documentación

Este proyecto sigue la metodología **Spec-Driven Development (SDD)**.

## Especificaciones

* Visión del producto
* Requisitos funcionales
* Requisitos no funcionales
* Casos de uso
* Modelo de dominio
* Diseño de la base de datos
* Diseño de la API
* Arquitectura
* Estructura de carpetas
* Roadmap

## Registros de Decisiones de Arquitectura (ADR)

* Clean Architecture
* FastAPI
* Repository Pattern
* Service Layer
* SQLAlchemy
* Prompt Engineering
* Gestión de configuración
* Estrategia de base de datos
* Integración futura con RAG

---

# 🚀 Roadmap

## Versión 1

* Generación de contenido mediante IA
* API REST
* SQLite
* Interfaz con Bootstrap
* Documentación Swagger

## Versión 2

* PostgreSQL
* Docker
* Autenticación
* Gestión de usuarios

## Versión 3

* Gestión de clientes
* Exportación a PDF
* Exportación a Word
* Dashboard

## Versión 4

* RAG
* Ollama
* Hugging Face
* Embeddings

## Versión 5

* Integración con Odoo CRM
* MCP
* Agentes de IA
* Plataforma empresarial

---

# 📊 Estado del Proyecto

| Fase             | Estado |
| ---------------- | ------ |
| Análisis         | ✅      |
| Especificaciones | ✅      |
| Arquitectura     | ✅      |
| Backend          | 🚧     |
| Frontend         | ⏳      |
| Testing          | ⏳      |
| Despliegue       | ⏳      |

---

# 🎓 Objetivos de Aprendizaje

Este proyecto está orientado a adquirir y demostrar experiencia práctica en:

* AI Software Engineering
* FastAPI
* SQLAlchemy
* Clean Architecture
* Prompt Engineering
* APIs REST
* Docker
* PostgreSQL
* RAG
* MCP
* Agentes de IA
* DevOps

---

# 👩‍💻 Autora

**Luciana Pinheiro**

AI Software Engineer • Full Stack Developer • Consultora Odoo

**GitHub**

https://github.com/LucPinheiro

**Portfolio**

https://lucpinheiro.github.io/

**LinkedIn**

https://linkedin.com/in/lucianapinheiro

---

# 📄 Licencia

Este proyecto se distribuye bajo la licencia **MIT**.

---

<p align="center">

⭐ Este proyecto forma parte del **AI Automation Portfolio**.

</p>
