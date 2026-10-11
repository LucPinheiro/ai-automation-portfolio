from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_ai_provider_resolver
from app.config import Settings
from app.core.exceptions import AIProviderError
from app.main import app
from app.models import Generation
from app.prompts.base import SYSTEM_PROMPT
from app.services.ai import create_ai_provider
from tests.factories import generation_payload
from tests.fakes import FakeAIProvider

GENERATE_URL = "/api/v1/generate"
GENERATIONS_URL = "/api/v1/generations"


def generate(client: TestClient, **overrides: Any) -> dict[str, Any]:
    response = client.post(GENERATE_URL, json=generation_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def stored_count(db_session: Session) -> int:
    # Every row in the table, whoever owns it.
    return db_session.scalar(select(func.count()).select_from(Generation)) or 0


# --- POST /api/v1/generate ---------------------------------------------------


def test_generate_returns_201_with_generated_content(
    client: TestClient, fake_ai_provider: FakeAIProvider
) -> None:
    fake_ai_provider.content = "Estimada María, ..."

    body = generate(client)

    assert body["id"] >= 1
    assert body["content_type"] == "commercial_email"
    assert body["generated_content"] == "Estimada María, ..."
    assert body["language"] == "es"
    assert body["tone"] == "professional"
    assert body["customer"] == "María López"
    assert body["ai_model"] == "fake-model"
    assert body["created_at"].endswith("Z") or body["created_at"].endswith("+00:00")


def test_generate_persists_the_generation(client: TestClient, db_session: Session) -> None:
    body = generate(client)

    assert stored_count(db_session) == 1
    assert client.get(f"{GENERATIONS_URL}/{body['id']}").json() == body


def test_generate_does_not_expose_prompts_or_token_usage(client: TestClient) -> None:
    response = client.post(GENERATE_URL, json=generation_payload())

    assert SYSTEM_PROMPT[:40] not in response.text
    assert "<customer_data>" not in response.text
    assert not {"prompt", "system", "prompt_tokens", "completion_tokens"} & response.json().keys()


@pytest.mark.parametrize(
    ("overrides", "field", "error_type"),
    [
        ({"content_type": "blog_post"}, "content_type", "enum"),
        ({"language": "de"}, "language", "enum"),
        ({"tone": "angry"}, "tone", "enum"),
        ({"customer": "   "}, "customer", "string_too_short"),
        ({"customer_needs": "x" * 2001}, "customer_needs", "string_too_long"),
        ({"unexpected": "value"}, "unexpected", "extra_forbidden"),
    ],
)
def test_generate_with_invalid_data_returns_422(
    client: TestClient,
    db_session: Session,
    fake_ai_provider: FakeAIProvider,
    overrides: dict[str, Any],
    field: str,
    error_type: str,
) -> None:
    response = client.post(GENERATE_URL, json=generation_payload(**overrides))

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert {"field": field, "type": error_type}.items() <= error["details"][0].items()
    assert fake_ai_provider.prompts == []
    assert stored_count(db_session) == 0


def test_generate_with_missing_field_returns_422(client: TestClient) -> None:
    payload = generation_payload()
    del payload["product_or_service"]

    response = client.post(GENERATE_URL, json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "product_or_service"


def test_generate_with_malformed_json_returns_400(client: TestClient, db_session: Session) -> None:
    response = client.post(
        GENERATE_URL, content=b'{"content_type": "whatsapp",', headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_json"
    assert stored_count(db_session) == 0


def test_provider_failure_returns_502_and_persists_nothing(
    client: TestClient, db_session: Session, fake_ai_provider: FakeAIProvider
) -> None:
    fake_ai_provider.error = AIProviderError()

    response = client.post(GENERATE_URL, json=generation_payload())

    assert response.status_code == 502
    assert response.json()["error"] == {
        "code": "ai_provider_error",
        "message": AIProviderError.default_message,
        "details": [],
    }
    assert stored_count(db_session) == 0


def test_missing_api_key_returns_503_and_persists_nothing(client: TestClient, db_session: Session) -> None:
    # Uses the real factory with settings that have no OPENAI_API_KEY.
    settings = Settings(_env_file=None, openai_api_key=None)  # type: ignore[call-arg]
    app.dependency_overrides[get_ai_provider_resolver] = lambda: lambda: create_ai_provider(settings)

    response = client.post(GENERATE_URL, json=generation_payload())

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ai_provider_not_configured"
    assert stored_count(db_session) == 0


def test_listing_works_when_provider_is_not_configured(client: TestClient) -> None:
    settings = Settings(_env_file=None, openai_api_key=None)  # type: ignore[call-arg]
    app.dependency_overrides[get_ai_provider_resolver] = lambda: lambda: create_ai_provider(settings)

    assert client.get(GENERATIONS_URL).status_code == 200


# --- GET /api/v1/generations -------------------------------------------------


def test_list_returns_newest_first_with_total(client: TestClient) -> None:
    first = generate(client, customer="First")
    second = generate(client, customer="Second")

    body = client.get(GENERATIONS_URL).json()

    assert body["total"] == 2
    assert (body["limit"], body["offset"]) == (20, 0)
    assert [item["id"] for item in body["items"]] == [second["id"], first["id"]]


def test_list_supports_pagination_and_content_type_filter(client: TestClient) -> None:
    for content_type in ("whatsapp", "sales_proposal", "whatsapp", "whatsapp"):
        generate(client, content_type=content_type)

    body = client.get(GENERATIONS_URL, params={"content_type": "whatsapp", "limit": 2, "offset": 1}).json()

    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert {item["content_type"] for item in body["items"]} == {"whatsapp"}


def test_list_is_empty_without_generations(client: TestClient) -> None:
    assert client.get(GENERATIONS_URL).json() == {"items": [], "total": 0, "limit": 20, "offset": 0}


@pytest.mark.parametrize(
    "params", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"content_type": "blog_post"}]
)
def test_list_with_invalid_query_returns_422(client: TestClient, params: dict[str, Any]) -> None:
    response = client.get(GENERATIONS_URL, params=params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


# --- GET /api/v1/generations/{id} ---------------------------------------------


def test_get_returns_the_generation(client: TestClient) -> None:
    created = generate(client, content_type="customer_summary")

    response = client.get(f"{GENERATIONS_URL}/{created['id']}")

    assert response.status_code == 200
    assert response.json()["content_type"] == "customer_summary"


def test_get_unknown_id_returns_404(client: TestClient) -> None:
    response = client.get(f"{GENERATIONS_URL}/999")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "Generation 999 was not found.", "details": []}
    }


@pytest.mark.parametrize("generation_id", ["0", "abc"])
def test_get_invalid_id_returns_422(client: TestClient, generation_id: str) -> None:
    assert client.get(f"{GENERATIONS_URL}/{generation_id}").status_code == 422


# --- OpenAPI ------------------------------------------------------------------


def test_openapi_documents_endpoints_with_common_error_schema(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    generate_responses = paths[GENERATE_URL]["post"]["responses"]
    assert set(generate_responses) == {"201", "400", "401", "403", "422", "500", "502", "503"}
    assert generate_responses["422"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/ErrorResponse"
    )
    assert "404" in paths[f"{GENERATIONS_URL}/{{generation_id}}"]["get"]["responses"]
    assert paths[GENERATIONS_URL]["get"]["summary"] == "List generations"


# --- PUT /api/v1/generations/{id} --------------------------------------------------


def test_regenerate_updates_the_same_generation(
    client: TestClient, db_session: Session, fake_ai_provider: FakeAIProvider
) -> None:
    created = generate(client)
    fake_ai_provider.content = "Nueva versión"

    response = client.put(f"{GENERATIONS_URL}/{created['id']}", json=generation_payload(customer="Ana Ruiz"))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == created["id"]
    assert body["customer"] == "Ana Ruiz"
    assert body["generated_content"] == "Nueva versión"
    assert body["created_at"] == created["created_at"]
    assert stored_count(db_session) == 1
    assert client.get(f"{GENERATIONS_URL}/{created['id']}").json() == body


def test_regenerate_unknown_id_returns_404(client: TestClient, fake_ai_provider: FakeAIProvider) -> None:
    response = client.put(f"{GENERATIONS_URL}/999", json=generation_payload())

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert fake_ai_provider.prompts == []


def test_regenerate_rejects_generated_content_from_the_client(client: TestClient) -> None:
    created = generate(client)
    payload = generation_payload(generated_content="Texto escrito a mano")

    response = client.put(f"{GENERATIONS_URL}/{created['id']}", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "generated_content"
    assert client.get(f"{GENERATIONS_URL}/{created['id']}").json() == created


def test_regenerate_with_invalid_data_returns_422(client: TestClient) -> None:
    created = generate(client)

    response = client.put(f"{GENERATIONS_URL}/{created['id']}", json=generation_payload(customer="   "))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_regenerate_provider_failure_returns_502_and_keeps_the_record(
    client: TestClient, fake_ai_provider: FakeAIProvider
) -> None:
    created = generate(client)
    fake_ai_provider.error = AIProviderError()

    response = client.put(f"{GENERATIONS_URL}/{created['id']}", json=generation_payload(customer="Ana Ruiz"))

    assert response.status_code == 502
    assert client.get(f"{GENERATIONS_URL}/{created['id']}").json() == created


@pytest.mark.parametrize("generation_id", ["0", "abc"])
def test_regenerate_invalid_id_returns_422(client: TestClient, generation_id: str) -> None:
    response = client.put(f"{GENERATIONS_URL}/{generation_id}", json=generation_payload())

    assert response.status_code == 422


# --- DELETE /api/v1/generations/{id} -----------------------------------------------


def test_delete_returns_204_and_removes_the_generation(client: TestClient, db_session: Session) -> None:
    created = generate(client)

    response = client.delete(f"{GENERATIONS_URL}/{created['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert stored_count(db_session) == 0
    assert client.get(f"{GENERATIONS_URL}/{created['id']}").status_code == 404


def test_delete_unknown_id_returns_404(client: TestClient) -> None:
    response = client.delete(f"{GENERATIONS_URL}/999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize("generation_id", ["0", "abc"])
def test_delete_invalid_id_returns_422(client: TestClient, generation_id: str) -> None:
    assert client.delete(f"{GENERATIONS_URL}/{generation_id}").status_code == 422


# --- Salesperson (sender) ---------------------------------------------------------------


def test_salesperson_is_stored_and_returned(client: TestClient, fake_ai_provider: FakeAIProvider) -> None:
    body = generate(client, salesperson="Carlos Vila", salesperson_company="FleetSoft S.L.")

    assert (body["salesperson"], body["salesperson_company"]) == ("Carlos Vila", "FleetSoft S.L.")
    assert client.get(f"{GENERATIONS_URL}/{body['id']}").json()["salesperson"] == "Carlos Vila"
    assert client.get(GENERATIONS_URL).json()["items"][0]["salesperson"] == "Carlos Vila"
    # It reaches the AI as the sender, separate from the customer.
    assert "Salesperson (sender): Carlos Vila" in fake_ai_provider.prompts[-1].user
    assert "Salesperson's company: FleetSoft S.L." in fake_ai_provider.prompts[-1].user


@pytest.mark.parametrize("value", [None, "", "   "])
def test_salesperson_is_optional_and_never_invented(client: TestClient, value: str | None) -> None:
    overrides = {} if value is None else {"salesperson": value, "salesperson_company": value}

    body = generate(client, **overrides)

    assert (body["salesperson"], body["salesperson_company"]) == (None, None)


def test_salesperson_too_long_returns_422(client: TestClient) -> None:
    response = client.post(GENERATE_URL, json=generation_payload(salesperson="x" * 151))

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "salesperson"


def test_regenerate_updates_or_clears_the_salesperson(client: TestClient) -> None:
    created = generate(client, salesperson="Carlos Vila")

    changed = client.put(f"{GENERATIONS_URL}/{created['id']}", json=generation_payload(salesperson="Ana Ruiz")).json()
    cleared = client.put(f"{GENERATIONS_URL}/{created['id']}", json=generation_payload()).json()

    assert changed["salesperson"] == "Ana Ruiz"
    assert cleared["salesperson"] is None


def test_guest_can_use_the_salesperson(anon_client: TestClient) -> None:
    anon_client.post("/api/v1/auth/guest")

    body = generate(anon_client, salesperson="Carlos Vila")

    assert body["salesperson"] == "Carlos Vila"


# --- Pricing (calculated by the backend) ------------------------------------------------


def test_generation_with_price_and_discount(
    client: TestClient, db_session: Session, fake_ai_provider: FakeAIProvider
) -> None:
    body = generate(client, price="179", discount_percent="15")

    assert (body["price"], body["discount_percent"]) == ("179.00", "15.00")
    assert body["pricing"] == {
        "original_price": "179.00",
        "discount_percent": "15.00",
        "discount_amount": "26.85",
        "final_price": "152.15",
        "currency": "EUR",
    }
    # Stored as exact integers; derived amounts are not stored.
    stored = db_session.get(Generation, body["id"])
    assert (stored.price_cents, stored.discount_basis_points) == (17900, 1500)
    # The AI receives the figures already calculated.
    prompt = fake_ai_provider.prompts[-1].user
    for line in ("Original price: 179.00 EUR", "Discount: 15%", "Discount amount: 26.85 EUR", "Final price: 152.15 EUR"):
        assert line in prompt


@pytest.mark.parametrize(
    ("price", "percent", "final"),
    [(179, 15, "152.15"), (100, 10, "90.00"), (49.99, 20, "39.99"), ("49,99".replace(",", "."), "20", "39.99")],
)
def test_json_numbers_and_strings_give_exact_results(client: TestClient, price, percent, final: str) -> None:
    body = generate(client, price=price, discount_percent=percent)

    assert body["pricing"]["final_price"] == final


def test_generation_with_price_only(client: TestClient, fake_ai_provider: FakeAIProvider) -> None:
    body = generate(client, price="49.99")

    assert body["pricing"]["discount_percent"] is None
    assert body["pricing"]["final_price"] == "49.99"
    assert "Price: 49.99 EUR" in fake_ai_provider.prompts[-1].user
    assert "Discount: none" in fake_ai_provider.prompts[-1].user


@pytest.mark.parametrize("empty", [None, ""])
def test_generation_without_pricing(client: TestClient, fake_ai_provider: FakeAIProvider, empty: str | None) -> None:
    overrides = {} if empty is None else {"price": empty, "discount_percent": empty}

    body = generate(client, **overrides)

    assert (body["price"], body["discount_percent"], body["pricing"]) == (None, None, None)
    assert "Pricing: not provided" in fake_ai_provider.prompts[-1].user


@pytest.mark.parametrize(
    ("overrides", "field", "error_type"),
    [
        ({"discount_percent": "15"}, "discount_percent", "discount_requires_price"),
        ({"price": "", "discount_percent": "15"}, "discount_percent", "discount_requires_price"),
        ({"price": "-10"}, "price", "greater_than"),
        ({"price": "0"}, "price", "greater_than"),
        ({"price": "179.999"}, "price", "decimal_max_places"),
        ({"price": "abc"}, "price", "decimal_parsing"),
        ({"price": "100", "discount_percent": "-1"}, "discount_percent", "greater_than_equal"),
        ({"price": "100", "discount_percent": "100.5"}, "discount_percent", "less_than_equal"),
        ({"price": "100", "discount_percent": "250"}, "discount_percent", "less_than_equal"),
        ({"price": "NaN"}, "price", "finite_number"),
    ],
)
def test_invalid_pricing_returns_422_without_calling_the_ai(
    client: TestClient, fake_ai_provider: FakeAIProvider, overrides: dict, field: str, error_type: str
) -> None:
    response = client.post(GENERATE_URL, json=generation_payload(**overrides))

    assert response.status_code == 422
    details = response.json()["error"]["details"]
    assert {"field": field, "type": error_type} in [{"field": d["field"], "type": d["type"]} for d in details]
    assert fake_ai_provider.prompts == []


def test_editing_changes_or_removes_the_pricing(client: TestClient, fake_ai_provider: FakeAIProvider) -> None:
    created = generate(client, price="179", discount_percent="15")

    changed = client.put(
        f"{GENERATIONS_URL}/{created['id']}", json=generation_payload(price="100", discount_percent="10")
    ).json()
    assert changed["pricing"]["final_price"] == "90.00"
    assert "Final price: 90.00 EUR" in fake_ai_provider.prompts[-1].user

    removed = client.put(f"{GENERATIONS_URL}/{created['id']}", json=generation_payload()).json()
    assert removed["pricing"] is None
    assert client.get(f"{GENERATIONS_URL}/{created['id']}").json()["pricing"] is None


def test_pricing_appears_in_the_history(client: TestClient) -> None:
    generate(client, price="100", discount_percent="0")

    item = client.get(GENERATIONS_URL).json()["items"][0]

    assert item["pricing"]["discount_amount"] == "0.00"
    assert item["pricing"]["final_price"] == "100.00"


# --- Customer email (pre-fills the share-by-email button) --------------------------------------------


def test_customer_email_is_stored_and_returned(client: TestClient) -> None:
    created = generate(client, customer_email="maria@logisticanorte.es")

    assert created["customer_email"] == "maria@logisticanorte.es"
    assert client.get(f"/api/v1/generations/{created['id']}").json()["customer_email"] == "maria@logisticanorte.es"


@pytest.mark.parametrize("value", [None, "", "   "])
def test_customer_email_is_optional(client: TestClient, value: str | None) -> None:
    assert generate(client, customer_email=value)["customer_email"] is None


@pytest.mark.parametrize("value", ["not-an-email", "maria@", "a" * 250 + "@x.es"])
def test_invalid_customer_email_is_rejected(client: TestClient, value: str) -> None:
    response = client.post("/api/v1/generate", json=generation_payload(customer_email=value))

    assert response.status_code == 422
    assert any(detail["field"] == "customer_email" for detail in response.json()["error"]["details"])


def test_regenerate_updates_the_customer_email(client: TestClient) -> None:
    created = generate(client, customer_email="old@example.com")

    response = client.put(f"/api/v1/generations/{created['id']}", json=generation_payload(customer_email="new@example.com"))

    assert response.json()["customer_email"] == "new@example.com"


def test_customer_email_is_never_sent_to_the_ai(client: TestClient, fake_ai_provider: FakeAIProvider) -> None:
    generate(client, customer_email="maria@logisticanorte.es")

    prompt = fake_ai_provider.prompts[-1]
    assert "maria@logisticanorte.es" not in prompt.system + prompt.user
