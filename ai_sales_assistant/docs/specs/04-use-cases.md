# 04. Use Cases

Actor: **Sales user**, through the API client. A web UI is planned.

## UC-01 Generate commercial content

- **Trigger:** `POST /api/v1/generate`
- **Preconditions:** the selected AI provider is available: `OPENAI_API_KEY` is configured (`AI_PROVIDER=openai`), or Ollama is running with `OLLAMA_MODEL` installed (`AI_PROVIDER=ollama`).

**Main flow:**

1. The user sends content type, customer, company, industry, product or service, customer needs, language and tone.
2. The system validates and trims the input.
3. The system builds the prompt: the shared rules, the instructions for that content type, and the delimited customer data.
4. The system sends the prompt to the configured AI provider.
5. The system stores the generation: input, content, provider, model and tokens.
6. The system returns the stored generation with status **201**.

**Alternative flows:**

| Case | Response | Stored? |
| ---- | -------- | ------- |
| 2a. Malformed JSON | 400 `invalid_json` | no |
| 2b. Invalid or missing data | 422 `validation_error` with the failing fields; the provider is not called | no |
| 4a. Provider not configured | 503 `ai_provider_not_configured` | no |
| 4b. Provider fails (timeout, rate limit, credentials, Ollama unreachable or model missing, empty answer) | 502 `ai_provider_error` | no |
| 5a. Database error | 500 `internal_error`; the transaction is rolled back | no |

## UC-02 Browse generation history

- **Trigger:** `GET /api/v1/generations?limit=&offset=&content_type=`

**Main flow:**

1. The system returns the requested page, newest first.
2. The response includes `total`, `limit` and `offset`.

**Alternative flows:**

- 1a. Invalid `limit` (outside 1–100), negative `offset` or unknown `content_type` → 422.

**Notes:** works even when the AI provider is not configured.

## UC-03 View a generation

- **Trigger:** `GET /api/v1/generations/{id}`

**Main flow:**

1. The system returns the generation.

**Alternative flows:**

- 1a. Unknown id → 404 `not_found`.
- 1b. Id that is not a positive integer → 422.

## UC-04 Check service health

- **Trigger:** `GET /health`

**Main flow:**

1. The system checks database connectivity.
2. The system returns `status: ok` with 200.

**Alternative flows:**

- 1a. Database unreachable → 503 with `status: degraded`, `database: unavailable`.
