"""Demo credentials (demo / demo123) and the HTML form fallbacks for login and guest access."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.main import app
from app.models import Generation, User
from tests.factories import PASSWORD, generation_payload, register

AUTH = "/api/v1/auth"
BROWSER = {"Origin": "http://testserver"}  # what a real browser sends with a same-site POST
DEMO = {"identifier": "demo", "password": "demo123"}


def api_demo_login(client: TestClient, **overrides: str):
    return client.post(f"{AUTH}/login", json=DEMO | overrides, headers=BROWSER)


def form_post(client: TestClient, path: str, data: dict | None = None, headers: dict | None = None):
    return client.post(path, data=data or {}, headers=headers or BROWSER, follow_redirects=False)


def users(db_session: Session) -> int:
    return db_session.scalar(select(func.count()).select_from(User)) or 0


@pytest.fixture
def second_browser(anon_client: TestClient) -> Iterator[TestClient]:
    with TestClient(app) as browser:
        yield browser


# --- A) demo / demo123 through the API (what auth.js calls) --------------------------------------------


def test_demo_credentials_open_a_guest_session(anon_client: TestClient, db_session: Session) -> None:
    response = api_demo_login(anon_client)

    assert response.status_code == 200
    assert response.json()["is_guest"] is True
    assert "httponly" in response.headers["set-cookie"].lower()
    assert anon_client.get(f"{AUTH}/me").json()["is_guest"] is True
    # Not an account: no stored email, username or password for the demo.
    stored = db_session.scalar(select(User))
    assert (stored.email, stored.username, stored.password_hash) == (None, None, None)


def test_demo_username_is_case_insensitive(anon_client: TestClient) -> None:
    assert api_demo_login(anon_client, identifier="  DEMO ").status_code == 200


@pytest.mark.parametrize(
    "credentials",
    [
        {"identifier": "demo", "password": "demo1234"},
        {"identifier": "demo", "password": "DEMO123"},
        {"identifier": "demo2", "password": "demo123"},
        {"identifier": "demo@example.com", "password": "demo123"},
    ],
)
def test_wrong_demo_credentials_do_not_enter(anon_client: TestClient, db_session: Session, credentials: dict) -> None:
    response = anon_client.post(f"{AUTH}/login", json=credentials, headers=BROWSER)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"
    assert anon_client.get(f"{AUTH}/me").status_code == 401
    assert users(db_session) == 0


@pytest.mark.parametrize("setting", ["demo_login_enabled", "guest_mode_enabled"])
def test_demo_credentials_can_be_disabled(anon_client: TestClient, test_settings: Settings, setting: str) -> None:
    setattr(test_settings, setting, False)

    assert api_demo_login(anon_client).status_code == 401


def test_demo_username_cannot_be_registered(anon_client: TestClient) -> None:
    response = anon_client.post(
        f"{AUTH}/register",
        json={"name": "X", "email": "x@example.com", "username": "Demo", "password": PASSWORD, "password_confirm": PASSWORD},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "username_already_taken"


def test_each_demo_visitor_gets_a_separate_guest(
    anon_client: TestClient, second_browser: TestClient, db_session: Session
) -> None:
    first = api_demo_login(anon_client).json()
    second = api_demo_login(second_browser).json()

    assert first["id"] != second["id"]
    created = anon_client.post("/api/v1/generate", json=generation_payload(), headers=BROWSER).json()
    # Same public credentials, but no access to each other's data.
    assert second_browser.get(f"/api/v1/generations/{created['id']}").status_code == 404
    assert second_browser.put(f"/api/v1/generations/{created['id']}", json=generation_payload()).status_code == 404
    assert second_browser.delete(f"/api/v1/generations/{created['id']}").status_code == 404
    assert second_browser.get("/api/v1/generations").json()["total"] == 0


def test_demo_guest_cannot_access_registered_users_data(anon_client: TestClient, second_browser: TestClient) -> None:
    register(second_browser)
    private = second_browser.post("/api/v1/generate", json=generation_payload()).json()

    api_demo_login(anon_client)

    assert anon_client.get(f"/api/v1/generations/{private['id']}").status_code == 404
    assert anon_client.get("/api/v1/generations").json()["total"] == 0


def test_demo_guest_can_generate_within_the_guest_limit(anon_client: TestClient, test_settings: Settings) -> None:
    test_settings.guest_max_generations = 1
    api_demo_login(anon_client)

    first = anon_client.post("/api/v1/generate", json=generation_payload())
    second = anon_client.post("/api/v1/generate", json=generation_payload())

    assert first.status_code == 201
    assert second.status_code == 403
    assert second.json()["error"]["code"] == "guest_quota_exceeded"


def test_demo_login_again_keeps_the_current_guest(anon_client: TestClient, db_session: Session) -> None:
    first = api_demo_login(anon_client).json()

    second = api_demo_login(anon_client).json()

    assert first["id"] == second["id"]
    assert users(db_session) == 1


def test_demo_logout_deletes_the_guest_data(anon_client: TestClient, db_session: Session) -> None:
    api_demo_login(anon_client)
    anon_client.post("/api/v1/generate", json=generation_payload())

    assert anon_client.post(f"{AUTH}/logout").status_code == 204

    assert users(db_session) == 0
    assert db_session.scalar(select(func.count()).select_from(Generation)) == 0
    assert anon_client.get("/api/v1/generations").status_code == 401


def test_registered_login_still_works_alongside_the_demo(anon_client: TestClient) -> None:
    register(anon_client, username="maria")
    anon_client.post(f"{AUTH}/logout")

    response = anon_client.post(f"{AUTH}/login", json={"identifier": "maria", "password": PASSWORD}, headers=BROWSER)

    assert response.status_code == 200
    assert response.json()["is_guest"] is False


# --- HTML form fallbacks (work even when JavaScript does not run) ------------------------------------


def test_guest_form_post_enters_the_app(anon_client: TestClient) -> None:
    response = form_post(anon_client, "/guest")

    assert response.status_code == 303
    assert response.headers["location"] == "/app"
    assert "httponly" in response.headers["set-cookie"].lower()
    app_page = anon_client.get("/app")
    assert app_page.status_code == 200
    assert 'id="guest-menu"' in app_page.text


def test_guest_form_rejects_cross_site_posts(anon_client: TestClient) -> None:
    response = form_post(anon_client, "/guest", headers={"Origin": "https://evil.example"})

    assert response.status_code == 403
    assert anon_client.get(f"{AUTH}/me").status_code == 401


def test_guest_form_when_guest_mode_is_disabled(anon_client: TestClient, test_settings: Settings) -> None:
    test_settings.guest_mode_enabled = False

    response = form_post(anon_client, "/guest")

    assert (response.status_code, response.headers["location"]) == (303, "/login?notice=guest_disabled")
    assert "no está disponible" in anon_client.get(response.headers["location"]).text


def test_login_form_with_demo_credentials_enters_the_app(anon_client: TestClient) -> None:
    response = form_post(anon_client, "/login", DEMO | {"next": "/account"})

    assert (response.status_code, response.headers["location"]) == (303, "/app")
    assert anon_client.get(f"{AUTH}/me").json()["is_guest"] is True


def test_login_form_with_wrong_credentials_shows_an_error(anon_client: TestClient) -> None:
    response = form_post(anon_client, "/login", {"identifier": "demo", "password": "wrong-secret-xyz"})

    assert response.status_code == 401
    assert "Usuario o contraseña incorrectos." in response.text
    assert 'value="demo"' in response.text  # the user does not have to type it again
    assert "wrong-secret-xyz" not in response.text  # the password is never echoed back
    assert "set-cookie" not in response.headers


def test_login_form_with_missing_fields(anon_client: TestClient) -> None:
    response = form_post(anon_client, "/login", {"identifier": "", "password": ""})

    assert response.status_code == 422
    assert "Usuario o contraseña incorrectos." in response.text


def test_login_form_for_a_registered_user_goes_to_next(anon_client: TestClient) -> None:
    register(anon_client)
    anon_client.post(f"{AUTH}/logout")

    response = form_post(anon_client, "/login", {"identifier": "maria@example.com", "password": PASSWORD, "next": "/account"})

    assert (response.status_code, response.headers["location"]) == (303, "/account")
    assert anon_client.get(f"{AUTH}/me").json()["is_guest"] is False


def test_login_form_never_redirects_off_site(anon_client: TestClient) -> None:
    register(anon_client)
    anon_client.post(f"{AUTH}/logout")

    response = form_post(
        anon_client, "/login", {"identifier": "maria@example.com", "password": PASSWORD, "next": "//evil.example"}
    )

    assert response.headers["location"] == "/app"


def test_login_form_rejects_cross_site_posts(anon_client: TestClient) -> None:
    response = form_post(anon_client, "/login", DEMO, headers={"Origin": "https://evil.example"})

    assert response.status_code == 403


# --- Login page ----------------------------------------------------------------------------------------


def test_login_page_prefills_the_demo_credentials(anon_client: TestClient) -> None:
    page = anon_client.get("/login").text

    assert 'name="identifier"' in page and 'value="demo"' in page
    assert 'value="demo123"' in page
    assert 'id="demo-hint"' in page
    assert '<form id="login-form" class="login-form" method="post" action="/login"' in page
    assert '<form id="guest-form" method="post" action="/guest"' in page
    assert 'id="guest-button" type="submit"' in page


def test_login_page_without_demo_has_empty_fields(anon_client: TestClient, test_settings: Settings) -> None:
    test_settings.demo_login_enabled = False

    page = anon_client.get("/login").text

    assert 'value="demo123"' not in page
    assert 'id="demo-hint"' not in page


def test_own_static_files_are_always_revalidated(anon_client: TestClient) -> None:
    # Prevents browsers from running an outdated auth.js/api.js against newer HTML or API.
    assert anon_client.get("/static/js/auth.js").headers["Cache-Control"] == "no-cache"
    assert anon_client.get("/static/css/app.css").headers["Cache-Control"] == "no-cache"
    assert "cache-control" not in anon_client.get("/static/vendor/bootstrap/bootstrap.min.css").headers
