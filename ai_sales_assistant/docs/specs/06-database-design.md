# 06. Database Design

- **Engine:** SQLite in Version 1, configured with `DATABASE_URL` (default `sqlite:///./ai_sales_assistant.db`). PostgreSQL is planned for Version 2.
- **Migrations:** Alembic, `alembic/versions/`. Current head is `0001`.

## Table `generations`

| Column | Type | Null | Constraints / index |
| ------ | ---- | ---- | ------------------- |
| `id` | INTEGER | no | `pk_generations` |
| `content_type` | VARCHAR(32) | no | `ix_generations_content_type` |
| `customer` | VARCHAR(150) | no | |
| `company` | VARCHAR(150) | no | |
| `industry` | VARCHAR(100) | no | |
| `product_or_service` | VARCHAR(200) | no | |
| `customer_needs` | TEXT | no | Max 2000 characters, validated by the API |
| `language` | VARCHAR(8) | no | |
| `tone` | VARCHAR(32) | no | |
| `generated_content` | TEXT | no | |
| `ai_provider` | VARCHAR(32) | no | |
| `ai_model` | VARCHAR(64) | no | |
| `prompt_tokens` | INTEGER | yes | |
| `completion_tokens` | INTEGER | yes | |
| `created_at` | DATETIME (timezone) | no | `ix_generations_created_at` |

Alembic also maintains its own `alembic_version` table.

## Design rules

- **Enums are stored as their string values** (e.g. `commercial_email`), with no native enum and no `CHECK` constraint. New values need no migration, and SQLite and PostgreSQL behave the same.
- **Timestamps are UTC.** The `UTCDateTime` type rejects naive values and always returns aware UTC datetimes, compensating for SQLite dropping the offset.
- **Indexes match the queries:** filter by `content_type`, order by `created_at`.
- **Constraint names follow a naming convention** (`pk_%(table_name)s`, `ix_%(column_0_label)s`, …) for portable migrations.
- **Length limits are defined once** in `app/core/constants.py` and shared by the columns and the API schemas.

## Migrations

| Revision | Description |
| -------- | ----------- |
| `0001` | Create `generations` table and its indexes |

Commands:

```bash
alembic upgrade head          # apply all migrations
alembic current               # show current revision
alembic downgrade -1          # revert the last migration
alembic revision --autogenerate -m "describe change" --rev-id 0002   # new migration
```

`tests/test_migrations.py` verifies that `upgrade head` produces exactly the schema defined by the models and that `downgrade base` removes it.
