from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

from app.database import Base

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# A generation as stored before user accounts existed (revision 0001).
LEGACY_GENERATION = text(
    "INSERT INTO generations (content_type, customer, company, industry, product_or_service, "
    "customer_needs, language, tone, generated_content, ai_provider, ai_model, created_at) "
    "VALUES ('whatsapp', 'Legacy', 'ACME', 'Retail', 'CRM', 'Needs', 'es', 'formal', "
    "'Old content', 'ollama', 'llama3.2:3b', '2026-10-01 10:00:00+00:00')"
)


@pytest.fixture
def alembic_config(tmp_path: Path) -> Config:
    # Built without alembic.ini so the test run's logging setup is left untouched.
    config = Config()
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{tmp_path / 'migrations.db'}")
    return config


def test_upgrade_creates_schema_matching_the_models(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")

    engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        differences = compare_metadata(context, Base.metadata)
    engine.dispose()

    assert differences == []


def test_downgrade_removes_schema(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "base")

    engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    assert "generations" not in inspect(engine).get_table_names()
    engine.dispose()


def test_upgrade_keeps_existing_generations_without_owner(alembic_config: Config) -> None:
    # A database created before user accounts existed, with one generation in it.
    command.upgrade(alembic_config, "0001")
    engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        connection.execute(LEGACY_GENERATION)

    command.upgrade(alembic_config, "head")

    with engine.connect() as connection:
        rows = connection.execute(text("SELECT customer, generated_content, user_id FROM generations")).all()
        tables = set(inspect(connection).get_table_names())
    engine.dispose()
    assert rows == [("Legacy", "Old content", None)]
    assert {"users", "user_sessions", "password_reset_tokens"} <= tables


def test_downgrade_to_0001_keeps_generations(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "0001")
    engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        connection.execute(LEGACY_GENERATION)
    command.upgrade(alembic_config, "head")

    command.downgrade(alembic_config, "0001")

    with engine.connect() as connection:
        rows = connection.execute(text("SELECT customer FROM generations")).all()
        tables = set(inspect(connection).get_table_names())
    engine.dispose()
    assert rows == [("Legacy",)]
    assert "users" not in tables


def test_0003_keeps_existing_accounts_as_registered_users(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "0002")
    engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (name, email, password_hash, created_at, password_changed_at) "
                "VALUES ('María', 'maria@example.com', '$argon2id$hash', '2026-10-07 10:00:00+00:00', "
                "'2026-10-07 10:00:00+00:00')"
            )
        )

    command.upgrade(alembic_config, "head")

    with engine.connect() as connection:
        user = connection.execute(text("SELECT email, username, is_guest, ai_generation_count FROM users")).one()
    engine.dispose()
    assert tuple(user) == ("maria@example.com", None, 0, 0)


def test_0003_downgrade_removes_only_guests(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")
    engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (id, name, email, password_hash, is_guest, created_at, password_changed_at) VALUES "
                "(1, 'María', 'maria@example.com', '$argon2id$hash', 0, '2026-10-07 10:00:00+00:00', '2026-10-07 10:00:00+00:00'), "
                "(2, 'Invitado', NULL, NULL, 1, '2026-10-07 10:00:00+00:00', '2026-10-07 10:00:00+00:00')"
            )
        )
        connection.execute(LEGACY_GENERATION)
        connection.execute(text("UPDATE generations SET user_id = 2"))

    command.downgrade(alembic_config, "0002")

    with engine.connect() as connection:
        users = connection.execute(text("SELECT email FROM users")).all()
        generations = connection.execute(text("SELECT count(*) FROM generations")).scalar()
    engine.dispose()
    assert users == [("maria@example.com",)]
    assert generations == 0  # the guest's temporary data goes with it


def test_0004_keeps_existing_generations_with_an_empty_salesperson(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "0003")
    engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        connection.execute(LEGACY_GENERATION)

    command.upgrade(alembic_config, "head")

    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT customer, generated_content, salesperson, salesperson_company FROM generations")
        ).one()
    engine.dispose()
    assert tuple(row) == ("Legacy", "Old content", None, None)


def test_0004_downgrade_keeps_the_generations(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")
    engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        connection.execute(LEGACY_GENERATION)
        connection.execute(text("UPDATE generations SET salesperson = 'Carlos Vila'"))

    command.downgrade(alembic_config, "0003")

    with engine.connect() as connection:
        rows = connection.execute(text("SELECT customer FROM generations")).all()
        columns = {column["name"] for column in inspect(connection).get_columns("generations")}
    engine.dispose()
    assert rows == [("Legacy",)]
    assert "salesperson" not in columns


def test_0005_keeps_existing_generations_without_price(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "0004")
    engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        connection.execute(LEGACY_GENERATION)

    command.upgrade(alembic_config, "head")

    with engine.connect() as connection:
        row = connection.execute(text("SELECT customer, price_cents, discount_basis_points FROM generations")).one()
    engine.dispose()
    assert tuple(row) == ("Legacy", None, None)


@pytest.mark.parametrize(
    "assignment",
    ["price_cents = -100", "price_cents = 0", "price_cents = 1000, discount_basis_points = 10001",
     "discount_basis_points = 1500"],
)
def test_0005_database_rejects_invalid_pricing(alembic_config: Config, assignment: str) -> None:
    from sqlalchemy.exc import IntegrityError

    command.upgrade(alembic_config, "head")
    engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        connection.execute(LEGACY_GENERATION)
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text(f"UPDATE generations SET {assignment}"))
    engine.dispose()


def test_0006_keeps_existing_generations_with_an_empty_customer_email(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "0005")
    engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        connection.execute(LEGACY_GENERATION)

    command.upgrade(alembic_config, "head")

    with engine.connect() as connection:
        row = connection.execute(text("SELECT customer, customer_email FROM generations")).one()
    engine.dispose()
    assert tuple(row) == ("Legacy", None)


def test_0006_downgrade_keeps_the_generations(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")
    engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        connection.execute(LEGACY_GENERATION)
        connection.execute(text("UPDATE generations SET customer_email = 'legacy@example.com'"))

    command.downgrade(alembic_config, "0005")

    with engine.connect() as connection:
        columns = {c["name"] for c in inspect(connection).get_columns("generations")}
        customer = connection.execute(text("SELECT customer FROM generations")).scalar_one()
    engine.dispose()
    assert "customer_email" not in columns
    assert customer == "Legacy"
