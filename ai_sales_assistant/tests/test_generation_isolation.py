"""A user can only ever see and change their own generations, whatever id they send."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Generation
from tests.factories import generation_payload, make_generation
from tests.fakes import FakeAIProvider

GENERATIONS = "/api/v1/generations"


@pytest.fixture
def marias_generation(client: TestClient) -> dict:
    response = client.post("/api/v1/generate", json=generation_payload(customer="Cliente de María"))
    assert response.status_code == 201
    return response.json()


def test_list_only_contains_own_generations(
    client: TestClient, other_client: TestClient, marias_generation: dict
) -> None:
    other_client.post("/api/v1/generate", json=generation_payload(customer="Cliente de Ana"))

    marias = client.get(GENERATIONS).json()
    anas = other_client.get(GENERATIONS).json()

    assert [item["customer"] for item in marias["items"]] == ["Cliente de María"]
    assert [item["customer"] for item in anas["items"]] == ["Cliente de Ana"]
    assert (marias["total"], anas["total"]) == (1, 1)


def test_filtered_list_is_also_scoped(client: TestClient, other_client: TestClient, marias_generation: dict) -> None:
    response = other_client.get(GENERATIONS, params={"content_type": "commercial_email"})

    assert response.json()["total"] == 0


def test_cannot_read_another_users_generation(other_client: TestClient, marias_generation: dict) -> None:
    response = other_client.get(f"{GENERATIONS}/{marias_generation['id']}")

    # Same answer as a missing id: the response does not reveal that it exists.
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert "Cliente de María" not in response.text


def test_cannot_regenerate_another_users_generation(
    client: TestClient, other_client: TestClient, marias_generation: dict, fake_ai_provider: FakeAIProvider
) -> None:
    calls_before = len(fake_ai_provider.prompts)

    response = other_client.put(
        f"{GENERATIONS}/{marias_generation['id']}", json=generation_payload(customer="Intruso")
    )

    assert response.status_code == 404
    assert len(fake_ai_provider.prompts) == calls_before  # no AI call for someone else's id
    assert client.get(f"{GENERATIONS}/{marias_generation['id']}").json() == marias_generation


def test_cannot_delete_another_users_generation(
    client: TestClient, other_client: TestClient, marias_generation: dict
) -> None:
    response = other_client.delete(f"{GENERATIONS}/{marias_generation['id']}")

    assert response.status_code == 404
    assert client.get(f"{GENERATIONS}/{marias_generation['id']}").status_code == 200


def test_owner_can_still_manage_their_generation(client: TestClient, marias_generation: dict) -> None:
    generation_id = marias_generation["id"]

    assert client.get(f"{GENERATIONS}/{generation_id}").status_code == 200
    assert client.put(f"{GENERATIONS}/{generation_id}", json=generation_payload()).status_code == 200
    assert client.delete(f"{GENERATIONS}/{generation_id}").status_code == 204


def test_unassigned_legacy_generations_are_invisible_to_everyone(
    client: TestClient, other_client: TestClient, db_session: Session
) -> None:
    legacy = make_generation(user_id=None, customer="Generación antigua")
    db_session.add(legacy)
    db_session.commit()

    for user_client in (client, other_client):
        assert user_client.get(GENERATIONS).json()["total"] == 0
        assert user_client.get(f"{GENERATIONS}/{legacy.id}").status_code == 404
        assert user_client.delete(f"{GENERATIONS}/{legacy.id}").status_code == 404
    assert db_session.get(Generation, legacy.id) is not None
