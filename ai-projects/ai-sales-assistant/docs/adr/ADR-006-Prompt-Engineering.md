# ADR-006 — Separación del Prompt Engineering

**Estado:** Aceptado

**Fecha:** 26/06/2026

**Proyecto:** AI Sales Assistant – Intelligent Commercial Assistant

**Autor:** Luciana Pinheiro

---

# 1. Contexto

El objetivo principal del AI Sales Assistant es generar contenido comercial utilizando modelos de lenguaje (LLMs).

La calidad del contenido generado depende directamente del prompt enviado al modelo de IA.

Por este motivo, los prompts dejan de ser simples cadenas de texto y pasan a convertirse en un activo funcional del sistema que debe poder evolucionar independientemente del resto del código.

---

# 2. Problema

En muchos proyectos los prompts se escriben directamente dentro de los servicios.

Ejemplo:

```python
prompt = f"""
Escribe un email comercial para...
"""
```

Este enfoque presenta varios inconvenientes:

* Prompts mezclados con la lógica de negocio.
* Difícil mantenimiento.
* Duplicación de instrucciones.
* Imposibilidad de reutilización.
* Mayor dificultad para experimentar con distintas versiones del prompt.
* Escasa escalabilidad.

A medida que aumenta el número de documentos soportados, esta situación se vuelve inmanejable.

---

# 3. Alternativas consideradas

## Opción 1 — Prompts dentro de los Services

### Ventajas

* Desarrollo inicial rápido.
* Menor número de archivos.

### Inconvenientes

* Mezcla de responsabilidades.
* Baja reutilización.
* Difícil mantenimiento.
* Complicada evolución del Prompt Engineering.

**Decisión:** Rechazada.

---

## Opción 2 — Prompts separados en módulos independientes

### Ventajas

* Separación clara de responsabilidades.
* Reutilización.
* Fácil mantenimiento.
* Versionado independiente.
* Preparación para futuras estrategias de Prompt Engineering.

**Decisión:** Aceptada.

---

# 4. Decisión

Todos los prompts del proyecto se almacenarán en una carpeta específica:

```text
app/prompts/
```

Cada tipo de documento dispondrá de su propio módulo.

Ejemplo:

```text
app/prompts/

email_prompt.py

proposal_prompt.py

followup_prompt.py

whatsapp_prompt.py

summary_prompt.py
```

Los servicios nunca construirán directamente los prompts.

---

# 5. Responsabilidades del Prompt Engine

El Prompt Engine será responsable de:

* Construir el prompt final.
* Seleccionar la plantilla adecuada.
* Incorporar los datos del usuario.
* Mantener instrucciones comunes.
* Preparar el contexto para el modelo.

Los Services únicamente solicitarán el prompt necesario.

---

# 6. Arquitectura

```mermaid
flowchart TD

Router

↓

Service

↓

Prompt Engine

↓

Proveedor IA

↓

Respuesta
```

El Prompt Engine actuará como una capa especializada dentro de la arquitectura.

---

# 7. Beneficios

Separar los prompts proporciona:

* Mejor organización.
* Código más limpio.
* Reutilización.
* Facilidad para experimentar.
* Menor acoplamiento.
* Preparación para futuras mejoras de IA.

---

# 8. Consecuencias

## Positivas

* Evolución independiente del Prompt Engineering.
* Posibilidad de versionar prompts.
* Mayor facilidad para realizar pruebas.
* Mejor mantenibilidad.

## Negativas

* Incremento del número de módulos.
* Ligera complejidad adicional.

Los beneficios superan ampliamente estos inconvenientes.

---

# 9. Evolución futura

La separación de los prompts permitirá incorporar posteriormente:

* Plantillas dinámicas.
* Prompt Templates parametrizados.
* Versionado de prompts.
* Prompts almacenados en base de datos.
* Prompt Chaining.
* Few-shot Prompting.
* Chain of Thought.
* RAG.
* Agentes especializados.

Sin modificar la lógica de negocio.

---

# 10. Ejemplo de Organización

```text
app/

prompts/

email_prompt.py

proposal_prompt.py

followup_prompt.py

whatsapp_prompt.py

summary_prompt.py

base_prompt.py
```

Cada módulo tendrá una única responsabilidad.

---

# 11. Relación con otras decisiones

Este ADR complementa:

* ADR-001 — Adopción de Clean Architecture.
* ADR-004 — Adopción del Repository Pattern.
* ADR-005 — Adopción de Service Layer.

Los Services coordinarán la generación, mientras que el Prompt Engine será responsable exclusivamente de construir las instrucciones enviadas al modelo de IA.

---

# 12. Especificaciones relacionadas

Este ADR está relacionado con:

* SPEC-04 — Casos de Uso.
* SPEC-08 — Arquitectura del Software.
* SPEC-09 — Estructura de Carpetas.
* SPEC-10 — Roadmap.

---

# 13. Referencias

* OpenAI Prompt Engineering Guide.
* Anthropic Prompt Engineering Best Practices.
* LangChain Documentation.
* Microsoft AI Engineering Documentation.

---

# 14. Conclusión

Se adopta una estrategia de **Prompt Engineering desacoplada** del resto del código mediante un Prompt Engine organizado en módulos independientes.

Esta decisión mejora la mantenibilidad, facilita la experimentación con distintas estrategias de generación y prepara la aplicación para evolucionar hacia sistemas más avanzados como RAG, Prompt Chaining y arquitecturas Multi-Agent.

El Prompt Engineering pasa a considerarse un componente funcional de la arquitectura y no simplemente un conjunto de cadenas de texto embebidas en el código.
