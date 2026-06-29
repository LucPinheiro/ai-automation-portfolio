# ADR-002 — ¿Por qué FastAPI?

**Estado:** Aceptado

**Fecha:** 26/06/2026

**Proyecto:** AI Sales Assistant – Intelligent Commercial Assistant

**Autor:** Luciana Pinheiro

---

# 1. Contexto

El proyecto **AI Sales Assistant** tiene como objetivo desarrollar una aplicación web moderna basada en Inteligencia Artificial para la generación de contenido comercial.

La aplicación necesita ofrecer:

* Una API REST profesional.
* Alto rendimiento.
* Validación automática de datos.
* Documentación de la API.
* Integración sencilla con proveedores de IA.
* Arquitectura preparada para evolucionar.

La elección del framework backend condiciona directamente la mantenibilidad, el rendimiento y la facilidad de desarrollo del proyecto.

---

# 2. Problema

Existen varios frameworks Python capaces de desarrollar APIs REST.

La decisión consiste en seleccionar aquel que mejor equilibre:

* rendimiento;
* productividad;
* facilidad de mantenimiento;
* calidad del código;
* documentación automática;
* integración con tecnologías de IA.

El framework elegido deberá acompañar al proyecto durante toda su evolución, desde un MVP hasta una plataforma empresarial.

---

# 3. Alternativas consideradas

## Opción 1 — Flask

### Ventajas

* Framework ligero.
* Gran comunidad.
* Muy sencillo de comenzar.

### Inconvenientes

* No incorpora validación automática.
* No genera documentación OpenAPI de forma nativa.
* Requiere instalar múltiples librerías adicionales.
* Mayor esfuerzo para mantener proyectos grandes.

**Decisión:** Rechazada.

---

## Opción 2 — Django

### Ventajas

* Framework muy maduro.
* Excelente ORM.
* Sistema de autenticación integrado.
* Panel de administración incluido.

### Inconvenientes

* Excesivamente grande para un proyecto centrado en APIs.
* Incluye funcionalidades que no son necesarias.
* Arquitectura menos adecuada para microservicios y aplicaciones de IA.

**Decisión:** Rechazada.

---

## Opción 3 — FastAPI

### Ventajas

* Alto rendimiento basado en ASGI.
* Soporte nativo para programación asíncrona.
* Integración directa con Pydantic.
* Documentación OpenAPI automática.
* Swagger UI integrado.
* ReDoc integrado.
* Excelente experiencia de desarrollo.
* Muy utilizado en proyectos de Inteligencia Artificial.

**Decisión:** Aceptada.

---

# 4. Decisión

Se adopta **FastAPI** como framework principal para el desarrollo del backend del proyecto.

FastAPI proporciona el mejor equilibrio entre rendimiento, simplicidad y productividad, además de integrarse perfectamente con el ecosistema moderno de Python y con aplicaciones basadas en IA.

---

# 5. Motivos de la decisión

FastAPI aporta ventajas especialmente relevantes para este proyecto:

* Validación automática mediante Pydantic.
* Documentación automática de la API.
* Compatibilidad con OpenAPI.
* Excelente rendimiento.
* Código limpio gracias al uso de type hints.
* Fácil integración con SQLAlchemy.
* Excelente integración con servicios de IA como OpenAI, Ollama o Hugging Face.

---

# 6. Impacto en la Arquitectura

FastAPI únicamente será responsable de la capa de presentación de la API.

Toda la lógica de negocio permanecerá fuera del framework.

La estructura será la siguiente:

```mermaid
flowchart TD

Cliente

↓

FastAPI Routers

↓

Service Layer

↓

Repository Layer

↓

Base de Datos
```

Esto garantiza que la lógica del negocio permanezca desacoplada del framework web.

---

# 7. Beneficios

La adopción de FastAPI proporciona:

* Mayor velocidad de desarrollo.
* Código más limpio.
* Validaciones automáticas.
* Documentación actualizada automáticamente.
* Excelente soporte para pruebas.
* Alta escalabilidad.
* Preparación para arquitecturas modernas.

---

# 8. Consecuencias

## Positivas

* Reducción del código repetitivo.
* Mejor experiencia para el desarrollador.
* API auto documentada.
* Menor esfuerzo de mantenimiento.
* Integración sencilla con herramientas modernas.

## Negativas

* Menor cantidad de funcionalidades integradas que Django.
* Algunas características empresariales requieren librerías adicionales.
* Curva de aprendizaje inicial para programación asíncrona.

Estas desventajas se consideran aceptables dadas las necesidades del proyecto.

---

# 9. Compatibilidad Futura

La elección de FastAPI facilita la incorporación de:

* PostgreSQL.
* Redis.
* Docker.
* Kubernetes.
* JWT.
* OAuth2.
* OpenAI.
* Ollama.
* Hugging Face.
* LangChain.
* MCP.
* Sistemas RAG.
* Integración con Odoo CRM.

---

# 10. Relación con otras decisiones

Esta decisión complementa directamente:

* ADR-001 — Adopción de Clean Architecture.
* ADR-003 — ¿Por qué SQLAlchemy?
* ADR-004 — Repository Pattern.
* ADR-005 — Service Layer.

FastAPI actúa únicamente como framework de exposición de la API, mientras que la lógica de negocio permanece aislada en la arquitectura definida.

---

# 11. Especificaciones relacionadas

Este ADR está relacionado con:

* SPEC-07 — Diseño de la API.
* SPEC-08 — Arquitectura del Software.
* SPEC-09 — Estructura de Carpetas.

---

# 12. Referencias

* Documentación oficial de FastAPI.
* Documentación oficial de Pydantic.
* Especificación OpenAPI.
* Documentación de Starlette.
* ASGI Specification.

---

# 13. Conclusión

Se adopta **FastAPI** como framework principal del backend por ofrecer un equilibrio óptimo entre rendimiento, productividad y calidad del código.

Su integración con Pydantic, la generación automática de documentación OpenAPI y su amplia adopción en proyectos de Inteligencia Artificial lo convierten en la opción más adecuada para el AI Sales Assistant.

Esta decisión garantiza una base sólida para el crecimiento del proyecto y facilita futuras integraciones con nuevas tecnologías y plataformas empresariales.
