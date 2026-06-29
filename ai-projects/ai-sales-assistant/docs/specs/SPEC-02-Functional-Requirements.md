# SPEC-02 — Functional Requirements

**Proyecto:** AI Sales Assistant – Intelligent Commercial Assistant

**Versión:** 1.0

**Estado:** Draft

**Autor:** Luciana Pinheiro

**Metodología:** Spec-Driven Development (SDD)

---

# 1. Objetivo

Este documento define los requisitos funcionales de la aplicación AI Sales Assistant.

Describe el comportamiento esperado del sistema desde el punto de vista del usuario, sin entrar en detalles de implementación técnica.

---

# 2. Actores

## Actor principal

**Usuario Comercial**

Persona que utiliza la aplicación para generar contenido comercial mediante Inteligencia Artificial.

---

## Actores secundarios

* Servicio de Inteligencia Artificial
* Base de Datos
* API REST

---

# 3. Funcionalidades

## FR-001 — Generar documento

El sistema deberá permitir generar contenido mediante IA a partir de la información introducida por el usuario.

Tipos soportados:

* Email Comercial
* Propuesta Comercial
* Mensaje de Seguimiento
* Mensaje para WhatsApp
* Resumen del Cliente

---

## FR-002 — Introducir información del cliente

El usuario podrá introducir:

* Nombre del cliente
* Empresa
* Sector
* Producto o servicio
* Necesidad del cliente
* Idioma
* Tono

---

## FR-003 — Mostrar resultado

Tras pulsar el botón **Generate**, el sistema mostrará el texto generado por la IA.

---

## FR-004 — Guardar historial

Cada generación deberá almacenarse automáticamente en la base de datos.

---

## FR-005 — Consultar historial

El usuario podrá consultar todas las generaciones realizadas anteriormente.

---

## FR-006 — Consultar una generación

El usuario podrá visualizar una generación concreta mediante su identificador.

---

## FR-007 — Eliminar una generación

El usuario podrá eliminar un registro del historial.

---

## FR-008 — Copiar resultado

El usuario podrá copiar el texto generado al portapapeles.

---

## FR-009 — Descargar resultado

El usuario podrá descargar el contenido generado como archivo `.txt`.

---

## FR-010 — Limpiar formulario

El usuario podrá limpiar todos los campos del formulario mediante un botón **Clear**.

---

# 4. Datos de entrada

| Campo               | Obligatorio |
| ------------------- | ----------- |
| Cliente             | Sí          |
| Empresa             | Sí          |
| Sector              | Sí          |
| Producto o Servicio | Sí          |
| Necesidad           | Sí          |
| Idioma              | Sí          |
| Tono                | Sí          |
| Tipo de Documento   | Sí          |

---

# 5. Tipos de documento

La aplicación soportará inicialmente:

* Email Comercial
* Propuesta Comercial
* Seguimiento Comercial
* WhatsApp
* Resumen del Cliente

---

# 6. Idiomas soportados

Versión inicial:

* Español
* Inglés
* Portugués

---

# 7. Tonos soportados

* Profesional
* Formal
* Cercano
* Persuasivo
* Amigable

---

# 8. Validaciones

## VR-001

Todos los campos obligatorios deberán estar informados.

---

## VR-002

El idioma deberá pertenecer a la lista de idiomas soportados.

---

## VR-003

El tono deberá pertenecer a la lista de tonos soportados.

---

## VR-004

El tipo de documento deberá ser válido.

---

## VR-005

No se permitirá generar documentos vacíos.

---

# 9. Reglas de negocio

## BR-001

Cada generación deberá almacenarse automáticamente.

---

## BR-002

Cada generación tendrá un identificador único.

---

## BR-003

La fecha de generación será asignada automáticamente por el sistema.

---

## BR-004

El historial podrá eliminarse individualmente.

---

## BR-005

La respuesta generada se almacenará íntegramente.

---

# 10. Gestión de errores

El sistema deberá gestionar al menos los siguientes casos:

* Campos obligatorios vacíos.
* Idioma no soportado.
* Tono inválido.
* Error de conexión con el proveedor de IA.
* Error de almacenamiento en base de datos.
* Error interno inesperado.

En todos los casos se mostrará un mensaje claro al usuario y el error se registrará mediante el sistema de logging.

---

# 11. Flujo funcional

1. El usuario completa el formulario.
2. Selecciona el tipo de documento.
3. Pulsa **Generate**.
4. El sistema valida los datos.
5. Se construye el prompt correspondiente.
6. Se envía la solicitud al modelo de IA.
7. Se recibe la respuesta.
8. Se guarda el resultado en la base de datos.
9. Se muestra el contenido generado al usuario.

---

# 12. Criterios de aceptación

## CA-001

**Dado** un formulario correctamente cumplimentado

**Cuando** el usuario pulse **Generate**

**Entonces** el sistema generará el documento solicitado.

---

## CA-002

**Dado** un documento generado

**Cuando** finalice el proceso

**Entonces** deberá almacenarse automáticamente en el historial.

---

## CA-003

**Dado** un registro existente

**Cuando** el usuario solicite eliminarlo

**Entonces** el sistema lo eliminará correctamente.

---

## CA-004

**Dado** un formulario con errores

**Cuando** el usuario pulse **Generate**

**Entonces** el sistema mostrará los mensajes de validación correspondientes.

---

# 13. Exclusiones de la versión 1

La primera versión no incluirá:

* Gestión de usuarios.
* Autenticación.
* Autorización.
* Panel de administración.
* Exportación PDF.
* Exportación Word.
* Integración con Odoo.
* Integración con CRM externos.
* RAG.
* Multi-Agent Systems.
* Redis.
* PostgreSQL.

Estas funcionalidades se desarrollarán en versiones posteriores del proyecto.
