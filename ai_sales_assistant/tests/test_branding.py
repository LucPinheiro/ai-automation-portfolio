"""New access screens, identity (logo, colours) and the interface-language architecture."""

import re
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, translator
from app.i18n.es import MESSAGES

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "app" / "templates"
STATIC = ROOT / "app" / "static"


@pytest.fixture
def login_page(anon_client: TestClient) -> str:
    response = anon_client.get("/login")
    assert response.status_code == 200
    return response.text


# --- Login screen -----------------------------------------------------------------------------------


def test_login_card_texts(login_page: str) -> None:
    assert '<h1 id="access-title" class="access-title">Iniciar sesión</h1>' in login_page
    assert '<label for="identifier" class="form-label">Usuario o email</label>' in login_page
    assert '<label for="password" class="form-label">Contraseña</label>' in login_page
    assert '<span class="button-label">Entrar</span>' in login_page


def test_primary_buttons_are_uppercase_by_css_only() -> None:
    css = (STATIC / "css" / "brand.css").read_text(encoding="utf-8")

    # "ENTRAR" / "CREAR CUENTA" on screen; screen readers still get normal words.
    for selector in (".btn-access-primary {", ".btn-access-outline {"):
        rule = css.split(selector)[1].split("}")[0]
        assert "text-transform: uppercase" in rule


def test_password_recovery_and_register_links(login_page: str) -> None:
    assert '<a href="/forgot-password" id="forgot-link">¿Has olvidado tu contraseña?</a>' in login_page
    assert '<a href="/register" id="register-link">Crear cuenta</a>' in login_page


def test_demo_values_are_prefilled_with_a_discreet_hint(login_page: str) -> None:
    assert re.search(r'id="identifier"[^>]*value="demo"', login_page)
    assert re.search(r'id="password"[^>]*value="demo123"', login_page)
    assert '<p class="demo-hint" id="demo-hint">Demo: demo / demo123</p>' in login_page


def test_login_and_guest_forms_keep_their_secure_endpoints(login_page: str) -> None:
    assert '<form id="login-form" class="login-form" method="post" action="/login"' in login_page
    assert '<form id="guest-form" method="post" action="/guest" class="access-guest">' in login_page


def test_guest_access_is_secondary_and_explains_its_limits(login_page: str) -> None:
    guest = login_page.split('<form id="guest-form"')[1].split("</form>")[0]

    assert '<span class="button-label">Probar sin registrarse</span>' in guest
    assert 'class="guest-link"' in guest and "btn-access-primary" not in guest
    assert "máximo 10 generaciones" in guest
    assert "tus datos se borran al salir" in guest


def test_presentation_panel(login_page: str) -> None:
    aside = login_page.split('<section class="access-aside"')[1].split("</section>")[0]

    assert "Tu asistente comercial inteligente" in aside
    assert "Crea emails, propuestas comerciales, seguimientos y mensajes profesionales con inteligencia artificial." in aside
    assert '<a href="/register" class="btn-access-outline" id="aside-register">Crear cuenta</a>' in aside
    assert "Empieza a crear comunicaciones comerciales en segundos." in aside


def test_card_comes_before_the_presentation_for_mobile_order(login_page: str) -> None:
    assert login_page.index('class="access-card"') < login_page.index('class="access-aside"')


def test_register_page_offers_login_instead(anon_client: TestClient) -> None:
    page = anon_client.get("/register").text

    assert 'id="aside-login"' in page and 'href="/login"' in page
    assert 'id="aside-register"' not in page


@pytest.mark.parametrize("path", ["/register", "/forgot-password", "/reset-password"])
def test_other_access_screens_share_the_layout(anon_client: TestClient, path: str) -> None:
    page = anon_client.get(path).text

    assert '<body class="access-page">' in page
    assert 'class="access-card"' in page and 'class="access-aside"' in page
    assert 'id="language-selector"' in page


def test_forgot_password_heading(anon_client: TestClient) -> None:
    assert ">¿Has olvidado tu contraseña?</h1>" in anon_client.get("/forgot-password").text


def test_no_secrets_in_the_login_html(login_page: str) -> None:
    for secret in ("$argon2", "OPENAI", "sk-", "api_key", "ai_sales_session=", "SMTP_PASSWORD"):
        assert secret not in login_page


def test_responsive_rules_exist() -> None:
    css = (STATIC / "css" / "brand.css").read_text(encoding="utf-8")
    mobile = css.split("@media (max-width: 991.98px)")[1].split("@media")[0]

    # Below 992 px the two columns become one (card first, presentation after).
    assert "grid-template-columns: minmax(0, 1fr);" in mobile


# --- Language selector and i18n architecture ----------------------------------------------------------


def test_language_selector_shows_es_and_offers_the_other_languages(login_page: str) -> None:
    selector = login_page.split('id="language-selector"')[1].split("</div>")[0]

    assert re.search(r">\s*ES\s*</button>", selector)
    assert 'aria-label="Idioma actual: Español"' in selector
    assert 'class="dropdown-item active" lang="es"' in selector
    assert 'href="/language/es?next=%2Flogin"' in selector and ">Español</a>" in selector
    assert 'href="/language/en?next=%2Flogin"' in selector and ">English</a>" in selector
    assert 'href="/language/pt?next=%2Flogin"' in selector and ">Portugués</a>" in selector
    assert 'href="/language/fr?next=%2Flogin"' in selector and ">Francés</a>" in selector
    assert selector.count('class="dropdown-item') == 4


def test_html_lang_is_spanish(login_page: str) -> None:
    assert '<html lang="es">' in login_page


def test_spanish_is_the_default_and_four_languages_are_supported() -> None:
    assert DEFAULT_LANGUAGE == "es"
    assert SUPPORTED_LANGUAGES == {"es": "Español", "en": "English", "pt": "Portugués", "fr": "Francés"}


def test_unknown_language_cookie_falls_back_to_spanish(anon_client: TestClient) -> None:
    anon_client.cookies.set("ui_lang", "xx")

    assert '<html lang="es">' in anon_client.get("/login").text


def test_translator_formats_and_reports_missing_keys() -> None:
    t = translator("es")

    assert t("footer.copyright", year=2026) == "© 2026 AI Sales Assistant"
    assert t("does.not.exist") == "does.not.exist"
    assert translator("xx")("brand.slogan") == "Tu asistente comercial inteligente"


def test_every_key_used_in_templates_exists_in_the_catalog() -> None:
    used = set()
    for template in TEMPLATES.glob("*.html"):
        used |= set(re.findall(r"""\bt\(\s*["']([a-z_.]+)["']""", template.read_text(encoding="utf-8")))
        used |= set(re.findall(r'"((?:legal|privacy)\.[a-z_]+)"', template.read_text(encoding="utf-8")))

    # Keys built in the template (e.g. "contact.category." ~ value) are checked where they are used.
    used = {key for key in used if not key.endswith(".")}
    assert used, "no translated keys found"
    assert used <= MESSAGES.keys(), sorted(used - MESSAGES.keys())


# --- Logo and colours ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name", ["logo-mark.svg", "logo-mark-teal.svg", "logo-mark-white.svg", "logo-full-teal.svg", "logo-full-white.svg"]
)
def test_logo_files_are_local_valid_svg(name: str) -> None:
    text = (STATIC / "img" / name).read_text(encoding="utf-8")
    root = ElementTree.fromstring(text)

    assert root.tag.endswith("svg")
    assert root.get("aria-label") == "AI Sales Assistant"
    # No external resources: the only URL is the SVG namespace itself.
    assert re.findall(r"https?://[^\"']+", text) == ["http://www.w3.org/2000/svg"]
    assert "<image" not in text and "<script" not in text


def test_white_and_turquoise_variants() -> None:
    assert 'fill="#FFFFFF"' in (STATIC / "img" / "logo-mark-white.svg").read_text(encoding="utf-8")
    assert 'fill="#0B6F6B"' in (STATIC / "img" / "logo-mark-teal.svg").read_text(encoding="utf-8")


def test_favicon_and_inline_mark(login_page: str) -> None:
    assert '<link rel="icon" href="/static/img/logo-mark.svg" type="image/svg+xml">' in login_page
    assert 'class="brand-mark' in login_page and 'fill-rule="evenodd"' in login_page
    assert "<strong>AI</strong> Sales Assistant" in login_page


def _luminance(hex_color: str) -> float:
    rgb = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(a: str, b: str) -> float:
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


@pytest.mark.parametrize(
    ("foreground", "background", "minimum"),
    [
        ("#ffffff", "--brand-teal", 4.5),  # presentation text on the turquoise background
        ("#ffffff", "--brand-teal-strong", 4.5),  # ENTRAR
        ("--brand-teal-strong", "#ffffff", 4.5),  # links on white
        ("--brand-ink", "#ffffff", 4.5),  # main text
        ("--brand-muted", "#ffffff", 4.5),  # secondary text (demo hint, footer)
        ("--brand-muted", "--brand-soft", 4.5),  # pending notes on public pages
    ],
)
def test_palette_meets_wcag_aa(foreground: str, background: str, minimum: float) -> None:
    css = (STATIC / "css" / "brand.css").read_text(encoding="utf-8")
    tokens = dict(re.findall(r"(--brand-[a-z-]+):\s*(#[0-9a-fA-F]{6})", css))

    def color(value: str) -> str:
        return tokens[value] if value.startswith("--") else value

    assert _contrast(color(foreground), color(background)) >= minimum


# --- One identity for login and app ---------------------------------------------------------------------

OWN_CSS = [STATIC / "css" / "app.css", STATIC / "css" / "brand.css"]
HEX_OR_RGB = re.compile(r"#[0-9a-fA-F]{3,6}(?![0-9a-fA-F])|rgba?\(\s*\d")


def _outside_root(css: str) -> str:
    start = css.index(":root {")
    end = css.index("\n}\n", start) + 3
    return css[:start] + css[end:]


@pytest.mark.parametrize("path", OWN_CSS, ids=lambda p: p.name)
def test_no_bootstrap_blue_in_our_css(path: Path) -> None:
    css = path.read_text(encoding="utf-8").lower()

    for blue in ("#0d6efd", "13, 110, 253", "13,110,253", "#6610f2"):
        assert blue not in css


@pytest.mark.parametrize("path", OWN_CSS, ids=lambda p: p.name)
def test_colours_only_live_in_the_brand_variables(path: Path) -> None:
    # Every literal colour is in a :root variable block, so the identity changes from one place.
    assert HEX_OR_RGB.findall(_outside_root(path.read_text(encoding="utf-8"))) == []


def test_bootstrap_primary_is_mapped_to_the_brand() -> None:
    css = (STATIC / "css" / "brand.css").read_text(encoding="utf-8")
    root = css[css.index(":root {") : css.index("\n}\n", css.index(":root {"))]

    for mapping in (
        "--bs-primary: var(--brand-teal-strong);",
        "--bs-primary-rgb: var(--brand-teal-strong-rgb);",
        "--bs-link-color: var(--brand-teal-strong);",
        "--bs-focus-ring-color: var(--brand-focus-ring);",
    ):
        assert mapping in root
    for component in (".btn-primary {", ".btn-outline-primary {", ".form-select:focus {", ".dropdown-menu {"):
        rule = css.split(component)[1].split("}")[0]
        assert "var(--brand-" in rule and not HEX_OR_RGB.search(rule), component


def test_destructive_actions_stay_red() -> None:
    css = (STATIC / "css" / "brand.css").read_text(encoding="utf-8") + (STATIC / "css" / "app.css").read_text(
        encoding="utf-8"
    )

    # Danger (Eliminar) and secondary (Editar) keep Bootstrap's own red and grey.
    assert ".btn-outline-danger" not in css and ".btn-danger" not in css
    assert ".btn-outline-secondary" not in css


def test_rgb_triplets_match_the_hex_brand_colours() -> None:
    css = (STATIC / "css" / "brand.css").read_text(encoding="utf-8")
    tokens = dict(re.findall(r"(--brand-[a-z-]+):\s*([^;]+);", css))

    for name in ("teal", "teal-strong", "teal-stronger"):
        hex_value = tokens[f"--brand-{name}"].strip()
        rgb = ", ".join(str(int(hex_value[i : i + 2], 16)) for i in (1, 3, 5))
        assert tokens[f"--brand-{name}-rgb"].strip() == rgb


def test_login_logo_is_slightly_larger_than_the_base_mark() -> None:
    css = (STATIC / "css" / "brand.css").read_text(encoding="utf-8")
    rule = css.split(".access-brand .brand-mark {")[1].split("}")[0]

    assert "width: 35px;" in rule and "height: 35px;" in rule  # base mark: 30 px (about +17 %)


# --- Dropdown menus and select lists: one highlight colour ---------------------------------------


def css_rule(css: str, selector_start: str) -> tuple[str, str]:
    """(selector list, declarations) of the rule whose selector list starts with selector_start."""
    start = css.index(selector_start)
    selectors, body = css[start:].split("{", 1)
    return selectors, body.split("}", 1)[0]


def test_every_dropdown_state_uses_the_logo_turquoise_with_white_text() -> None:
    css = (STATIC / "css" / "brand.css").read_text(encoding="utf-8")
    logo = (STATIC / "img" / "logo-mark-teal.svg").read_text(encoding="utf-8")
    assert 'fill="#0B6F6B"' in logo and "--brand-teal-strong: #0b6f6b;" in css  # the logo colour

    highlight = ("color: var(--brand-on-teal);", "background-color: var(--brand-teal-strong);")
    expected = {
        ".dropdown-item:hover": (":hover", ":focus", ":focus-visible", ":active", ".active", ".selected"),
        ".form-select option:hover": (":hover", ":focus", ":focus-visible", ":checked"),
        ".form-select option:checked {": (":checked",),
    }
    for start, states in expected.items():
        selectors, body = css_rule(css, start)
        for state in states:
            assert state in selectors, (start, state)
        for declaration in highlight:
            assert declaration in body, (start, declaration)
        assert not HEX_OR_RGB.search(body), start

    menu = css_rule(css, ".dropdown-menu {")[1]
    for variable in ("hover-bg: var(--brand-teal-strong)", "hover-color: var(--brand-on-teal)",
                     "active-bg: var(--brand-teal-strong)", "active-color: var(--brand-on-teal)"):
        assert f"--bs-dropdown-link-{variable};" in menu
    # The red "Cerrar sesión" also turns white on the highlight (red on turquoise is unreadable).
    assert "color: var(--brand-on-teal) !important;" in css_rule(css, ".dropdown-item.text-danger:hover")[1]
    # The language selector no longer has its own pale highlight.
    assert ".lang-switch .dropdown-item.active {" not in css


def test_customizable_select_is_only_used_where_supported() -> None:
    css = (STATIC / "css" / "brand.css").read_text(encoding="utf-8")
    block = css.split("@supports (appearance: base-select) {", 1)[1]

    assert "appearance: base-select;" in block
    assert css.count("appearance: base-select;") == 1  # never outside the @supports guard
    assert ".form-select::picker-icon {\n    display: none;" in block  # no second arrow next to Bootstrap's
