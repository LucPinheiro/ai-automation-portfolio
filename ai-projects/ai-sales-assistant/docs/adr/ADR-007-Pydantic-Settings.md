# ADR-007 — Adopción de Pydantic Settings para la Configuración

**Estado:** Aceptado

**Fecha:** 26/06/2026

**Proyecto:** AI Sales Assistant – Intelligent Commercial Assistant

**Autor:** Luciana Pinheiro

---

# 1. Contexto

El proyecto AI Sales Assistant utilizará distintos servicios y configuraciones durante su ciclo de vida.

Entre ellos:

* Base de datos.
* Claves API.
* Configuración de OpenAI.
* Configuración de Docker.
* Variables de entorno.
* Parámetros de desarrollo y producción.

Es necesario disponer de un mecanismo centralizado para gestionar toda la configuración de forma segura y mantenible.

---

# 2. Problema

Una práctica habitual consiste en escribir la configuración directamente dentro del código.

Ejemplo:

```python
OPENAI_API_KEY = "mi_clave"
DATABASE_URL = "sqlite:///database.db"
DEBUG = True
```

Este enfoque presenta varios problemas:

* Exposición de información sensible.
* Dificultad para cambiar de entorno.
* Duplicación de configuración.
* Riesgo de subir credenciales al repositorio.
* Baja mantenibilidad.

---

# 3. Alternativas consideradas

## Opción 1 — Configuración directamente en el código

### Ventajas

* Muy sencilla.
* Sin dependencias adicionales.

### Inconvenientes

* Poco segura.
* Difícil de mantener.
* No escalable.
* No adecuada para producción.

**Decisión:** Rechazada.

---

## Opción 2 — Uso de variables de entorno con Pydantic Settings

### Ventajas

* Configuración centralizada.
* Mayor seguridad.
* Validación automática.
* Compatible con Docker.
* Fácil cambio entre entornos.

**Decisión:** Aceptada.

---

# 4. Decisión

Se utilizará **Pydantic Settings** como mecanismo principal para gestionar toda la configuración del proyecto.

La configuración se centralizará en:

```text
app/config/settings.py
```

Los valores se obtendrán desde variables de entorno y archivos `.env`.

---

# 5. Organización

La estructura será la siguiente:

```text
app/

config/

settings.py

.env

.env.example
```

El archivo `.env` contendrá la configuración local y nunca se incluirá en el repositorio.

El archivo `.env.example` servirá como plantilla para otros desarrolladores.

---

# 6. Variables previstas

Entre las variables que se gestionarán mediante Pydantic Settings se encuentran:

* DATABASE_URL
* OPENAI_API_KEY
* APP_NAME
* APP_VERSION
* DEBUG
* LOG_LEVEL
* SECRET_KEY (futuro)
* JWT_ALGORITHM (futuro)
* REDIS_URL (futuro)

---

# 7. Arquitectura

```mermaid
flowchart TD

Variables de Entorno

↓

Pydantic Settings

↓

Configuración Centralizada

↓

Resto de la Aplicación
```

Todos los componentes accederán a la configuración a través de una única instancia de Settings.

---

# 8. Beneficios

La utilización de Pydantic Settings proporciona:

* Configuración centralizada.
* Validación automática.
* Tipado fuerte.
* Seguridad.
* Compatibilidad con Docker.
* Fácil despliegue en distintos entornos.

---

# 9. Consecuencias

## Positivas

* Menor riesgo de exponer credenciales.
* Configuración consistente.
* Código más limpio.
* Facilidad para desplegar en producción.
* Escalabilidad.

## Negativas

* Ligero incremento en la configuración inicial.
* Necesidad de mantener el archivo `.env.example`.

Estas desventajas son mínimas frente a las ventajas obtenidas.

---

# 10. Impacto Futuro

Esta decisión facilitará el despliegue del proyecto en:

* Docker.
* Docker Compose.
* Railway.
* Render.
* Azure.
* AWS.
* Google Cloud.
* Kubernetes.

Cada entorno podrá definir sus propias variables sin modificar el código.

---

# 11. Relación con otras decisiones

Este ADR complementa:

* ADR-001 — Adopción de Clean Architecture.
* ADR-002 — ¿Por qué FastAPI?
* ADR-003 — ¿Por qué SQLAlchemy?
* ADR-005 — Adopción de Service Layer.

La configuración se considera un componente transversal de la arquitectura y no debe depender de ninguna capa concreta.

---

# 12. Especificaciones relacionadas

Este ADR está relacionado con:

* SPEC-03 — Requisitos No Funcionales.
* SPEC-08 — Arquitectura del Software.
* SPEC-09 — Estructura de Carpetas.

---

# 13. Referencias

* Documentación oficial de Pydantic Settings.
* Twelve-Factor App.
* Documentación oficial de FastAPI.
* Buenas prácticas de gestión de configuración en aplicaciones Python.

---

# 14. Conclusión

Se adopta **Pydantic Settings** como solución para la gestión centralizada de la configuración del AI Sales Assistant.

Esta decisión mejora la seguridad, facilita el despliegue en distintos entornos y mantiene la configuración desacoplada de la lógica de negocio.

Además, prepara el proyecto para evolucionar hacia una aplicación lista para producción, siguiendo las buenas prácticas recomendadas para aplicaciones modernas desarrolladas con FastAPI.
