import re
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.enums import ContentType, Language, Tone
from app.main import app
from app.routers.web import CONTENT_TYPE_LABELS, LANGUAGE_LABELS, MAX_LENGTHS, TONE_LABELS
from app.schemas.generation import GenerationCreate

APP_URL = "/app"
JS_TESTS = Path(__file__).parent / "js"
STATIC_JS = Path(__file__).parent.parent / "app" / "static" / "js"
DELETE_MESSAGE = "¿Seguro que quieres eliminar esta generación? Esta acción no se puede deshacer."


@pytest.fixture
def page(client: TestClient) -> str:
    response = client.get(APP_URL)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    return response.text


def form_html(page: str) -> str:
    match = re.search(r'<form id="generate-form".*?</form>', page, re.DOTALL)
    assert match, "generation form not found"
    return match.group(0)


def select_values(page: str, name: str) -> list[str]:
    match = re.search(rf'<select id="{name}" name="{name}".*?</select>', page, re.DOTALL)
    assert match, f"select {name} not found"
    return re.findall(r'<option value="([^"]+)"', match.group(0))


def test_page_shows_header_and_generate_button(page: str) -> None:
    assert "AI Sales Assistant" in page
    assert "Tu asistente comercial inteligente" in page
    assert "Generar con IA" in page
    assert 'class="brand-mark' in page
    assert 'href="/static/img/logo-mark.svg"' in page


def test_form_fields_match_the_generate_schema(page: str) -> None:
    # Guards against the form drifting from POST /api/v1/generate.
    names = set(re.findall(r'\bname="([^"]+)"', form_html(page)))

    assert names == set(GenerationCreate.model_fields)


@pytest.mark.parametrize(
    ("name", "enum", "labels"),
    [
        ("content_type", ContentType, CONTENT_TYPE_LABELS),
        ("language", Language, LANGUAGE_LABELS),
        ("tone", Tone, TONE_LABELS),
    ],
)
def test_selects_offer_every_api_value(page: str, name: str, enum: type, labels: dict) -> None:
    expected = [member.value for member in enum]

    assert set(labels) == set(enum)
    assert select_values(page, name) == expected


def test_max_lengths_match_the_generate_schema(page: str) -> None:
    form = form_html(page)
    for name, limit in MAX_LENGTHS.items():
        constraint = next(m for m in GenerationCreate.model_fields[name].metadata if hasattr(m, "max_length"))
        assert constraint.max_length == limit
        assert re.search(rf'name="{name}"[^>]*maxlength="{limit}"', form), name


def test_page_uses_local_assets_only(page: str) -> None:
    # The UI must work offline next to a local Ollama: nothing is loaded from another server.
    # Plain links (the footer's WhatsApp and GitHub buttons) and SVG namespaces load nothing.
    assert not re.search(r"""\bsrc=["']?(?:https?:)?//""", page)
    assert not re.search(r"""<link\b[^>]*\bhref=["']?(?:https?:)?//""", page)
    assert not re.search(r"""url\(\s*["']?(?:https?:)?//""", page)
    assert not re.search(r"""@import\s+(?:url\()?\s*["']?(?:https?:)?//""", page)
    external = re.findall(r"""https?://[^"'\s<>)]+""", page)
    assert set(external) <= {"http://www.w3.org/2000/svg", "https://wa.me/34600123456", "https://github.com/LucPinheiro"}


@pytest.mark.parametrize(
    "path",
    [
        "/static/vendor/bootstrap/bootstrap.min.css",
        "/static/vendor/bootstrap/bootstrap.bundle.min.js",
        "/static/css/app.css",
        "/static/js/app.js",
        "/static/js/api.js",
        "/static/js/ui.js",
        "/static/js/markdown.js",
        "/static/js/generation-form.js",
        "/static/js/icons.js",
        "/static/js/auth.js",
        "/static/js/auth-utils.js",
        "/static/js/forms.js",
        "/static/js/session.js",
        "/static/img/logo-mark.svg",
        "/static/img/logo-mark-teal.svg",
        "/static/img/logo-mark-white.svg",
        "/static/img/logo-full-teal.svg",
        "/static/img/logo-full-white.svg",
        "/static/css/brand.css",
    ],
)
def test_static_assets_are_served(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 200


def test_ui_is_not_part_of_the_openapi_schema() -> None:
    paths = app.openapi()["paths"]

    assert APP_URL not in paths
    assert not any(path.startswith("/static") for path in paths)


def test_root_still_returns_api_information(client: TestClient) -> None:
    response = client.get("/")

    assert response.headers["content-type"] == "application/json"
    assert response.json()["docs_url"] == "/docs"


def test_swagger_ui_is_still_available(client: TestClient) -> None:
    response = client.get("/docs")

    assert response.status_code == 200
    assert "swagger-ui" in response.text


def test_generated_content_areas_are_rendered_not_preformatted(page: str) -> None:
    for name in ("result", "detail"):
        assert f'<div id="{name}-content" class="generated-content' in page
        assert f'id="{name}-placeholders"' in page
    assert "<pre" not in page


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_javascript_unit_tests_pass() -> None:
    # Runs tests/js/*.test.mjs with Node's built-in runner (no npm dependencies).
    result = subprocess.run(
        ["node", "--test", "tests/js/*.test.mjs"],
        cwd=JS_TESTS.parent.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_page_has_the_edit_mode_banner(page: str) -> None:
    assert 'id="edit-banner"' in page
    assert 'id="cancel-edit"' in page
    assert "Cancelar edición" in page


def test_page_has_the_delete_confirmation(page: str) -> None:
    modal = re.search(r'<div class="modal fade" id="delete-modal".*?</div>\s*</div>\s*</div>\s*</div>', page, re.DOTALL)
    assert modal, "delete confirmation modal not found"
    assert DELETE_MESSAGE in modal.group(0)
    assert 'id="delete-confirm" type="button" class="btn btn-danger"' in modal.group(0)


def test_js_form_fields_match_the_generate_schema() -> None:
    # The fields loaded into the form when editing must be exactly the API input fields.
    source = (STATIC_JS / "generation-form.js").read_text(encoding="utf-8")
    block = re.search(r"FORM_FIELDS = \[(.*?)\]", source, re.DOTALL)
    assert block, "FORM_FIELDS not found"

    assert re.findall(r'"([a-z_]+)"', block.group(1)) == list(GenerationCreate.model_fields)


def test_salesperson_fields_are_optional_and_labelled(page: str) -> None:
    form = form_html(page)

    for name, label in (("salesperson", "Comercial"), ("salesperson_company", "Empresa del comercial")):
        field = re.search(rf'<input id="{name}" name="{name}"[^>]*>', form)
        assert field, name
        assert "required" not in field.group(0)
        assert f">{label} <span" in form
    assert ">Empresa del cliente<" in form


def test_pricing_fields_and_preview_box(page: str) -> None:
    form = form_html(page)

    for name in ("price", "discount_percent"):
        field = re.search(rf'<input id="{name}" name="{name}"[^>]*>', form)
        assert field and 'inputmode="decimal"' in field.group(0) and "required" not in field.group(0)
    assert ">Precio (€) <span" in form
    assert ">Descuento (%) <span" in form
    assert 'id="pricing-preview"' in form


def test_commercial_terms_warning_areas(page: str) -> None:
    assert 'id="result-commercial-missing" class="alert alert-danger' in page
    assert 'id="detail-commercial-missing" class="alert alert-danger' in page
