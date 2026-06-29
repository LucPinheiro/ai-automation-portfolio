# ADR-005 — Adopción de Service Layer

**Estado:** Aceptado

**Fecha:** 26/06/2026

**Proyecto:** AI Sales Assistant – Intelligent Commercial Assistant

**Autor:** Luciana Pinheiro

---

# 1. Contexto

El proyecto AI Sales Assistant implementa una arquitectura basada en Clean Architecture con el objetivo de mantener una clara separación entre la presentación, la lógica de negocio y la persistencia.

La aplicación realizará operaciones que implican múltiples pasos:

* Validar datos de entrada.
* Construir prompts.
* Invocar un proveedor de IA.
* Procesar la respuesta.
* Guardar la información en la base de datos.
* Devolver el resultado al usuario.

Estas operaciones constituyen la lógica de negocio del sistema y deben mantenerse independientes tanto del framework web como de la base de datos.

---

# 2. Problema

En muchas aplicaciones pequeñas la lógica de negocio termina implementándose dentro de los Routers.

Por ejemplo:

* Validaciones.
* Construcción del prompt.
* Llamadas a OpenAI.
* Consultas a la base de datos.
* Tratamiento de errores.

Este enfoque provoca:

* Routers excesivamente grandes.
* Código difícil de mantener.
* Duplicación de lógica.
* Escasa reutilización.
* Pruebas unitarias más complejas.

---

# 3. Alternativas consideradas

## Opción 1 — Lógica dentro de los Routers

### Ventajas

* Menor número de archivos.
* Desarrollo inicial más rápido.

### Inconvenientes

* Alto acoplamiento.
* Difícil reutilización.
* Baja mantenibilidad.
* Mezcla de responsabilidades.

**Decisión:** Rechazada.

---

## Opción 2 — Service Layer

### Ventajas

* Centraliza la lógica de negocio.
* Favorece la reutilización.
* Facilita las pruebas unitarias.
* Mejora la organización del código.
* Reduce el acoplamiento.

**Decisión:** Aceptada.

---

# 4. Decisión

Se adopta una **Service Layer** como núcleo funcional del proyecto.

Toda la lógica de negocio se implementará dentro de la carpeta:

```text
app/services/
```

Los Routers actuarán únicamente como punto de entrada HTTP y delegarán todo el procesamiento en los servicios correspondientes.

---

# 5. Arquitectura

```mermaid
flowchart TD

Cliente

↓

FastAPI Router

↓

Service Layer

↓

Repository Layer

↓

Base de Datos
```

Cuando sea necesario generar contenido mediante IA, el Service también coordinará el uso del Prompt Engine y del proveedor de IA.

---

# 6. Responsabilidades del Service Layer

Los servicios serán responsables de:

* Aplicar las reglas de negocio.
* Coordinar el flujo de generación.
* Invocar los repositorios.
* Construir los prompts.
* Comunicarse con el proveedor de IA.
* Gestionar excepciones del dominio.
* Orquestar operaciones complejas.

---

# 7. Responsabilidades que NO tendrá

Los servicios no deberán:

* Acceder directamente a HTTP.
* Construir respuestas HTTP.
* Renderizar plantillas HTML.
* Ejecutar consultas SQL.
* Conocer detalles de FastAPI.

Estas responsabilidades pertenecen a otras capas de la arquitectura.

---

# 8. Ejemplo Conceptual

En lugar de implementar la lógica en el Router:

```python
@router.post("/generate")
def generate():
    ...
```

El Router simplemente delegará:

```python
generation_service.generate_document(request)
```

Será el servicio quien coordine todo el proceso.

---

# 9. Beneficios

La adopción de una Service Layer proporciona:

* Separación clara de responsabilidades.
* Código más limpio.
* Mayor reutilización.
* Menor duplicación.
* Mayor facilidad para escribir pruebas unitarias.
* Independencia del framework web.

---

# 10. Consecuencias

## Positivas

* Arquitectura más mantenible.
* Servicios reutilizables desde distintos puntos de entrada.
* Menor acoplamiento.
* Mayor facilidad para evolucionar el proyecto.

## Negativas

* Incremento del número de clases.
* Mayor estructura inicial.
* Curva de aprendizaje ligeramente superior.

Se considera una decisión adecuada para un proyecto con vocación de crecimiento.

---

# 11. Relación con otras decisiones

Este ADR complementa:

* ADR-001 — Adopción de Clean Architecture.
* ADR-002 — ¿Por qué FastAPI?
* ADR-003 — ¿Por qué SQLAlchemy?
* ADR-004 — Adopción del Repository Pattern.

Juntos definen la organización principal de la aplicación.

---

# 12. Especificaciones relacionadas

Este ADR está relacionado con:

* SPEC-07 — Diseño de la API.
* SPEC-08 — Arquitectura del Software.
* SPEC-09 — Estructura de Carpetas.

---

# 13. Referencias

* Martin Fowler — *Patterns of Enterprise Application Architecture*.
* Robert C. Martin — *Clean Architecture*.
* Domain-Driven Design — Eric Evans.
* Documentación oficial de FastAPI.

---

# 14. Conclusión

Se adopta una **Service Layer** para centralizar toda la lógica de negocio del AI Sales Assistant.

Esta decisión permite mantener los Routers ligeros, desacoplar la aplicación del framework web y facilitar la evolución del proyecto.

La Service Layer actuará como el núcleo funcional del sistema, coordinando la interacción entre los repositorios, el motor de prompts y los proveedores de Inteligencia Artificial, garantizando una arquitectura modular, mantenible y preparada para futuras ampliaciones.
