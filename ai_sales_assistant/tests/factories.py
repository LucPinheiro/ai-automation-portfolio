from typing import Any

from fastapi.testclient import TestClient

from app.core.enums import ContentType, Language, Tone
from app.core.security import hash_password
from app.models import Generation, User

# Id of the default owner in repository/service tests (created by their `owner` fixture).
OWNER = 1
PASSWORD = "correct-horse-battery"

REGISTER_URL = "/api/v1/auth/register"


def generation_payload(**overrides: Any) -> dict[str, Any]:
    """A valid request body for content generation."""
    payload: dict[str, Any] = {
        "content_type": "commercial_email",
        "customer": "María López",
        "company": "Logística Norte S.L.",
        "industry": "Logistics",
        "product_or_service": "Fleet management software",
        "customer_needs": "Reduce fuel costs and track deliveries in real time.",
        "language": "es",
        "tone": "professional",
    }
    return payload | overrides


def make_generation(**overrides: Any) -> Generation:
    fields: dict[str, Any] = {
        "user_id": OWNER,
        "content_type": ContentType.COMMERCIAL_EMAIL,
        "customer": "María López",
        "company": "Logística Norte S.L.",
        "industry": "Logistics",
        "product_or_service": "Fleet management software",
        "customer_needs": "Reduce fuel costs.",
        "language": Language.SPANISH,
        "tone": Tone.PROFESSIONAL,
        "generated_content": "Estimada María, ...",
        "ai_provider": "fake",
        "ai_model": "fake-model",
        "prompt_tokens": 120,
        "completion_tokens": 80,
    }
    return Generation(**(fields | overrides))


def make_user(**overrides: Any) -> User:
    fields: dict[str, Any] = {
        "name": "María López",
        "email": "maria@example.com",
        "password_hash": hash_password(PASSWORD),
    }
    return User(**(fields | overrides))


def register_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "María López",
        "email": "maria@example.com",
        "password": PASSWORD,
        "password_confirm": PASSWORD,
    }
    return payload | overrides


def register(client: TestClient, **overrides: Any) -> dict[str, Any]:
    """Registers (and thereby logs in) an account through the real API."""
    response = client.post(REGISTER_URL, json=register_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()
