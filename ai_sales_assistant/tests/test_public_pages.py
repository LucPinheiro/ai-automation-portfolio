"""Public pages (/contacto, /legal, /privacidad) and the shared footer."""

import re

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database.types import utc_now
from app.main import app

PAGES = {
    "/contacto": "Contacto y soporte",
    "/legal": "Aviso legal",
    "/privacidad": "Política de privacidad",
}


@pytest.mark.parametrize(("path", "title"), PAGES.items())
def test_public_pages_need_no_session(anon_client: TestClient, path: str, title: str) -> None:
    response = anon_client.get(path)

    assert response.status_code == 200
    assert f'<h1 class="public-title">{title}</h1>' in response.text
    assert f"<title>{title} · AI Sales Assistant</title>" in response.text
    assert '<html lang="es">' in response.text


@pytest.mark.parametrize("path", PAGES)
def test_public_pages_also_work_logged_in(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 200
    assert "Ir a la aplicación" in response.text


@pytest.mark.parametrize("path", ["/legal", "/privacidad"])
def test_legal_pages_invent_no_legal_data(anon_client: TestClient, path: str) -> None:
    page = anon_client.get(path).text
    body = page.split('<main class="public-main">')[1].split("</main>")[0]

    sections = re.findall(r'<section class="public-section"', body)
    assert len(sections) >= 6
    assert body.count("Pendiente de completar.") == len(sections)
    for invented in ("CIF", "NIF", "S.L.", "S.A.", "@", "Calle", "C/", "+34", "Registro Mercantil"):
        assert invented not in body, invented


def test_legal_page_structure(anon_client: TestClient) -> None:
    page = anon_client.get("/legal").text

    for heading in ("Titular del sitio web", "Condiciones de uso", "Propiedad intelectual e industrial", "Legislación aplicable"):
        assert f"<h2>{heading}</h2>" in page


def test_privacy_page_structure(anon_client: TestClient) -> None:
    page = anon_client.get("/privacidad").text

    for heading in ("Responsable del tratamiento", "Finalidad del tratamiento", "Base jurídica", "Derechos de las personas usuarias"):
        assert f"<h2>{heading}</h2>" in page


def test_contact_page_without_support_email(anon_client: TestClient, test_settings: Settings) -> None:
    test_settings.support_email = None
    test_settings.support_phone = None

    page = anon_client.get("/contacto").text

    assert "Próximamente publicaremos aquí el email de soporte." in page
    assert "Próximamente publicaremos aquí el teléfono de soporte." in page
    assert "mailto:" not in page and "tel:" not in page
    assert 'href="/docs"' in page
    assert "Nunca envíes contraseñas, tokens, claves de API ni claves privadas." in page


def test_contact_page_shows_the_configured_support_email(anon_client: TestClient, test_settings: Settings) -> None:
    test_settings.support_email = "soporte@example.com"

    page = anon_client.get("/contacto").text

    assert '<a href="mailto:soporte@example.com">soporte@example.com</a>' in page
    assert "Próximamente publicaremos aquí el email de soporte." not in page


def test_public_pages_are_not_part_of_the_api_docs() -> None:
    paths = app.openapi()["paths"]

    assert not {"/contacto", "/legal", "/privacidad"} & paths.keys()


# --- Footer -------------------------------------------------------------------------------------


def footer(page: str) -> str:
    match = re.search(r'<footer class="site-footer">.*?</footer>', page, re.DOTALL)
    assert match, "footer not found"
    return match.group(0)


@pytest.mark.parametrize("path", ["/login", "/register", "/forgot-password", "/reset-password", "/contacto", "/legal", "/privacidad"])
def test_footer_on_public_and_access_screens(anon_client: TestClient, path: str) -> None:
    html = footer(anon_client.get(path).text)

    assert f"© {utc_now().year} AI Sales Assistant" in html
    assert '<a href="/contacto">Contacto</a>' in html
    assert '<a href="/legal">Legal</a>' in html
    assert '<a href="/privacidad">Privacidad</a>' in html


@pytest.mark.parametrize("path", ["/app", "/account"])
def test_footer_inside_the_application(client: TestClient, path: str) -> None:
    html = footer(client.get(path).text)

    assert '<a href="/contacto">Contacto</a>' in html


def footer_contacts(html: str) -> dict[str, str]:
    return dict(re.findall(r'data-footer-contact="(\w+)" href="([^"]+)"', html))


@pytest.mark.parametrize("path", ["/login", "/contacto", "/privacidad"])
def test_footer_contact_buttons_on_public_and_access_screens(anon_client: TestClient, path: str) -> None:
    html = footer(anon_client.get(path).text)

    assert footer_contacts(html) == {
        "email": "mailto:soporte@aisalesassistant.demo",
        "whatsapp": "https://wa.me/34600123456",
        "github": "https://github.com/LucPinheiro",
    }
    for label in ("Correo electrónico", "WhatsApp", "GitHub"):
        assert f"<span>{label}</span>" in html
    assert html.count('target="_blank" rel="noopener noreferrer"') == 2  # WhatsApp and GitHub, not mailto
    assert html.count('class="footer-social-icon"') == 3


@pytest.mark.parametrize("path", ["/app", "/account"])
def test_footer_contact_buttons_inside_the_application(client: TestClient, path: str) -> None:
    assert footer_contacts(footer(client.get(path).text)).keys() == {"email", "whatsapp", "github"}


def test_footer_hides_contact_buttons_without_a_value(anon_client: TestClient, test_settings: Settings) -> None:
    test_settings.support_phone = None
    test_settings.github_url = None

    html = footer(anon_client.get("/login").text)

    assert footer_contacts(html).keys() == {"email"}

    test_settings.support_email = None
    assert "site-footer-social" not in footer(anon_client.get("/login").text)
