"""Interface translations: catalogs, the language switch and pages fully rendered in every language."""

import html
import re
import string
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.i18n import CATALOGS, LANGUAGE_COOKIE, SUPPORTED_LANGUAGES, js_messages
from app.i18n.en import MESSAGES as EN
from app.i18n.es import MESSAGES as ES

# Every language other than Spanish (the source catalog).
TRANSLATIONS = [code for code in SUPPORTED_LANGUAGES if code != "es"]

ROOT = Path(__file__).resolve().parents[1]
JS_DIR = ROOT / "app" / "static" / "js"
# t("js.key", "Spanish fallback", ...) in the JavaScript modules.
JS_CALL = re.compile(r't\(\s*"(js\.[\w.]+)",\s*"((?:[^"\\]|\\.)*)"')
SCRIPT = re.compile(r"<script\b.*?</script>", re.DOTALL)


def placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def js_calls() -> list[tuple[str, str, str]]:
    return [
        (path.name, key, fallback)
        for path in sorted(JS_DIR.glob("*.js"))
        for key, fallback in JS_CALL.findall(path.read_text(encoding="utf-8"))
    ]


# --- Catalogs -----------------------------------------------------------------------------------


def test_every_catalog_has_the_same_keys() -> None:
    for language, catalog in CATALOGS.items():
        assert catalog.keys() == ES.keys(), (language, sorted(catalog.keys() ^ ES.keys()))


@pytest.mark.parametrize("language", TRANSLATIONS)
def test_translations_keep_the_same_placeholders(language: str) -> None:
    catalog = CATALOGS[language]
    assert [key for key in ES if placeholders(catalog[key]) != placeholders(ES[key])] == []


@pytest.mark.parametrize("language", TRANSLATIONS)
def test_translation_is_not_a_copy_of_the_spanish_catalog(language: str) -> None:
    # Brand names, formats and loan words may match; real sentences may not.
    brand_and_formats = {"brand.name", "footer.copyright", "auth.login.demo_hint", "js.error.http"}
    catalog = CATALOGS[language]
    same = {key for key in ES if ES[key] == catalog[key] and len(ES[key].split()) > 2}
    assert same <= brand_and_formats


FOOTER_KEYS = ("contact", "legal", "privacy", "social.email", "social.whatsapp", "social.github")


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("en", ["Contact", "Legal Notice", "Privacy", "Email", "WhatsApp", "GitHub"]),
        ("pt", ["Contacto", "Aviso Legal", "Privacidade", "E-mail", "WhatsApp", "GitHub"]),
        ("fr", ["Contact", "Mentions Légales", "Confidentialité", "E-mail", "WhatsApp", "GitHub"]),
    ],
)
def test_footer_texts(language: str, expected: list[str]) -> None:
    assert [CATALOGS[language][f"footer.{key}"] for key in FOOTER_KEYS] == expected


def test_js_fallbacks_are_the_spanish_catalog_texts() -> None:
    calls = js_calls()
    assert calls, "no t() calls found in static/js"
    for file, key, fallback in calls:
        assert key in ES, (file, key)
        assert ES[key] == fallback, (file, key)


def test_every_js_text_in_the_catalog_is_used() -> None:
    used = {key for _, key, _ in js_calls()} | {
        # Rendered by index.html with t(): shared with the JavaScript so both say the same.
        key for key in ES if key.startswith("js.") and re.search(rf"""t\(\s*["']{re.escape(key)}["']""", (ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8"))
    }
    assert {key for key in ES if key.startswith("js.")} == used


def test_js_messages_only_carry_the_javascript_texts() -> None:
    messages = js_messages("en")

    assert messages.keys() == {key for key in ES if key.startswith("js.")}
    assert messages["js.gen.submit"] == "Generate with AI"
    assert js_messages("xx")["js.gen.submit"] == "Generar con IA"


# --- Language switch ------------------------------------------------------------------------------


def test_language_route_stores_the_choice_and_goes_back(anon_client: TestClient) -> None:
    response = anon_client.get("/language/en", params={"next": "/contacto"}, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/contacto"
    cookie = response.headers["set-cookie"]
    assert f"{LANGUAGE_COOKIE}=en" in cookie and "SameSite=lax" in cookie and "Max-Age=31536000" in cookie
    assert '<html lang="en">' in anon_client.get("/contacto").text


def test_language_route_ignores_unknown_languages_and_foreign_redirects(anon_client: TestClient) -> None:
    response = anon_client.get("/language/xx", params={"next": "https://evil.example"}, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/app"
    assert "set-cookie" not in response.headers


def test_switching_back_to_spanish(anon_client: TestClient) -> None:
    anon_client.get("/language/en", params={"next": "/login"})
    page = anon_client.get("/language/es", params={"next": "/login"}).text

    assert '<html lang="es">' in page and "Iniciar sesión" in page


def test_selector_marks_english_and_links_back_to_the_same_page(anon_client: TestClient) -> None:
    anon_client.cookies.set(LANGUAGE_COOKIE, "en")

    page = anon_client.get("/legal").text
    selector = page.split('id="language-selector"')[1].split("</div>")[0]

    assert re.search(r">\s*EN\s*</button>", selector)
    assert 'aria-label="Current language: English"' in selector
    assert 'class="dropdown-item active" lang="en"' in selector
    assert 'href="/language/es?next=%2Flegal"' in selector


def test_selector_never_copies_the_query_string(anon_client: TestClient) -> None:
    # The reset link carries a secret token in its query: the selector only returns to the path.
    page = anon_client.get("/reset-password", params={"token": "secret-reset-token"}).text

    assert "secret-reset-token" not in page
    assert 'href="/language/en?next=%2Freset-password"' in page


def test_app_header_has_the_language_selector(client: TestClient) -> None:
    assert 'id="language-selector"' in client.get("/app").text


# --- Pages rendered in English contain no Spanish interface text ------------------------------------

def spanish_only(language: str) -> list[str]:
    """Spanish catalog texts that must not appear on a page rendered in `language`.

    Texts that also appear inside one of that language's texts (e.g. "Legal" in "Legal Notice",
    "Contacto" in Portuguese) or are the same word in both cannot reveal an untranslated text, so
    they are not checked. Nor are the language names, which the selector always shows in their own
    language ("Español").
    """
    catalog = CATALOGS[language]
    return sorted(
        {
            fragment.strip()
            for key, text in ES.items()
            if text != catalog[key] and text not in SUPPORTED_LANGUAGES.values()
            for fragment in re.split(r"\{\w+\}", text)
            if len(fragment.strip()) >= 4 and not any(fragment.strip() in own for own in catalog.values())
        }
    )


def assert_no_spanish(page: str, language: str, *, user_data: tuple[str, ...] = ()) -> None:
    # The JSON for the JavaScript is checked separately (js_messages); everything else is the page,
    # except data typed by the user (e.g. the account name "María López" in the header).
    visible = html.unescape(SCRIPT.sub("", page))
    for value in user_data:
        visible = visible.replace(value, "")
    found = [text for text in spanish_only(language) if text in visible]
    assert found == []


@pytest.mark.parametrize("language", TRANSLATIONS)
@pytest.mark.parametrize(
    "path", ["/login", "/register", "/forgot-password", "/reset-password", "/contacto", "/legal", "/privacidad"]
)
def test_public_and_access_pages_are_translated(anon_client: TestClient, path: str, language: str) -> None:
    anon_client.cookies.set(LANGUAGE_COOKIE, language)

    page = anon_client.get(path).text

    assert f'<html lang="{language}">' in page
    assert_no_spanish(page, language)


@pytest.mark.parametrize("language", TRANSLATIONS)
@pytest.mark.parametrize("path", ["/app", "/account"])
def test_application_pages_are_translated(client: TestClient, path: str, language: str) -> None:
    client.cookies.set(LANGUAGE_COOKIE, language)

    page = client.get(path).text

    assert_no_spanish(page, language, user_data=("María López",))


@pytest.mark.parametrize("language", TRANSLATIONS)
def test_guest_app_page_is_translated(anon_client: TestClient, language: str) -> None:
    anon_client.post("/api/v1/auth/guest")
    anon_client.cookies.set(LANGUAGE_COOKIE, language)

    page = anon_client.get("/app").text

    t = CATALOGS[language]
    assert t["app.guest_badge"] in page and t["app.guest_logout"] in page
    assert_no_spanish(page, language)


@pytest.mark.parametrize(
    ("language", "title", "submit", "content_type"),
    [
        ("pt", "Nova geração", "Gerar com IA", "E-mail comercial"),
        ("fr", "Nouvelle génération", "Générer avec l&#39;IA", "E-mail commercial"),
    ],
)
def test_generator_in_portuguese_and_french(client: TestClient, language: str, title: str, submit: str, content_type: str) -> None:
    client.cookies.set(LANGUAGE_COOKIE, language)

    page = client.get("/app").text

    assert f'<html lang="{language}">' in page
    assert f'<h2 id="form-title" class="h5 mb-3">{title}</h2>' in page
    assert f'<span class="button-label">{submit}</span>' in page
    assert f'<option value="commercial_email">{content_type}</option>' in page


def test_login_messages_rendered_by_the_server_in_english(anon_client: TestClient) -> None:
    anon_client.cookies.set(LANGUAGE_COOKIE, "en")

    assert "You have signed out." in anon_client.get("/login", params={"notice": "logged_out"}).text
    page = anon_client.post("/login", data={"identifier": "nobody@example.com", "password": "wrong-password"}).text
    assert "Incorrect username or password." in page


def test_english_page_carries_the_english_javascript_texts(client: TestClient) -> None:
    client.cookies.set(LANGUAGE_COOKIE, "en")

    page = client.get("/app").text
    data = re.search(r'<script id="i18n-messages" type="application/json">(.*?)</script>', page, re.DOTALL)

    assert data and '"js.gen.submit": "Generate with AI"' in data.group(1)
    # Selects show the options in English; the values sent to the API do not change.
    assert '<option value="commercial_email">Sales email</option>' in page
    assert '<option value="en">English</option>' in page
