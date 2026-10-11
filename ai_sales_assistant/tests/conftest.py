from collections.abc import Iterator

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (registers ORM models on Base.metadata)
from app.api.dependencies import get_ai_provider_resolver, get_email_sender
from app.config import Settings, get_settings
from app.core import security
from app.database import Base, get_db
from app.main import app
from tests.factories import register
from tests.fakes import FakeAIProvider, FakeEmailSender


@pytest.fixture(autouse=True)
def fast_password_hashing(monkeypatch: pytest.MonkeyPatch) -> None:
    # Real Argon2id with the minimum cost: the suite stays fast without mocking the hashing.
    monkeypatch.setattr(security, "_hasher", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1))


@pytest.fixture
def engine() -> Iterator[Engine]:
    # Shared in-memory database for the duration of one test.
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    yield session
    session.close()


@pytest.fixture
def test_settings() -> Settings:
    # Independent of the developer's .env: plain-http cookies and the console email backend.
    return Settings(_env_file=None, environment="testing", email_backend="console")  # type: ignore[call-arg]


@pytest.fixture
def fake_ai_provider() -> FakeAIProvider:
    return FakeAIProvider()


@pytest.fixture
def fake_email_sender() -> FakeEmailSender:
    return FakeEmailSender()


@pytest.fixture
def anon_client(
    db_session: Session,
    fake_ai_provider: FakeAIProvider,
    fake_email_sender: FakeEmailSender,
    test_settings: Settings,
) -> Iterator[TestClient]:
    """A client without a session. The real AI provider and email sender are always replaced."""
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_ai_provider_resolver] = lambda: lambda: fake_ai_provider
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_email_sender] = lambda: fake_email_sender
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def client(anon_client: TestClient) -> TestClient:
    """Logged in as María (maria@example.com) through the real register endpoint."""
    register(anon_client)
    return anon_client


@pytest.fixture
def other_client(anon_client: TestClient) -> Iterator[TestClient]:
    """A second browser (own cookie jar) logged in as Ana, sharing the app and database."""
    with TestClient(app) as second:
        register(second, name="Ana Ruiz", email="ana@example.com")
        yield second
