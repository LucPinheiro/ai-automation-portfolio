# SPEC-03 — Non-Functional Requirements

**Proyecto:** AI Sales Assistant – Intelligent Commercial Assistant

**Versión:** 1.0

**Estado:** Draft

**Autor:** Luciana Pinheiro

**Metodología:** Spec-Driven Development (SDD)

---

# 1. Objetivo

Este documento define los requisitos no funcionales del sistema.

Los requisitos no funcionales describen **cómo debe comportarse la aplicación**, garantizando calidad, seguridad, mantenibilidad, rendimiento y escalabilidad.

---

# 2. Rendimiento

## NFR-001

El tiempo medio de respuesta para las operaciones de lectura deberá ser inferior a **500 ms**, excluyendo el tiempo de respuesta del proveedor de IA.

---

## NFR-002

La generación de contenido dependerá del tiempo de respuesta del modelo de IA, pero la aplicación deberá informar al usuario del estado de la operación.

---

## NFR-003

Las consultas a la base de datos deberán minimizar el número de accesos innecesarios.

---

# 3. Disponibilidad

## NFR-004

La aplicación deberá poder ejecutarse localmente mediante Docker Compose.

---

## NFR-005

El sistema deberá poder migrarse posteriormente a un entorno cloud sin cambios significativos en la arquitectura.

---

# 4. Escalabilidad

La arquitectura deberá permitir incorporar en futuras versiones:

* PostgreSQL
* Redis
* JWT
* Kubernetes
* Balanceo de carga
* Sistemas RAG
* Agentes de IA
* Integraciones con ERP y CRM

Sin necesidad de reescribir la lógica de negocio.

---

# 5. Seguridad

## NFR-006

Las claves API nunca deberán almacenarse en el código fuente.

---

## NFR-007

Toda la configuración sensible deberá gestionarse mediante variables de entorno.

---

## NFR-008

Las entradas del usuario deberán validarse antes de ser procesadas.

---

## NFR-009

Los errores internos no deberán mostrar información sensible al usuario.

---

# 6. Mantenibilidad

El proyecto deberá seguir una arquitectura modular.

Cada módulo tendrá una única responsabilidad.

Se aplicarán los principios:

* SOLID
* DRY
* Clean Code
* Separation of Concerns

---

# 7. Calidad del código

Todo el código deberá cumplir las siguientes normas:

* Tipado completo mediante type hints.
* Docstrings en clases y funciones públicas.
* Nombres descriptivos.
* Funciones pequeñas y reutilizables.
* Eliminación de duplicidad de código.

---

# 8. Logging

La aplicación deberá registrar:

* Inicio del sistema.
* Errores.
* Excepciones.
* Solicitudes de generación.
* Eventos importantes.

El sistema de logging deberá facilitar el diagnóstico de incidencias.

---

# 9. Configuración

La configuración de la aplicación deberá centralizarse mediante Pydantic Settings.

No se permitirán valores de configuración distribuidos por el código.

---

# 10. Base de datos

La capa de acceso a datos deberá ser independiente del proveedor de base de datos.

La sustitución de SQLite por PostgreSQL no deberá requerir cambios en la lógica de negocio.

---

# 11. API

La API REST deberá:

* seguir principios RESTful;
* utilizar códigos HTTP adecuados;
* devolver respuestas consistentes;
* validar automáticamente las entradas;
* documentarse mediante OpenAPI y Swagger.

---

# 12. Frontend

La interfaz deberá ser:

* responsive;
* sencilla;
* intuitiva;
* compatible con navegadores modernos.

La primera versión utilizará Bootstrap 5 y Jinja2.

---

# 13. Observabilidad

La aplicación deberá facilitar el seguimiento del comportamiento del sistema mediante:

* logging;
* mensajes de error controlados;
* trazabilidad de operaciones.

---

# 14. Documentación

El proyecto deberá incluir:

* README profesional.
* Especificaciones SDD.
* Diagramas Mermaid.
* Documentación OpenAPI.
* ADR (Architecture Decision Records).

Toda la documentación deberá mantenerse alineada con la implementación.

---

# 15. Pruebas

La arquitectura deberá facilitar la incorporación de pruebas automatizadas mediante pytest.

Las capas de negocio deberán poder probarse de forma independiente.

---

# 16. Portabilidad

La aplicación deberá poder ejecutarse en:

* Windows
* Linux
* macOS

Sin modificaciones en el código fuente.

---

# 17. Compatibilidad futura

La arquitectura quedará preparada para integrar:

* OpenAI
* Ollama
* Hugging Face
* LangChain
* MCP
* Sistemas Multi-Agent
* Odoo CRM
* APIs REST externas

---

# 18. Criterios de calidad

El proyecto se considerará conforme cuando:

* La arquitectura sea modular.
* No existan dependencias innecesarias entre capas.
* La configuración esté externalizada.
* El código siga buenas prácticas de ingeniería de software.
* La documentación esté actualizada.
* El sistema pueda evolucionar sin afectar a los módulos existentes.
