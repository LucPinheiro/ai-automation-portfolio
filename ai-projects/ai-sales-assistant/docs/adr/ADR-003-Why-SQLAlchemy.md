# ADR-003 — ¿Por qué SQLAlchemy?

**Estado:** Aceptado

**Fecha:** 26/06/2026

**Proyecto:** AI Sales Assistant – Intelligent Commercial Assistant

**Autor:** Luciana Pinheiro

---

# 1. Contexto

El proyecto AI Sales Assistant necesita una capa de persistencia robusta, flexible y desacoplada de la base de datos.

En la primera versión se utilizará SQLite por su simplicidad de configuración, pero la arquitectura está diseñada para evolucionar hacia PostgreSQL sin modificar la lógica de negocio.

Por este motivo es necesario seleccionar un ORM maduro y ampliamente utilizado que facilite esta transición.

---

# 2. Problema

El proyecto requiere una solución que permita:

* Trabajar con distintas bases de datos.
* Mantener la independencia entre la lógica de negocio y la persistencia.
* Facilitar las migraciones mediante Alembic.
* Integrarse correctamente con FastAPI.
* Ofrecer un buen rendimiento y flexibilidad.

La elección del ORM condicionará el diseño de los modelos, repositorios y servicios durante todo el ciclo de vida del proyecto.

---

# 3. Alternativas consideradas

## Opción 1 — SQL directo

### Ventajas

* Máximo control sobre las consultas.
* Sin dependencias adicionales.
* Buen rendimiento.

### Inconvenientes

* Mayor cantidad de código.
* Difícil mantenimiento.
* Repetición de consultas.
* Mayor probabilidad de errores.
* Escasa reutilización.

**Decisión:** Rechazada.

---

## Opción 2 — SQLModel

### Ventajas

* Sintaxis sencilla.
* Integración con Pydantic.
* Basado en SQLAlchemy.

### Inconvenientes

* Proyecto más joven.
* Menor adopción en proyectos empresariales.
* Menor cantidad de documentación y ejemplos.

**Decisión:** Rechazada.

---

## Opción 3 — SQLAlchemy

### Ventajas

* ORM muy maduro.
* Gran comunidad.
* Excelente documentación.
* Compatible con múltiples motores de base de datos.
* Integración oficial con Alembic.
* Amplia adopción en proyectos empresariales.

**Decisión:** Aceptada.

---

# 4. Decisión

Se adopta **SQLAlchemy** como ORM principal del proyecto.

SQLAlchemy será el encargado de mapear las entidades del dominio a la base de datos y de proporcionar una capa de acceso a datos independiente del motor de almacenamiento.

---

# 5. Motivos de la decisión

SQLAlchemy ofrece numerosas ventajas para un proyecto con vocación de crecimiento:

* Independencia del proveedor de base de datos.
* Integración con SQLite y PostgreSQL.
* Excelente compatibilidad con FastAPI.
* Integración nativa con Alembic.
* Gran flexibilidad para consultas complejas.
* Amplia adopción en el ecosistema Python.

Además, permite combinar el uso del ORM con consultas SQL cuando sea necesario.

---

# 6. Impacto en la Arquitectura

SQLAlchemy quedará encapsulado dentro de la capa **Repository**.

La arquitectura será la siguiente:

```mermaid
flowchart TD

Service Layer

↓

Repository Layer

↓

SQLAlchemy ORM

↓

SQLite / PostgreSQL
```

Los **Services** nunca accederán directamente al ORM.

Toda interacción con la base de datos deberá realizarse a través de los repositorios.

---

# 7. Beneficios

La utilización de SQLAlchemy proporciona:

* Separación entre dominio y persistencia.
* Código más limpio.
* Reutilización de consultas.
* Facilidad para cambiar de base de datos.
* Integración con Alembic.
* Compatibilidad con proyectos de gran tamaño.

---

# 8. Consecuencias

## Positivas

* Mayor mantenibilidad.
* Independencia del motor de base de datos.
* Integración sencilla con FastAPI.
* Arquitectura preparada para crecer.
* Facilidad para incorporar PostgreSQL.

## Negativas

* Curva de aprendizaje superior a otros ORMs más simples.
* Configuración inicial algo más extensa.
* Necesidad de comprender el funcionamiento de las sesiones y transacciones.

Estas desventajas son aceptables considerando la flexibilidad obtenida.

---

# 9. Compatibilidad futura

La elección de SQLAlchemy permitirá integrar fácilmente:

* PostgreSQL.
* MySQL.
* MariaDB.
* SQL Server.
* Oracle.
* SQLite.

Además, facilitará el uso de:

* Alembic.
* Repository Pattern.
* Unit of Work (si fuese necesario).
* Testing con bases de datos temporales.

---

# 10. Relación con otras decisiones

Esta decisión complementa:

* ADR-001 — Adopción de Clean Architecture.
* ADR-002 — ¿Por qué FastAPI?
* ADR-004 — Repository Pattern.
* ADR-005 — Service Layer.

SQLAlchemy se utilizará únicamente en la capa de persistencia, manteniendo desacoplada la lógica de negocio.

---

# 11. Especificaciones relacionadas

Este ADR está relacionado con:

* SPEC-06 — Diseño de Base de Datos.
* SPEC-08 — Arquitectura del Software.
* SPEC-09 — Estructura de Carpetas.

---

# 12. Referencias

* Documentación oficial de SQLAlchemy.
* Documentación oficial de Alembic.
* FastAPI SQL Databases Tutorial.
* Patterns of Enterprise Application Architecture — Martin Fowler.

---

# 13. Conclusión

Se adopta **SQLAlchemy** como ORM principal del AI Sales Assistant por su madurez, flexibilidad y amplia adopción en proyectos profesionales.

Esta decisión permite mantener una separación clara entre la lógica de negocio y la persistencia de datos, facilita la evolución desde SQLite hacia PostgreSQL y proporciona una base sólida para el crecimiento del proyecto sin comprometer la mantenibilidad ni la escalabilidad de la arquitectura.
