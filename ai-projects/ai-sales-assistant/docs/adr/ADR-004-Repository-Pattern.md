# ADR-004 — Adopción del Repository Pattern

**Estado:** Aceptado

**Fecha:** 26/06/2026

**Proyecto:** AI Sales Assistant – Intelligent Commercial Assistant

**Autor:** Luciana Pinheiro

---

# 1. Contexto

El proyecto AI Sales Assistant requiere una arquitectura que permita separar claramente la lógica de negocio del acceso a los datos.

La aplicación comenzará utilizando SQLite y evolucionará posteriormente hacia PostgreSQL, pudiendo incorporar además Redis u otros sistemas de almacenamiento.

Para evitar que la lógica de negocio dependa directamente del ORM o de la base de datos, es necesario introducir una capa de abstracción.

---

# 2. Problema

En muchas aplicaciones pequeñas los servicios acceden directamente a SQLAlchemy.

Por ejemplo:

```python
result = session.query(DocumentGeneration).all()
```

Aunque esta solución funciona, presenta varios inconvenientes:

* Los servicios conocen detalles de la base de datos.
* Se mezclan reglas de negocio con consultas SQL.
* Es difícil reutilizar consultas.
* Las pruebas unitarias requieren acceder a la base de datos.
* Cambiar el sistema de persistencia implica modificar la lógica de negocio.

Este enfoque incrementa el acoplamiento entre las capas del sistema.

---

# 3. Alternativas consideradas

## Opción 1 — Acceso directo mediante SQLAlchemy

### Ventajas

* Menor número de archivos.
* Desarrollo inicial más rápido.
* Menos abstracciones.

### Inconvenientes

* Alto acoplamiento.
* Baja mantenibilidad.
* Difícil reutilización.
* Servicios dependientes del ORM.

**Decisión:** Rechazada.

---

## Opción 2 — Repository Pattern

### Ventajas

* Separación clara entre negocio y persistencia.
* Reutilización de consultas.
* Mejor mantenibilidad.
* Fácil realización de pruebas.
* Independencia del ORM.

**Decisión:** Aceptada.

---

# 4. Decisión

Se adopta el **Repository Pattern** para encapsular todo el acceso a la base de datos.

Los repositorios serán la única capa autorizada para interactuar con SQLAlchemy.

Los servicios utilizarán exclusivamente los repositorios y nunca accederán directamente al ORM.

---

# 5. Arquitectura

```mermaid
flowchart TD

Router

↓

Service

↓

Repository

↓

SQLAlchemy

↓

SQLite / PostgreSQL
```

Cada capa tiene una responsabilidad claramente definida.

---

# 6. Responsabilidades

## Router

* Recibir peticiones HTTP.
* Validar datos.
* Invocar servicios.

---

## Service

* Aplicar reglas de negocio.
* Coordinar procesos.
* Gestionar excepciones.

---

## Repository

* Consultar la base de datos.
* Insertar registros.
* Actualizar información.
* Eliminar registros.
* Encapsular SQLAlchemy.

---

# 7. Ejemplo Conceptual

En lugar de hacer esto en un servicio:

```python
documents = session.query(DocumentGeneration).all()
```

El servicio utilizará un repositorio:

```python
documents = generation_repository.get_all()
```

El servicio desconoce cómo se recuperan los datos.

Únicamente conoce el comportamiento del repositorio.

---

# 8. Beneficios

La utilización del Repository Pattern aporta:

* Bajo acoplamiento.
* Alta cohesión.
* Código más limpio.
* Consultas reutilizables.
* Mejor organización.
* Mayor facilidad para escribir pruebas unitarias.
* Independencia del sistema de persistencia.

---

# 9. Consecuencias

## Positivas

* Cambio sencillo de SQLite a PostgreSQL.
* Posibilidad de utilizar otro ORM en el futuro.
* Servicios independientes del acceso a datos.
* Código más fácil de mantener.

## Negativas

* Mayor número de clases.
* Más archivos en el proyecto.
* Ligero incremento de complejidad inicial.

Estas desventajas se consideran asumibles dada la escalabilidad que proporciona el patrón.

---

# 10. Impacto Futuro

El Repository Pattern permitirá incorporar nuevas fuentes de datos sin modificar la lógica de negocio.

Ejemplos:

* PostgreSQL.
* Redis.
* APIs externas.
* Odoo.
* Sistemas RAG.
* Bases de datos vectoriales.

Los servicios continuarán utilizando los mismos métodos del repositorio.

---

# 11. Relación con otras decisiones

Este ADR complementa directamente:

* ADR-001 — Adopción de Clean Architecture.
* ADR-002 — ¿Por qué FastAPI?
* ADR-003 — ¿Por qué SQLAlchemy?
* ADR-005 — Service Layer.

El Repository Pattern constituye el puente entre la lógica de negocio y la infraestructura de persistencia.

---

# 12. Especificaciones relacionadas

Este ADR está relacionado con:

* SPEC-06 — Diseño de Base de Datos.
* SPEC-08 — Arquitectura del Software.
* SPEC-09 — Estructura de Carpetas.

---

# 13. Referencias

* Martin Fowler — *Patterns of Enterprise Application Architecture*.
* Eric Evans — *Domain-Driven Design*.
* Documentación oficial de SQLAlchemy.
* Clean Architecture — Robert C. Martin.

---

# 14. Conclusión

Se adopta el **Repository Pattern** para aislar completamente el acceso a los datos del resto de la aplicación.

Esta decisión mejora la mantenibilidad, facilita las pruebas unitarias y permite evolucionar la capa de persistencia sin afectar a la lógica de negocio.

El patrón encaja de forma natural con la Clean Architecture adoptada en el proyecto y constituye una pieza clave para mantener un código modular, desacoplado y preparado para crecer.
