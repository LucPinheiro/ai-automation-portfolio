"""Optional live test against the real AI provider configured in .env (Ollama or OpenAI).

Skipped unless RUN_LLM_TESTS=1, because it is slow and may cost money:

    RUN_LLM_TESTS=1 pytest tests/llm -s          (Git Bash / Linux / macOS)
    $env:RUN_LLM_TESTS=1; pytest tests/llm -s    (PowerShell)

It runs the real generation flow (prompt, verification and the single retry) with the container
example and checks, with the same deterministic verifier the app uses, that every mandatory
commercial term is in the final text. On failure it prints the text and what is missing.
"""

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (registers ORM models)
from app.config import Settings
from app.database import Base
from app.repositories import GenerationRepository
from app.schemas.generation import GenerationCreate
from app.services.ai import create_ai_provider
from app.services.generation_service import GenerationService
from tests.factories import make_user

pytestmark = pytest.mark.skipif(os.environ.get("RUN_LLM_TESTS") != "1", reason="set RUN_LLM_TESTS=1 to call the real model")

SCALE = (
    "Oferta por volumen:\n"
    "- De 1 a 5 contenedores: precio habitual, sin descuento.\n"
    "- De 6 a 10 contenedores: 5 % de descuento.\n"
    "- De 11 a 20 contenedores: 10 % de descuento.\n"
    "- De 21 a 50 contenedores: 15 % de descuento.\n"
    "- Más de 50 contenedores: 20 % de descuento."
)
BASE = {
    "customer": "María López",
    "company": "Pesquera Atlántica S.L.",
    "industry": "Pesca",
    "product_or_service": "Contenedores para el sector pesquero",
    "salesperson": "Carlos Vila",
    "salesperson_company": "Logística Norte S.L.",
    "language": "es",
    "tone": "professional",
}


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    db.add(make_user(id=1))
    db.commit()
    yield db
    db.close()
    engine.dispose()


@pytest.mark.parametrize(
    ("case", "extra"),
    [
        ("case-3-scale-and-structured-pricing", {"customer_needs": SCALE, "price": "15000", "discount_percent": "15"}),
        ("case-1-scale-only", {"customer_needs": SCALE}),
        ("case-2-structured-pricing-only", {"customer_needs": "Renovar la flota de contenedores.", "price": "15000", "discount_percent": "15"}),
    ],
)
@pytest.mark.parametrize("content_type", ["commercial_email", "sales_proposal"])
def test_real_model_keeps_every_commercial_term(session: Session, case: str, extra: dict, content_type: str) -> None:
    settings = Settings()  # the provider configured in .env (AI_PROVIDER=ollama or openai)
    provider = create_ai_provider(settings)
    service = GenerationService(
        session,
        GenerationRepository(session),
        lambda: provider,
        commercial_terms_max_retries=settings.commercial_terms_max_retries,
    )

    result = service.generate(
        GenerationCreate.model_validate({**BASE, **extra, "content_type": content_type}), user_id=1
    )

    print(f"\n--- {case} / {content_type} ({result.ai_provider} {result.ai_model}) ---\n{result.generated_content}")
    assert result.missing_commercial_terms == [], f"Missing: {result.missing_commercial_terms}"
