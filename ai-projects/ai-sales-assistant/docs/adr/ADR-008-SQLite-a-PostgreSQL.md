# ADR-008 — Adopción de SQLite en la versión inicial y migración futura a PostgreSQL

**Estado:** Aceptado

**Fecha:** 26/06/2026

**Proyecto:** AI Sales Assistant – Intelligent Commercial Assistant

**Autor:** Luciana Pinheiro

---

# 1. Contexto

El AI Sales Assistant comienza como un MVP (Minimum Viable Product) cuyo objetivo principal es validar la arquitectura, la lógica de negocio y la integración con modelos de Inteligencia Artificial.

Durante esta primera fase, el proyecto será desarrollado y probado principalmente en un entorno local.

No existe inicialmente la necesidad de soportar múltiples usuarios concurrentes ni grandes volúmenes de información.

---

# 2. Problema

La aplicación necesita persistir la información generada por la IA.

Debe elegirse un motor de base de datos que permita:

* desarrollo rápido;
* configuración sencilla;
* facilidad de despliegue;
* evolución futura hacia producción.

Elegir directamente una base de datos empresarial puede aumentar innecesariamente la complejidad del proyecto durante sus primeras etapas.

---

# 3. Alternativas consideradas

## Opción 1 — PostgreSQL desde el inicio

### Ventajas

* Base de datos preparada para producción.
* Excelente rendimiento.
* Gran escalabilidad.
* Amplio soporte para funciones avanzadas.

### Inconvenientes

* Configuración inicial más compleja.
* Necesidad de instalar un servidor.
* Mayor tiempo de preparación del entorno.
* Incremento de la complejidad del MVP.

**Decisión:** Rechazada para la versión inicial.

---

## Opción 2 — SQLite para el MVP y PostgreSQL posteriormente

### Ventajas

* Configuración inmediata.
* Sin instalación de servidor.
* Ideal para desarrollo local.
* Compatible con SQLAlchemy.
* Migración sencilla a PostgreSQL.

### Inconvenientes

* Limitaciones en concurrencia.
* No adecuada para aplicaciones con muchos usuarios simultáneos.
* Funcionalidad más limitada que PostgreSQL.

**Decisión:** Aceptada.

---

# 4. Decisión

Se utilizará **SQLite** como base de datos durante la primera versión del proyecto.

La arquitectura se diseñará para permitir la sustitución por **PostgreSQL** sin modificar la lógica de negocio.

El acceso a datos se realizará exclusivamente mediante SQLAlchemy y el Repository Pattern.

---

# 5. Arquitectura

```mermaid
flowchart TD

Service Layer

↓

Repository Layer

↓

SQLAlchemy ORM

↓

SQLite

↓

(PostgreSQL en futuras versiones)
```

La aplicación nunca accederá directamente al motor de base de datos.

---

# 6. Motivos de la decisión

SQLite ofrece importantes ventajas para un MVP:

* No requiere instalación.
* Base de datos almacenada en un único archivo.
* Integración inmediata con FastAPI.
* Compatible con SQLAlchemy.
* Compatible con Alembic.
* Facilita el aprendizaje y el desarrollo iterativo.

El objetivo es centrar el esfuerzo inicial en la arquitectura y la funcionalidad del sistema, no en la administración de infraestructura.

---

# 7. Beneficios

La utilización inicial de SQLite proporciona:

* Mayor rapidez de desarrollo.
* Entorno sencillo para nuevos colaboradores.
* Menor tiempo de configuración.
* Facilidad para realizar pruebas.
* Menor consumo de recursos.

---

# 8. Consecuencias

## Positivas

* Desarrollo más ágil.
* Menor complejidad inicial.
* Arquitectura preparada para crecer.
* Curva de aprendizaje más suave.

## Negativas

* Limitaciones en escenarios de alta concurrencia.
* No adecuada para despliegues empresariales.
* Menor rendimiento en cargas elevadas.

Estas limitaciones son aceptables para un MVP.

---

# 9. Estrategia de migración

Cuando el proyecto alcance la versión 2 se realizará la migración a PostgreSQL.

Gracias a SQLAlchemy y Alembic, el cambio afectará únicamente a:

* Configuración de conexión.
* Variables de entorno.
* Despliegue.

No será necesario modificar:

* Routers.
* Services.
* Repositories.
* Prompt Engine.
* Frontend.

---

# 10. Compatibilidad futura

La arquitectura quedará preparada para integrar:

* PostgreSQL.
* Redis.
* Bases de datos vectoriales.
* Almacenamiento distribuido.

Todo ello sin alterar la lógica principal del sistema.

---

# 11. Relación con otras decisiones

Este ADR complementa:

* ADR-001 — Adopción de Clean Architecture.
* ADR-003 — ¿Por qué SQLAlchemy?
* ADR-004 — Adopción del Repository Pattern.
* ADR-007 — Adopción de Pydantic Settings.

La combinación de estas decisiones garantiza que el motor de base de datos pueda sustituirse con un impacto mínimo.

---

# 12. Especificaciones relacionadas

Este ADR está relacionado con:

* SPEC-06 — Diseño de Base de Datos.
* SPEC-08 — Arquitectura del Software.
* SPEC-09 — Estructura de Carpetas.
* SPEC-10 — Roadmap.

---

# 13. Referencias

* Documentación oficial de SQLite.
* Documentación oficial de PostgreSQL.
* Documentación oficial de SQLAlchemy.
* Documentación oficial de Alembic.
* Twelve-Factor App.

---

# 14. Conclusión

Se adopta **SQLite** como base de datos para la primera versión del AI Sales Assistant debido a su simplicidad, rapidez de configuración y excelente integración con SQLAlchemy.

La arquitectura queda preparada para migrar posteriormente a **PostgreSQL** sin modificar la lógica de negocio, garantizando una evolución ordenada desde un MVP hasta una aplicación preparada para entornos de producción.

Esta estrategia permite centrar el desarrollo inicial en la calidad del software, manteniendo una base sólida para el crecimiento futuro del proyecto.
