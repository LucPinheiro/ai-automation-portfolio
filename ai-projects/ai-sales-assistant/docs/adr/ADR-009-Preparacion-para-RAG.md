# ADR-009 — Preparación de la Arquitectura para RAG

**Estado:** Aceptado

**Fecha:** 26/06/2026

**Proyecto:** AI Sales Assistant – Intelligent Commercial Assistant

**Autor:** Luciana Pinheiro

---

# 1. Contexto

El AI Sales Assistant nace como una aplicación capaz de generar contenido comercial utilizando modelos de lenguaje (LLMs).

En la primera versión, los documentos se generarán únicamente a partir de la información proporcionada por el usuario.

Sin embargo, la visión a medio plazo del proyecto contempla incorporar capacidades avanzadas de Inteligencia Artificial, como la consulta de documentación propia de la empresa, manuales, catálogos de productos o políticas comerciales.

Para ello será necesario incorporar una arquitectura basada en **Retrieval-Augmented Generation (RAG)**.

---

# 2. Problema

Los modelos de lenguaje poseen un conocimiento general, pero no conocen la información específica de cada empresa.

Si la aplicación necesitara responder utilizando:

* documentación interna;
* fichas de productos;
* políticas comerciales;
* contratos;
* procedimientos;
* bases de conocimiento;

sería necesario proporcionar ese contexto durante la generación.

No resulta adecuado rediseñar completamente la arquitectura cuando llegue ese momento.

---

# 3. Alternativas consideradas

## Opción 1 — Incorporar RAG únicamente cuando sea necesario

### Ventajas

* Menor complejidad inicial.
* Desarrollo más rápido del MVP.

### Inconvenientes

* Posible necesidad de rediseñar la arquitectura.
* Mayor esfuerzo de refactorización.
* Riesgo de introducir dependencias innecesarias.

**Decisión:** Rechazada.

---

## Opción 2 — Preparar la arquitectura desde la versión 1

### Ventajas

* Arquitectura preparada para crecer.
* Menor coste de evolución.
* Separación clara de responsabilidades.
* Integración sencilla con futuras tecnologías.

**Decisión:** Aceptada.

---

# 4. Decisión

La versión 1 **no implementará un sistema RAG**, pero toda la arquitectura quedará preparada para incorporarlo sin modificar la lógica principal del sistema.

El Prompt Engine y la Service Layer se diseñarán pensando en que, en el futuro, puedan recibir contexto adicional procedente de una base de conocimiento.

---

# 5. Arquitectura futura

```mermaid
flowchart TD

Usuario

↓

Router

↓

Service Layer

↓

Prompt Engine

↓

RAG Service

↓

Base de Conocimiento

↓

Prompt Final

↓

Proveedor IA

↓

Respuesta
```

La incorporación del RAG se realizará mediante nuevos componentes sin alterar los ya existentes.

---

# 6. Componentes previstos

En futuras versiones se añadirán nuevos módulos:

```text
app/

rag/

retriever.py

embeddings.py

vector_store.py

knowledge_base.py

chunking.py

ranking.py
```

Estos componentes serán independientes del resto de la aplicación.

---

# 7. Beneficios

Preparar la arquitectura desde el inicio proporciona:

* Menor deuda técnica.
* Evolución progresiva.
* Mayor flexibilidad.
* Integración sencilla con nuevas tecnologías.
* Mejor escalabilidad.

---

# 8. Consecuencias

## Positivas

* Arquitectura preparada para IA avanzada.
* Menor esfuerzo de evolución.
* Reutilización de componentes existentes.
* Menor impacto sobre el código ya desarrollado.

## Negativas

* Ligero incremento del diseño inicial.
* Necesidad de planificar futuras extensiones.

Estas desventajas son reducidas frente a las ventajas obtenidas.

---

# 9. Evolución prevista

Las futuras versiones podrán incorporar:

### Bases vectoriales

* ChromaDB
* Qdrant
* Pinecone
* Weaviate

---

### Embeddings

* OpenAI Embeddings
* Sentence Transformers
* BAAI BGE
* Nomic Embeddings

---

### Recuperación de contexto

* Similarity Search.
* Hybrid Search.
* Metadata Filtering.
* Re-ranking.

---

### Modelos de IA

* OpenAI
* Ollama
* Hugging Face
* Anthropic
* Gemini

---

# 10. Relación con otras decisiones

Este ADR complementa:

* ADR-001 — Adopción de Clean Architecture.
* ADR-005 — Adopción de Service Layer.
* ADR-006 — Separación del Prompt Engineering.

La separación de responsabilidades facilitará la incorporación del RAG sin modificar la lógica existente.

---

# 11. Especificaciones relacionadas

Este ADR está relacionado con:

* SPEC-08 — Arquitectura del Software.
* SPEC-09 — Estructura de Carpetas.
* SPEC-10 — Roadmap.

---

# 12. Referencias

* Lewis et al. — *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*.
* LangChain Documentation.
* LlamaIndex Documentation.
* Chroma Documentation.
* Pinecone Documentation.
* OpenAI Embeddings Guide.

---

# 13. Conclusión

Aunque la versión 1 del AI Sales Assistant no implementará Retrieval-Augmented Generation, la arquitectura se diseña desde el inicio para soportarlo.

Esta decisión permitirá evolucionar el proyecto hacia una plataforma de IA empresarial capaz de utilizar conocimiento específico de una organización sin modificar la lógica de negocio existente.

La incorporación futura de RAG se realizará mediante nuevos componentes especializados, manteniendo la modularidad y la mantenibilidad definidas por la Clean Architecture adoptada en el proyecto.
