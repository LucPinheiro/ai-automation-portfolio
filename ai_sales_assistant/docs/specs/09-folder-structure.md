# 09. Folder Structure

```text
ai-sales-assistant/
├── app/
│   ├── main.py                     # create_app(): settings, logging, handlers, routers
│   ├── api/
│   │   ├── v1.py                   # /api/v1 router
│   │   ├── dependencies.py         # DI: session, cached AI provider, GenerationService
│   │   └── responses.py            # OpenAPI error responses with examples
│   ├── routers/
│   │   ├── system.py               # GET /, GET /health
│   │   └── generations.py          # POST /generate, GET /generations, GET /generations/{id}
│   ├── services/
│   │   ├── generation_service.py   # generation use cases
│   │   ├── health_service.py       # health check
│   │   └── ai/
│   │       ├── base.py             # AIProvider protocol, AIResult
│   │       ├── openai_provider.py  # OpenAI Responses API adapter
│   │       ├── ollama_provider.py  # Ollama /api/chat adapter (local models)
│   │       └── factory.py          # create_ai_provider(settings)
│   ├── repositories/
│   │   └── generation_repository.py
│   ├── prompts/
│   │   ├── base.py                 # Prompt, PromptTemplate, system prompt, language/tone guidance
│   │   ├── builder.py              # build_prompt()
│   │   ├── registry.py             # ContentType → PromptTemplate
│   │   └── commercial_email.py, sales_proposal.py, follow_up.py, whatsapp.py, customer_summary.py
│   ├── models/
│   │   └── generation.py           # Generation ORM model
│   ├── schemas/
│   │   ├── generation.py           # GenerationCreate, GenerationRead, GenerationList
│   │   ├── system.py               # RootResponse, HealthResponse
│   │   └── errors.py               # ErrorResponse
│   ├── database/
│   │   ├── base.py                 # DeclarativeBase + naming convention
│   │   ├── session.py              # engine, SessionLocal, get_db
│   │   └── types.py                # UTCDateTime
│   ├── config/
│   │   └── settings.py             # Settings (pydantic-settings)
│   ├── core/
│   │   ├── enums.py                # ContentType, Language, Tone
│   │   ├── constants.py            # length limits, pagination
│   │   ├── exceptions.py           # AppError hierarchy
│   │   ├── error_handlers.py       # global exception handlers
│   │   └── logging.py
│   ├── templates/                  # reserved for the Jinja2 UI (empty)
│   ├── static/                     # reserved for UI assets (empty)
│   └── utils/                      # reserved (empty)
├── alembic/
│   ├── env.py                      # URL from settings, batch mode for SQLite
│   └── versions/0001_create_generations_table.py
├── alembic.ini
├── docs/
│   ├── specs/                      # these specifications
│   ├── adr/                        # architecture decision records
│   ├── diagrams/                   # reserved
│   └── images/                     # reserved
├── tests/                          # pytest suite (fakes, factories, unit and API tests)
├── docker/                         # reserved for Version 2
├── .env.example                    # configuration template (no secrets)
├── requirements.txt                # runtime dependencies
├── requirements-dev.txt            # + pytest, httpx2
├── pytest.ini
├── README.md
├── LICENSE
└── .gitignore
```

## Differences from the original README structure

- **`alembic/` and `alembic.ini`** were added. Alembic requires them, and keeping them at the project root is the standard layout.
- **`app/api/` vs `app/routers/`:** the endpoint modules live in `routers/`. `api/` assembles them under the API version and holds the dependency wiring.
- **Empty reserved folders** (`templates`, `static`, `utils`, `diagrams`, `images`, `docker`) contain a `.gitkeep` so Git keeps them.
