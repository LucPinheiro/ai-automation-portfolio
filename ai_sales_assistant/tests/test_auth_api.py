from datetime import UTC, datetime, timedelta
from http.cookies import SimpleCookie

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.main import app
from app.models import User, UserSession
from tests.factories import PASSWORD, generation_payload, register, register_payload

AUTH = "/api/v1/auth"
COOKIE = "ai_sales_session"


def session_cookie_header(response) -> SimpleCookie:
    cookies = SimpleCookie()
    for header in response.headers.get_list("set-cookie"):
        cookies.load(header)
    return cookies


def login(client: TestClient, email: str = "maria@example.com", password: str = PASSWORD):
    return client.post(f"{AUTH}/login", json={"email": email, "password": password})


def session_count(db_session: Session) -> int:
    return db_session.scalar(select(func.count()).select_from(UserSession)) or 0


# --- Registration -------------------------------------------------------------------------


def test_register_creates_the_account_and_logs_in(anon_client: TestClient) -> None:
    response = anon_client.post(f"{AUTH}/register", json=register_payload())

    assert response.status_code == 201
    body = response.json()
    assert body.keys() == {"id", "name", "email", "username", "is_guest", "created_at"}
    assert body["is_guest"] is False
    assert (body["name"], body["email"]) == ("María López", "maria@example.com")
    assert anon_client.get(f"{AUTH}/me").json()["id"] == body["id"]


def test_register_stores_only_an_argon2_hash(anon_client: TestClient, db_session: Session) -> None:
    register(anon_client)

    user = db_session.scalar(select(User))
    assert user is not None
    assert user.password_hash.startswith("$argon2id$")
    assert PASSWORD not in user.password_hash


def test_session_cookie_is_http_only_and_same_site_lax(anon_client: TestClient) -> None:
    response = anon_client.post(f"{AUTH}/register", json=register_payload())

    cookie = session_cookie_header(response)[COOKIE]
    assert cookie["httponly"]
    assert cookie["samesite"].lower() == "lax"
    assert cookie["path"] == "/"
    assert abs(int(cookie["max-age"]) - 168 * 3600) <= 5
    assert not cookie["secure"]  # testing environment over plain http


def test_session_cookie_is_secure_in_production(anon_client: TestClient) -> None:
    production = Settings(_env_file=None, environment="production", email_backend="smtp")  # type: ignore[call-arg]
    app.dependency_overrides[get_settings] = lambda: production

    response = anon_client.post(f"{AUTH}/register", json=register_payload())

    assert session_cookie_header(response)[COOKIE]["secure"]


@pytest.mark.parametrize("email", ["maria@example.com", "MARIA@Example.com", "  maria@example.com "])
def test_duplicate_email_returns_409(anon_client: TestClient, email: str) -> None:
    register(anon_client)

    response = anon_client.post(f"{AUTH}/register", json=register_payload(name="Otra", email=email))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_already_registered"


@pytest.mark.parametrize(
    ("overrides", "field", "error_type"),
    [
        ({"email": "not-an-email"}, "email", "value_error"),
        ({"name": "   "}, "name", "string_too_short"),
        ({"password": "short", "password_confirm": "short"}, "password", "string_too_short"),
        ({"password": "x" * 129, "password_confirm": "x" * 129}, "password", "string_too_long"),
        ({"password_confirm": "different-password"}, "password_confirm", "password_mismatch"),
        ({"is_admin": True}, "is_admin", "extra_forbidden"),
    ],
)
def test_register_validates_input(anon_client: TestClient, overrides: dict, field: str, error_type: str) -> None:
    response = anon_client.post(f"{AUTH}/register", json=register_payload(**overrides))

    assert response.status_code == 422
    details = response.json()["error"]["details"]
    assert {"field": field, "type": error_type} in [{"field": d["field"], "type": d["type"]} for d in details]


# --- Login ----------------------------------------------------------------------------------


def test_login_with_correct_credentials(anon_client: TestClient) -> None:
    register(anon_client)
    anon_client.cookies.clear()

    response = login(anon_client, email="MARIA@example.com")

    assert response.status_code == 200
    assert response.json()["email"] == "maria@example.com"
    assert session_cookie_header(response)[COOKIE]["httponly"]
    assert anon_client.get(f"{AUTH}/me").status_code == 200


@pytest.mark.parametrize(
    ("email", "password"),
    [("maria@example.com", "wrong-password"), ("nobody@example.com", PASSWORD)],
)
def test_login_failure_is_identical_for_wrong_password_and_unknown_email(
    anon_client: TestClient, email: str, password: str
) -> None:
    register(anon_client)
    anon_client.cookies.clear()

    response = login(anon_client, email=email, password=password)

    assert response.status_code == 401
    assert response.json() == {
        "error": {"code": "invalid_credentials", "message": "Invalid email or password.", "details": []}
    }
    assert COOKIE not in session_cookie_header(response)
    assert anon_client.get(f"{AUTH}/me").status_code == 401


# --- Current user and logout ---------------------------------------------------------------


def test_me_returns_the_user_without_secrets(client: TestClient) -> None:
    response = client.get(f"{AUTH}/me")

    assert response.status_code == 200
    assert response.json().keys() == {"id", "name", "email", "username", "is_guest", "created_at"}
    assert "argon2" not in response.text


def test_me_without_session_returns_401(anon_client: TestClient) -> None:
    response = anon_client.get(f"{AUTH}/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_me_with_a_forged_cookie_returns_401(anon_client: TestClient) -> None:
    anon_client.cookies.set(COOKIE, "forged-token")

    assert anon_client.get(f"{AUTH}/me").status_code == 401


def test_logout_closes_the_session_on_the_server(client: TestClient, db_session: Session) -> None:
    old_token = client.cookies.get(COOKIE)

    response = client.post(f"{AUTH}/logout")

    assert response.status_code == 204
    cleared = session_cookie_header(response)[COOKIE]
    assert cleared.value == "" or cleared["max-age"] == "0"
    assert session_count(db_session) == 0
    assert client.get(f"{AUTH}/me").status_code == 401
    # Replaying the old cookie no longer works.
    client.cookies.set(COOKIE, old_token)
    assert client.get(f"{AUTH}/me").status_code == 401
    assert client.get("/api/v1/generations").status_code == 401


def test_logout_without_session_returns_401(anon_client: TestClient) -> None:
    assert anon_client.post(f"{AUTH}/logout").status_code == 401


def test_logout_only_closes_the_current_session(anon_client: TestClient) -> None:
    register(anon_client)
    with TestClient(app) as second_browser:
        assert login(second_browser).status_code == 200

        anon_client.post(f"{AUTH}/logout")

        assert second_browser.get(f"{AUTH}/me").status_code == 200


# --- Protected endpoints -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/v1/generate"),
        ("get", "/api/v1/generations"),
        ("get", "/api/v1/generations/1"),
        ("put", "/api/v1/generations/1"),
        ("delete", "/api/v1/generations/1"),
    ],
)
def test_generation_endpoints_require_authentication(anon_client: TestClient, method: str, path: str) -> None:
    kwargs = {"json": generation_payload()} if method in {"post", "put"} else {}

    response = anon_client.request(method.upper(), path, **kwargs)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_authenticated_user_can_generate(client: TestClient) -> None:
    response = client.post("/api/v1/generate", json=generation_payload())

    assert response.status_code == 201
    assert client.get("/api/v1/generations").json()["total"] == 1


def test_expired_session_is_rejected(client: TestClient, db_session: Session) -> None:
    for user_session in db_session.scalars(select(UserSession)):
        user_session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()

    assert client.get(f"{AUTH}/me").status_code == 401


def test_session_token_is_stored_only_as_a_hash(client: TestClient, db_session: Session) -> None:
    token = client.cookies.get(COOKIE)
    stored = db_session.scalar(select(UserSession))

    assert stored is not None
    assert stored.token_hash != token
    assert len(stored.token_hash) == 64


# --- Change password --------------------------------------------------------------------------


def change_password(client: TestClient, current: str = PASSWORD, new: str = "new-password-123", confirm=None):
    return client.post(
        f"{AUTH}/change-password",
        json={"current_password": current, "new_password": new, "new_password_confirm": confirm or new},
    )


def test_change_password_replaces_the_password(client: TestClient) -> None:
    response = change_password(client)

    assert response.status_code == 204
    assert client.get(f"{AUTH}/me").status_code == 200  # the current browser keeps a (new) session
    client.cookies.clear()
    assert login(client).status_code == 401
    assert login(client, password="new-password-123").status_code == 200


def test_change_password_closes_other_sessions(client: TestClient) -> None:
    with TestClient(app) as other_device:
        assert login(other_device).status_code == 200

        change_password(client)

        assert other_device.get(f"{AUTH}/me").status_code == 401


def test_change_password_rotates_the_current_session(client: TestClient) -> None:
    before = client.cookies.get(COOKIE)

    response = change_password(client)

    after = session_cookie_header(response)[COOKIE].value
    assert after and after != before


def test_change_password_with_wrong_current_password(client: TestClient) -> None:
    response = change_password(client, current="not-my-password")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_current_password"
    client.cookies.clear()
    assert login(client).status_code == 200


def test_change_password_validates_the_new_password(client: TestClient) -> None:
    mismatch = change_password(client, confirm="something-else-1")
    too_short = change_password(client, new="short")

    assert mismatch.status_code == 422
    assert mismatch.json()["error"]["details"][0]["field"] == "new_password_confirm"
    assert too_short.status_code == 422


def test_change_password_requires_authentication(anon_client: TestClient) -> None:
    assert change_password(anon_client).status_code == 401
