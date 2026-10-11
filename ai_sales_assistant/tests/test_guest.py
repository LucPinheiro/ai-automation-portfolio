"""Guest mode: a temporary account inside the normal authentication system."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from http.cookies import SimpleCookie

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.cli import purge_expired_guests
from app.config import Settings
from app.main import app
from app.models import Generation, User, UserSession
from tests.factories import PASSWORD, generation_payload, register
from tests.fakes import FakeAIProvider

AUTH = "/api/v1/auth"
GENERATIONS = "/api/v1/generations"
COOKIE = "ai_sales_session"


def start_guest(client: TestClient) -> dict:
    response = client.post(f"{AUTH}/guest")
    assert response.status_code == 201, response.text
    return response.json()


def generate(client: TestClient, **overrides: str) -> dict:
    response = client.post("/api/v1/generate", json=generation_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def count(db_session: Session, model: type) -> int:
    return db_session.scalar(select(func.count()).select_from(model)) or 0


@pytest.fixture
def guest(anon_client: TestClient) -> TestClient:
    start_guest(anon_client)
    return anon_client


@pytest.fixture
def other_guest(anon_client: TestClient) -> Iterator[TestClient]:
    with TestClient(app) as browser:
        start_guest(browser)
        yield browser


@pytest.fixture
def registered(anon_client: TestClient) -> Iterator[TestClient]:
    with TestClient(app) as browser:
        register(browser)
        yield browser


# --- Entering as a guest ------------------------------------------------------------------------


def test_enter_as_guest_creates_a_backend_session(anon_client: TestClient, db_session: Session) -> None:
    response = anon_client.post(f"{AUTH}/guest")

    assert response.status_code == 201
    body = response.json()
    assert body["is_guest"] is True
    assert (body["name"], body["email"], body["username"]) == ("Invitado", None, None)
    cookies = SimpleCookie()
    for header in response.headers.get_list("set-cookie"):
        cookies.load(header)
    assert cookies[COOKIE]["httponly"]
    assert cookies[COOKIE]["samesite"].lower() == "lax"
    assert abs(int(cookies[COOKIE]["max-age"]) - 24 * 3600) <= 5  # shorter than a registered session
    assert anon_client.get(f"{AUTH}/me").json()["is_guest"] is True
    stored = db_session.scalar(select(User))
    assert stored is not None and stored.is_guest and stored.password_hash is None


def test_entering_again_keeps_the_same_guest(guest: TestClient, db_session: Session) -> None:
    first = guest.get(f"{AUTH}/me").json()

    second = start_guest(guest)

    assert second["id"] == first["id"]
    assert count(db_session, User) == 1


def test_guest_mode_can_be_disabled(anon_client: TestClient, test_settings: Settings) -> None:
    test_settings.guest_mode_enabled = False

    response = anon_client.post(f"{AUTH}/guest")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "guest_mode_disabled"
    assert 'id="guest-button"' not in anon_client.get("/login").text


def test_guest_entry_is_protected_against_cross_site_requests(anon_client: TestClient) -> None:
    response = anon_client.post(f"{AUTH}/guest", headers={"Origin": "https://evil.example"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


def test_guests_cannot_log_in_with_credentials(guest: TestClient) -> None:
    for identifier in ("Invitado", "invitado", "@"):
        response = guest.post(f"{AUTH}/login", json={"identifier": identifier, "password": "anything"})
        assert response.status_code in {401, 422}


def test_registered_accounts_keep_their_credentials_in_the_database(db_session: Session) -> None:
    db_session.add(User(name="Sin credenciales", is_guest=False))

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# --- Using the generator as a guest -----------------------------------------------------------


def test_guest_can_generate(guest: TestClient, fake_ai_provider: FakeAIProvider) -> None:
    body = generate(guest)

    assert body["generated_content"] == fake_ai_provider.content
    assert len(fake_ai_provider.prompts) == 1


def test_guest_lists_and_reads_only_their_generations(guest: TestClient, other_guest: TestClient) -> None:
    own = generate(guest, customer="Cliente del invitado 1")
    generate(other_guest, customer="Cliente del invitado 2")

    listing = guest.get(GENERATIONS).json()

    assert [item["customer"] for item in listing["items"]] == ["Cliente del invitado 1"]
    assert guest.get(f"{GENERATIONS}/{own['id']}").json() == own


def test_guest_can_edit_and_delete_their_generations(guest: TestClient) -> None:
    created = generate(guest)

    updated = guest.put(f"{GENERATIONS}/{created['id']}", json=generation_payload(customer="Editado"))
    deleted = guest.delete(f"{GENERATIONS}/{created['id']}")

    assert updated.status_code == 200 and updated.json()["customer"] == "Editado"
    assert deleted.status_code == 204
    assert guest.get(GENERATIONS).json()["total"] == 0


def assert_no_access(intruder: TestClient, owner: TestClient, generation: dict, provider: FakeAIProvider) -> None:
    calls = len(provider.prompts)
    url = f"{GENERATIONS}/{generation['id']}"

    assert intruder.get(url).status_code == 404
    assert intruder.put(url, json=generation_payload(customer="Intruso")).status_code == 404
    assert intruder.delete(url).status_code == 404
    assert intruder.get(GENERATIONS).json()["total"] == 0
    assert len(provider.prompts) == calls  # no AI call for someone else's id
    assert owner.get(url).json() == generation


def test_guest_cannot_access_another_guests_data(
    guest: TestClient, other_guest: TestClient, fake_ai_provider: FakeAIProvider
) -> None:
    assert_no_access(other_guest, guest, generate(guest), fake_ai_provider)


def test_guest_cannot_access_a_registered_users_data(
    guest: TestClient, registered: TestClient, fake_ai_provider: FakeAIProvider
) -> None:
    assert_no_access(guest, registered, generate(registered), fake_ai_provider)


def test_registered_user_cannot_access_a_guests_data(
    guest: TestClient, registered: TestClient, fake_ai_provider: FakeAIProvider
) -> None:
    assert_no_access(registered, guest, generate(guest), fake_ai_provider)


def test_registered_user_cannot_access_another_registered_users_data(
    registered: TestClient, fake_ai_provider: FakeAIProvider
) -> None:
    with TestClient(app) as ana:
        register(ana, name="Ana Ruiz", email="ana@example.com")
        assert_no_access(ana, registered, generate(registered), fake_ai_provider)


# --- Guest limits --------------------------------------------------------------------------------


def test_guest_generation_limit(
    guest: TestClient, test_settings: Settings, fake_ai_provider: FakeAIProvider
) -> None:
    test_settings.guest_max_generations = 2
    created = generate(guest)
    assert guest.put(f"{GENERATIONS}/{created['id']}", json=generation_payload()).status_code == 200  # counts too
    guest.delete(f"{GENERATIONS}/{created['id']}")  # deleting does not give calls back
    calls = len(fake_ai_provider.prompts)

    response = guest.post("/api/v1/generate", json=generation_payload())

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "guest_quota_exceeded"
    assert len(fake_ai_provider.prompts) == calls  # the limit is checked before calling the AI


def test_registered_users_have_no_generation_limit(registered: TestClient, test_settings: Settings) -> None:
    test_settings.guest_max_generations = 1

    for _ in range(3):
        generate(registered)


def test_guest_cannot_use_account_features(guest: TestClient) -> None:
    response = guest.post(
        f"{AUTH}/change-password",
        json={"current_password": "x", "new_password": "new-password-1", "new_password_confirm": "new-password-1"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "guest_not_allowed"
    account = guest.get("/account", follow_redirects=False)
    assert (account.status_code, account.headers["location"]) == (303, "/app")


# --- Leaving guest mode ---------------------------------------------------------------------------


def test_guest_logout_deletes_the_guest_and_its_generations(guest: TestClient, db_session: Session) -> None:
    generate(guest)
    generate(guest)
    old_cookie = guest.cookies.get(COOKIE)

    response = guest.post(f"{AUTH}/logout")

    assert response.status_code == 204
    assert (count(db_session, User), count(db_session, Generation), count(db_session, UserSession)) == (0, 0, 0)
    guest.cookies.set(COOKIE, old_cookie)
    assert guest.get(GENERATIONS).status_code == 401


def test_guest_logout_does_not_touch_other_users(
    guest: TestClient, other_guest: TestClient, registered: TestClient, db_session: Session
) -> None:
    generate(guest)
    generate(other_guest)
    generate(registered)

    guest.post(f"{AUTH}/logout")

    assert other_guest.get(GENERATIONS).json()["total"] == 1
    assert registered.get(GENERATIONS).json()["total"] == 1
    assert count(db_session, User) == 2


def expire_sessions_of(db_session: Session, user_id: int) -> None:
    for user_session in db_session.scalars(select(UserSession).where(UserSession.user_id == user_id)):
        user_session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()


def test_expired_guests_are_purged_when_a_new_guest_starts(
    guest: TestClient, registered: TestClient, db_session: Session
) -> None:
    old_guest = guest.get(f"{AUTH}/me").json()
    generate(guest)
    member = registered.get(f"{AUTH}/me").json()
    expire_sessions_of(db_session, old_guest["id"])
    expire_sessions_of(db_session, member["id"])  # registered accounts are never purged

    with TestClient(app) as newcomer:
        start_guest(newcomer)

    db_session.expire_all()
    assert db_session.get(User, old_guest["id"]) is None
    assert count(db_session, Generation) == 0
    assert db_session.get(User, member["id"]) is not None


def test_purge_command_deletes_expired_guests(guest: TestClient, db_session: Session) -> None:
    guest_id = guest.get(f"{AUTH}/me").json()["id"]
    generate(guest)
    expire_sessions_of(db_session, guest_id)

    assert purge_expired_guests(db_session) == 1
    assert count(db_session, Generation) == 0


def test_registering_from_a_guest_session_keeps_the_generations(guest: TestClient, db_session: Session) -> None:
    guest_id = guest.get(f"{AUTH}/me").json()["id"]
    created = generate(guest, customer="Probado como invitado")

    account = register(guest)

    assert account["is_guest"] is False
    listing = guest.get(GENERATIONS).json()
    assert [item["id"] for item in listing["items"]] == [created["id"]]
    db_session.expire_all()
    assert db_session.get(User, guest_id) is None


def test_logging_in_from_a_guest_session_keeps_the_generations(anon_client: TestClient) -> None:
    with TestClient(app) as setup:
        register(setup, username="maria")
    start_guest(anon_client)
    created = generate(anon_client)

    response = anon_client.post(f"{AUTH}/login", json={"identifier": "maria", "password": PASSWORD})

    assert response.status_code == 200
    assert anon_client.get(f"{GENERATIONS}/{created['id']}").status_code == 200


def test_a_guest_cookie_cannot_be_merged_into_someone_elses_login(
    guest: TestClient, other_guest: TestClient
) -> None:
    # Each browser only ever carries its own cookie: the merge only takes the caller's guest.
    created = generate(other_guest)

    register(guest)

    assert guest.get(f"{GENERATIONS}/{created['id']}").status_code == 404
    assert other_guest.get(f"{GENERATIONS}/{created['id']}").status_code == 200


# --- Interface --------------------------------------------------------------------------------------


def test_login_page_offers_guest_access(anon_client: TestClient) -> None:
    page = anon_client.get("/login").text

    assert 'id="guest-button"' in page
    assert "Probar sin registrarse" in page
    assert 'placeholder="Usuario o email"' in page
    assert 'placeholder="Contraseña"' in page
    assert '<span class="button-label">Entrar</span>' in page


def test_app_shows_guest_mode(guest: TestClient) -> None:
    page = guest.get("/app").text

    assert 'id="guest-menu"' in page
    assert "Modo invitado" in page
    assert 'href="/login"' in page and 'href="/register"' in page
    assert 'href="/account"' not in page
    assert 'id="user-menu"' not in page
    assert 'id="guest-notice"' in page
    assert 'data-confirm="Al salir del modo invitado' in page


def test_guest_can_open_login_and_register_pages(guest: TestClient) -> None:
    login_page = guest.get("/login", follow_redirects=False)
    register_page = guest.get("/register", follow_redirects=False)

    assert login_page.status_code == 200 and register_page.status_code == 200
    assert "Seguir como invitado" in login_page.text
    assert 'id="guest-button"' not in login_page.text
    assert "Tus generaciones se guardarán en tu nueva cuenta" in register_page.text


# --- Usernames and normal login still work ------------------------------------------------------------


def test_login_with_username_or_email(anon_client: TestClient) -> None:
    register(anon_client, username="Maria.Lopez")
    anon_client.post(f"{AUTH}/logout")

    by_username = anon_client.post(f"{AUTH}/login", json={"identifier": "maria.lopez", "password": PASSWORD})
    anon_client.post(f"{AUTH}/logout")
    by_email = anon_client.post(f"{AUTH}/login", json={"identifier": "maria@example.com", "password": PASSWORD})
    anon_client.post(f"{AUTH}/logout")
    legacy_key = anon_client.post(f"{AUTH}/login", json={"email": "maria@example.com", "password": PASSWORD})

    assert [r.status_code for r in (by_username, by_email, legacy_key)] == [200, 200, 200]
    assert by_username.json()["username"] == "maria.lopez"


def test_duplicate_username_returns_409(anon_client: TestClient) -> None:
    register(anon_client, username="maria")

    with TestClient(app) as other:
        response = other.post(
            f"{AUTH}/register",
            json={
                "name": "Otra",
                "email": "otra@example.com",
                "username": "MARIA",
                "password": PASSWORD,
                "password_confirm": PASSWORD,
            },
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "username_already_taken"


@pytest.mark.parametrize("username", ["ab", "con espacio", "maria@x", "x" * 31])
def test_invalid_usernames_are_rejected(anon_client: TestClient, username: str) -> None:
    response = anon_client.post(
        f"{AUTH}/register",
        json={"name": "M", "email": "m@example.com", "username": username, "password": PASSWORD, "password_confirm": PASSWORD},
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "username"


def test_registration_without_username_still_works(anon_client: TestClient) -> None:
    body = register(anon_client, username="")

    assert body["username"] is None
