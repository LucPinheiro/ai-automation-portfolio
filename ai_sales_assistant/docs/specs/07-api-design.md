# 07. API Design

## Conventions

| Aspect | Convention |
| ------ | ---------- |
| Base URL (local) | `http://127.0.0.1:8000` |
| Versioning | Business endpoints live under `/api/v1`; `/` and `/health` are unversioned |
| Format | JSON (UTF-8). Dates are ISO 8601 in UTC. |
| Documentation | Swagger UI at `/docs`, ReDoc at `/redoc`, schema at `/openapi.json` |
| Authentication | None in Version 1 (planned for Version 2) |

## Endpoints

| Method | Path | Success | Errors |
| ------ | ---- | ------- | ------ |
| GET | `/` | 200 `RootResponse` | 500 |
| GET | `/health` | 200 `HealthResponse` | 503 `HealthResponse`, 500 |
| POST | `/api/v1/auth/register` | 201 `UserRead` + session cookie | 400, 403, 409, 422, 500 |
| POST | `/api/v1/auth/login` | 200 `UserRead` + session cookie | 400, 401, 403, 422, 500 |
| POST | `/api/v1/auth/logout` | 204 | 401, 403, 500 |
| GET | `/api/v1/auth/me` | 200 `UserRead` | 401, 500 |
| POST | `/api/v1/auth/change-password` | 204 + new session cookie | 400, 401, 403, 422, 500 |
| POST | `/api/v1/auth/guest` | 201 `UserRead` (`is_guest: true`) + session cookie | 403, 500 |
| POST | `/api/v1/auth/forgot-password` | 202 `MessageResponse` | 400, 403, 422, 500 |
| POST | `/api/v1/auth/reset-password` | 204 | 400, 403, 422, 500 |
| POST | `/api/v1/generate` | 201 `GenerationRead` | 400, 401, 403, 422, 500, 502, 503 |
| GET | `/api/v1/generations` | 200 `GenerationList` | 401, 422, 500 |
| GET | `/api/v1/generations/{generation_id}` | 200 `GenerationRead` | 401, 404, 422, 500 |
| PUT | `/api/v1/generations/{generation_id}` | 200 `GenerationRead` | 400, 401, 403, 404, 422, 500, 502, 503 |
| GET | `/api/v1/pricing/discount?price=&discount_percent=` | 200 `PricingRead` | 401, 422, 500 |
| DELETE | `/api/v1/generations/{generation_id}` | 204 (no body) | 401, 403, 404, 422, 500 |

### Authentication

Authentication uses a server-side session identified by the HttpOnly cookie `ai_sales_session` (`SameSite=Lax`, `Secure` in production); see [ADR 0013](../adr/0013-authentication.md). Generation endpoints require it (401 `not_authenticated` otherwise) and are scoped to the current user: another user's generation returns 404. State-changing requests from another origin are rejected with 403 `csrf_failed`. Login failures always return 401 `invalid_credentials`; `forgot-password` always returns 202; invalid, used or expired reset tokens return 400 `invalid_or_expired_token`; a taken email on registration returns 409 `email_already_registered` (409 `username_already_taken` for a taken username). Login accepts `identifier` (username or email).

`GenerationRead.missing_commercial_terms` lists mandatory commercial terms (structured pricing and figure-bearing lines of the customer needs) that the generated text does not contain, after one automatic retry ([ADR 0016](../adr/0016-mandatory-commercial-terms.md)). With `COMMERCIAL_TERMS_STRICT=true` such a text is rejected with 502 `commercial_terms_missing`.

Guests ([ADR 0014](../adr/0014-guest-mode.md)) use the same endpoints for their own generations, limited to `GUEST_MAX_GENERATIONS` AI calls (403 `guest_quota_exceeded`); account endpoints answer 403 `guest_not_allowed`. Logging out deletes the guest and its generations.

### POST /api/v1/generate

Request (`GenerationCreate`). All fields are required, and unknown fields are rejected:

```json
{
  "content_type": "commercial_email",
  "customer": "María López",
  "company": "Logística Norte S.L.",
  "industry": "Logistics",
  "product_or_service": "Fleet management software",
  "customer_needs": "Reduce fuel costs and track deliveries in real time.",
  "language": "es",
  "tone": "professional"
}
```

| Field | Rules |
| ----- | ----- |
| `content_type` | `commercial_email` · `sales_proposal` · `follow_up` · `whatsapp` · `customer_summary` |
| `customer`, `company` | 1–150 characters after trimming |
| `industry` | 1–100 characters |
| `product_or_service` | 1–200 characters |
| `customer_needs` | 1–2000 characters |
| `price` | Optional. > 0, at most 2 decimals, up to 99,999,999.99 (EUR) |
| `discount_percent` | Optional. 0–100, at most 2 decimals (15 means 15 %). Requires `price` (422 `discount_requires_price`) |
| `customer_email` | Optional valid email (up to 254 characters); empty means not provided. Stored and returned, never included in the prompt |
| `salesperson`, `salesperson_company` | Optional, up to 150 characters; empty means not provided (no name is invented) |
| `language` | `es` · `en` · `pt` · `fr` |
| `tone` | `professional` · `formal` · `friendly` · `persuasive` · `concise` |

Response `201` (`GenerationRead`):

```json
{
  "id": 1,
  "content_type": "commercial_email",
  "generated_content": "Subject: ...",
  "language": "es",
  "tone": "professional",
  "customer": "María López",
  "company": "Logística Norte S.L.",
  "industry": "Logistics",
  "product_or_service": "Fleet management software",
  "customer_needs": "Reduce fuel costs and track deliveries in real time.",
  "ai_provider": "openai",
  "ai_model": "gpt-4o-mini-2024-07-18",
  "created_at": "2026-10-07T12:00:00Z"
}
```

Prompts and token usage are never returned.

### GET /api/v1/generations

| Query parameter | Type | Default | Rules |
| --------------- | ---- | ------- | ----- |
| `limit` | int | 20 | 1–100 |
| `offset` | int | 0 | ≥ 0 |
| `content_type` | ContentType | none | optional filter |

Response:

```json
{"items": [ /* GenerationRead */ ], "total": 1, "limit": 20, "offset": 0}
```

Items are ordered newest first.

### GET /api/v1/generations/{generation_id}

`generation_id` must be an integer ≥ 1. Returns `GenerationRead`, or 404 if the generation does not exist.

### PUT /api/v1/generations/{generation_id}

Regenerates an existing generation from new input and updates **the same record** (same `id` and `created_at`). The body is a `GenerationCreate`, validated exactly like `POST /generate`; `generated_content` is rejected (422) because the content always comes from the AI provider. An unknown id returns 404 without calling the AI. If the provider fails (502/503), the stored record is left unchanged.

### DELETE /api/v1/generations/{generation_id}

Permanently deletes a generation. Returns 204 with no body, or 404 when the id does not exist. It does not need the AI provider.

### GET /health

```json
{"status": "ok", "version": "0.1.0", "database": "ok"}
```

If the database is unreachable it returns 503 with `"status": "degraded", "database": "unavailable"`.

## Error format

Every error except `/health` uses:

```json
{"error": {"code": "<machine code>", "message": "<safe human message>", "details": [{"field": "...", "message": "...", "type": "..."}]}}
```

| HTTP | `code` | When |
| ---- | ------ | ---- |
| 400 | `invalid_json` | Body is not valid JSON |
| 404 | `not_found` | Unknown generation or route |
| 405 | `method_not_allowed` | Wrong HTTP method |
| 422 | `validation_error` | Invalid or missing fields; `details` lists them (input is not echoed) |
| 500 | `internal_error` | Unexpected error (logged, never detailed) |
| 502 | `ai_provider_error` | AI provider failed |
| 503 | `ai_provider_not_configured` | `OPENAI_API_KEY` missing (`AI_PROVIDER=openai`) |

## Example (curl)

```bash
curl -X POST http://127.0.0.1:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"content_type":"whatsapp","customer":"Ana Ruiz","company":"Retail Sur","industry":"Retail","product_or_service":"Loyalty app","customer_needs":"Increase repeat purchases","language":"es","tone":"friendly"}'
```
