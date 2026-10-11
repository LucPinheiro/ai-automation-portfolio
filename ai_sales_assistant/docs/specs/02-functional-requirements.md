# 02. Functional Requirements

Status: ✅ implemented in Version 1 · ⏳ planned

## Content generation

| ID | Requirement | Status |
| -- | ----------- | ------ |
| FR-01 | The system generates content of type `commercial_email`, `sales_proposal`, `follow_up`, `whatsapp` or `customer_summary`. | ✅ |
| FR-02 | Generation uses: customer, company, industry, product or service, customer needs, language and tone. All are required. | ✅ |
| FR-03 | Supported languages: Spanish (`es`), English (`en`), Portuguese (`pt`), French (`fr`). | ✅ |
| FR-04 | Supported tones: `professional`, `formal`, `friendly`, `persuasive`, `concise`. | ✅ |
| FR-05 | Each content type has its own instructions and output format (e.g. a WhatsApp message of at most 600 characters, a proposal with fixed sections). | ✅ |
| FR-06 | Generated content must not invent figures (percentages, quantities, prices, dates, durations, statistics, metrics) or commitments; missing details are omitted naturally and no placeholders are produced, including in the sign-off. | ✅ (enforced via prompt) |
| FR-07 | The response returns the generated content together with its id, type, language, tone, input data, model and creation date. | ✅ |

## History

| ID | Requirement | Status |
| -- | ----------- | ------ |
| FR-08 | Every successful generation is stored with its input, output, provider, model and token usage. | ✅ |
| FR-09 | Failed generations are not stored. | ✅ |
| FR-10 | Users can list generations, newest first, with pagination (`limit` 1–100, default 20; `offset`). | ✅ |
| FR-11 | Users can filter the list by content type. | ✅ |
| FR-12 | Users can retrieve a generation by id; an unknown id returns 404. | ✅ |

## Validation

| ID | Requirement | Status |
| -- | ----------- | ------ |
| FR-13 | Text fields are trimmed; empty or whitespace-only values are rejected. | ✅ |
| FR-14 | Length limits: customer 150, company 150, industry 100, product or service 200, customer needs 2000 characters. | ✅ |
| FR-15 | Unknown content types, languages, tones and unexpected fields are rejected. | ✅ |

## Operations

| ID | Requirement | Status |
| -- | ----------- | ------ |
| FR-16 | `GET /` returns application name, version and documentation links. | ✅ |
| FR-17 | `GET /health` reports application and database status. | ✅ |
| FR-18 | Interactive API documentation is available at `/docs` (Swagger UI) and `/redoc`. | ✅ |

## Planned (not implemented)

| ID | Requirement | Version |
| -- | ----------- | ------- |
| FR-19 | Bootstrap web interface to fill in the form and view the history | 1 (pending) |
| FR-20 | User authentication and user management | 2 |
| FR-21 | Customer management (reusable customer records) | 3 |
| FR-22 | PDF and Word export | 3 |
| FR-23 | Dashboard | 3 |
| FR-24 | RAG over company knowledge, local models (Hugging Face), embeddings. Ollama is already supported as a local AI provider | 4 |
| FR-25 | Odoo CRM integration, MCP, AI agents | 5 |
