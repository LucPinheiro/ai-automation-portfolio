import re
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PasswordResetToken
from tests.factories import PASSWORD, register
from tests.fakes import FakeEmailSender

AUTH = "/api/v1/auth"
NEW_PASSWORD = "brand-new-password-9"
GENERIC_MESSAGE = "If an account exists for that email, a password reset link has been sent."


def request_reset(client: TestClient, email: str = "maria@example.com"):
    return client.post(f"{AUTH}/forgot-password", json={"email": email})


def reset(client: TestClient, token: str, password: str = NEW_PASSWORD, confirm: str | None = None):
    return client.post(
        f"{AUTH}/reset-password",
        json={"token": token, "new_password": password, "new_password_confirm": confirm or password},
    )


def login(client: TestClient, password: str):
    return client.post(f"{AUTH}/login", json={"email": "maria@example.com", "password": password})


def token_from_email(sender: FakeEmailSender) -> str:
    link = re.search(r"https?://\S+/reset-password\?\S+", sender.messages[-1].body)
    assert link, "reset link not found in the email"
    return parse_qs(urlsplit(link.group(0)).query)["token"][0]


@pytest.fixture
def account(anon_client: TestClient) -> TestClient:
    """A registered account, logged out (as someone who forgot the password would be)."""
    register(anon_client)
    anon_client.post(f"{AUTH}/logout")
    return anon_client


# --- Request -----------------------------------------------------------------------------------


def test_request_for_existing_email_sends_a_reset_link(
    account: TestClient, fake_email_sender: FakeEmailSender
) -> None:
    response = request_reset(account, email="MARIA@example.com")

    assert response.status_code == 202
    assert response.json() == {"message": GENERIC_MESSAGE}
    assert len(fake_email_sender.messages) == 1
    message = fake_email_sender.messages[0]
    assert message.to == "maria@example.com"
    assert "/reset-password?token=" in message.body
    assert "30 minutos" in message.body


def test_request_for_unknown_email_looks_identical_and_sends_nothing(
    account: TestClient, fake_email_sender: FakeEmailSender
) -> None:
    known = request_reset(account)
    unknown = request_reset(account, email="nobody@example.com")

    assert (unknown.status_code, unknown.json()) == (known.status_code, known.json())
    assert [m.to for m in fake_email_sender.messages] == ["maria@example.com"]


def test_reset_token_is_stored_only_as_a_hash(
    account: TestClient, db_session: Session, fake_email_sender: FakeEmailSender
) -> None:
    request_reset(account)
    token = token_from_email(fake_email_sender)

    stored = db_session.scalar(select(PasswordResetToken))
    assert stored is not None
    assert stored.token_hash != token
    assert token not in stored.token_hash
    assert stored.used_at is None


def test_request_with_invalid_email_returns_422(anon_client: TestClient) -> None:
    assert request_reset(anon_client, email="not-an-email").status_code == 422


# --- Reset ---------------------------------------------------------------------------------------


def test_valid_token_resets_the_password(account: TestClient, fake_email_sender: FakeEmailSender) -> None:
    request_reset(account)

    response = reset(account, token_from_email(fake_email_sender))

    assert response.status_code == 204
    assert login(account, PASSWORD).status_code == 401
    assert login(account, NEW_PASSWORD).status_code == 200


def test_invalid_token_is_rejected(account: TestClient) -> None:
    response = reset(account, "this-token-does-not-exist")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_or_expired_token"
    assert login(account, PASSWORD).status_code == 200


def test_expired_token_is_rejected(
    account: TestClient, db_session: Session, fake_email_sender: FakeEmailSender
) -> None:
    request_reset(account)
    token = token_from_email(fake_email_sender)
    stored = db_session.scalar(select(PasswordResetToken))
    stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()

    response = reset(account, token)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_or_expired_token"
    assert login(account, PASSWORD).status_code == 200


def test_token_expires_after_the_configured_time(
    account: TestClient, db_session: Session, fake_email_sender: FakeEmailSender
) -> None:
    before = datetime.now(UTC)
    request_reset(account)

    stored = db_session.scalar(select(PasswordResetToken))
    assert before + timedelta(minutes=29) < stored.expires_at <= datetime.now(UTC) + timedelta(minutes=30)


def test_used_token_cannot_be_reused(account: TestClient, fake_email_sender: FakeEmailSender) -> None:
    request_reset(account)
    token = token_from_email(fake_email_sender)
    assert reset(account, token).status_code == 204

    second = reset(account, token, password="another-password-7")

    assert second.status_code == 400
    assert second.json()["error"]["code"] == "invalid_or_expired_token"
    assert login(account, NEW_PASSWORD).status_code == 200


def test_new_request_invalidates_the_previous_link(account: TestClient, fake_email_sender: FakeEmailSender) -> None:
    request_reset(account)
    first = token_from_email(fake_email_sender)
    request_reset(account)
    second = token_from_email(fake_email_sender)

    assert reset(account, first).status_code == 400
    assert reset(account, second).status_code == 204


def test_reset_closes_every_session(anon_client: TestClient, fake_email_sender: FakeEmailSender) -> None:
    register(anon_client)  # still logged in on this device
    request_reset(anon_client)

    reset(anon_client, token_from_email(fake_email_sender))

    assert anon_client.get(f"{AUTH}/me").status_code == 401


def test_reset_validates_the_new_password(account: TestClient, fake_email_sender: FakeEmailSender) -> None:
    request_reset(account)
    token = token_from_email(fake_email_sender)

    mismatch = reset(account, token, confirm="different-password")
    too_short = reset(account, token, password="short")

    assert mismatch.status_code == 422
    assert too_short.status_code == 422
    # A rejected attempt does not consume the token.
    assert reset(account, token).status_code == 204
