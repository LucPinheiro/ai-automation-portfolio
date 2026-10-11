import pytest
from fastapi.testclient import TestClient

from app.core.middleware import origin_of
from app.routers.web import safe_next_path
from tests.factories import generation_payload, register_payload

# --- CSRF (Origin check) ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "https://evil.example"},
        {"Origin": "null"},
        {"Referer": "https://evil.example/attack.html"},
        {"Origin": "http://testserver.evil.example"},
    ],
)
def test_cross_site_writes_are_rejected(client: TestClient, headers: dict) -> None:
    response = client.post("/api/v1/generate", json=generation_payload(), headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"
    assert client.get("/api/v1/generations").json()["total"] == 0


@pytest.mark.parametrize("method", ["put", "delete"])
def test_cross_site_update_and_delete_are_rejected(client: TestClient, method: str) -> None:
    created = client.post("/api/v1/generate", json=generation_payload()).json()
    kwargs = {"json": generation_payload()} if method == "put" else {}

    response = client.request(
        method.upper(), f"/api/v1/generations/{created['id']}", headers={"Origin": "https://evil.example"}, **kwargs
    )

    assert response.status_code == 403
    assert client.get(f"/api/v1/generations/{created['id']}").json() == created


def test_cross_site_login_and_logout_are_rejected(client: TestClient) -> None:
    evil = {"Origin": "https://evil.example"}

    assert client.post("/api/v1/auth/logout", headers=evil).status_code == 403
    assert client.get("/api/v1/auth/me").status_code == 200  # still logged in
    assert client.post("/api/v1/auth/register", json=register_payload(email="x@example.com"), headers=evil).status_code == 403


def test_same_origin_writes_are_allowed(client: TestClient) -> None:
    response = client.post(
        "/api/v1/generate", json=generation_payload(), headers={"Origin": "http://testserver"}
    )

    assert response.status_code == 201


def test_cross_site_reads_are_not_blocked_by_the_origin_check(client: TestClient) -> None:
    # Reads change nothing; the browser's same-origin policy keeps the response from the other site.
    assert client.get("/api/v1/generations", headers={"Origin": "https://evil.example"}).status_code == 200


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("http://127.0.0.1:8000/app", "http://127.0.0.1:8000"),
        ("HTTPS://Example.COM", "https://example.com"),
        ("null", None),
        ("", None),
    ],
)
def test_origin_of(url: str, expected: str | None) -> None:
    assert origin_of(url) == expected


def test_security_headers_are_set(anon_client: TestClient) -> None:
    response = anon_client.get("/login")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "same-origin"


# --- Pages and redirects ------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/app", "/account"])
def test_protected_pages_redirect_to_login(anon_client: TestClient, path: str) -> None:
    response = anon_client.get(path, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == f"/login?next=%2F{path[1:]}"


def test_protected_pages_render_for_a_logged_in_user(client: TestClient) -> None:
    app_page = client.get("/app")
    account_page = client.get("/account")

    assert app_page.status_code == 200
    assert account_page.status_code == 200
    assert "maria@example.com" in account_page.text
    assert 'id="change-password-form"' in account_page.text
    assert account_page.headers["Cache-Control"] == "no-store"


def test_header_shows_the_logged_in_user_and_logout(client: TestClient) -> None:
    page = client.get("/app").text

    assert 'id="user-menu"' in page
    assert "María López" in page
    assert 'id="logout-button"' in page
    assert 'href="/account"' in page
    assert "/static/js/session.js" in page


@pytest.mark.parametrize(
    ("path", "form_id", "fields"),
    [
        ("/login", "login-form", ["identifier", "password"]),
        ("/register", "register-form", ["name", "email", "password", "password_confirm"]),
        ("/forgot-password", "forgot-form", ["email"]),
        ("/reset-password", "reset-form", ["new_password", "new_password_confirm"]),
    ],
)
def test_auth_pages_render_their_forms(anon_client: TestClient, path: str, form_id: str, fields: list[str]) -> None:
    response = anon_client.get(path)

    assert response.status_code == 200
    assert f'id="{form_id}"' in response.text
    for name in fields:
        assert f'name="{name}"' in response.text
    assert 'id="user-menu"' not in response.text
    assert "/static/js/auth.js" in response.text


def test_password_inputs_carry_the_api_limits(anon_client: TestClient) -> None:
    page = anon_client.get("/register").text

    assert 'name="password" type="password"' in page
    assert 'minlength="8"' in page
    assert 'maxlength="128"' in page


def test_reset_page_never_leaks_its_token(anon_client: TestClient) -> None:
    response = anon_client.get("/reset-password", params={"token": "secret-reset-token"})

    assert "secret-reset-token" not in response.text
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cache-Control"] == "no-store"


def test_login_page_redirects_a_logged_in_user(client: TestClient) -> None:
    response = client.get("/login", params={"next": "/account"}, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/account"


def test_login_page_keeps_a_safe_next_path(anon_client: TestClient) -> None:
    page = anon_client.get("/login", params={"next": "/account"}).text

    assert 'data-next="/account"' in page


@pytest.mark.parametrize("notice", ["logged_out", "password_reset", "session_expired"])
def test_login_page_shows_known_notices(anon_client: TestClient, notice: str) -> None:
    page = anon_client.get("/login", params={"notice": notice}).text

    assert "alert alert-info" in page


def test_login_page_ignores_unknown_notices(anon_client: TestClient) -> None:
    page = anon_client.get("/login", params={"notice": "<script>alert(1)</script>"}).text

    assert "alert(1)" not in page
    assert "alert alert-info" not in page


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("/app", "/app"),
        ("/account?tab=1", "/account?tab=1"),
        (None, "/app"),
        ("", "/app"),
        ("https://evil.example", "/app"),
        ("//evil.example", "/app"),
        ("/\\evil.example", "/app"),
        ("javascript:alert(1)", "/app"),
    ],
)
def test_safe_next_path_blocks_open_redirects(value: str | None, expected: str) -> None:
    assert safe_next_path(value) == expected


def test_swagger_and_root_stay_public(anon_client: TestClient) -> None:
    assert anon_client.get("/docs").status_code == 200
    assert anon_client.get("/").status_code == 200
    assert anon_client.get("/health").status_code == 200
