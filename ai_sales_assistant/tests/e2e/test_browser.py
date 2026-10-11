"""Browser end-to-end tests: real HTTP server + real headless Chrome.

The unit and API tests use TestClient, which does not run JavaScript and does not behave like a
browser (Origin headers, cookies, cache, form submission). These tests start the real app with
uvicorn on a free port, with a throwaway database and a fake Ollama server, and drive Chrome.
They are skipped when Chrome or Node.js is not installed.
"""

import json
from urllib.parse import parse_qs, urlsplit
import re
import os
import shutil
import socket
import subprocess
import sys
import threading
import warnings
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config

from tests.e2e.server_log import never_reached_server

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HARNESS = Path(__file__).with_name("browser_flows.mjs")
CHROME_CANDIDATES = [
    os.environ.get("CHROME_PATH", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]
CLOSED_TEST_PROCESS = re.compile(r"\[e2e\] closed test process \d+ \(profile e2e-chrome-[A-Za-z0-9]{6}\)")
OMIT_MARKER = "E2E-OMIT"
HARNESS_TIMEOUT = 90
# Server log of each running test server (base_url -> path), used to decide on retries.
SERVER_LOGS: dict[str, Path] = {}
FAKE_CONTENT = "**Propuesta para Empresa E2E**\n\n- Ayuda a reducir los costes operativos.\n\nAtentamente,"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None or not any(path and Path(path).exists() for path in CHROME_CANDIDATES),
    reason="Browser E2E tests need Node.js and Chrome",
)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class FakeOllama(BaseHTTPRequestHandler):
    """Answers POST /api/chat like Ollama, so generation works without a model.

    It behaves like an obedient model (copies the mandatory commercial terms it receives), unless
    the request contains OMIT_MARKER: then it leaves them out, like a small model ignoring rules.
    """

    def do_POST(self) -> None:  # noqa: N802 (http.server API)
        request = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        user = request["messages"][-1]["content"]
        content = FAKE_CONTENT
        if OMIT_MARKER not in user and "<mandatory_commercial_terms>" in user:
            block = user.split("<mandatory_commercial_terms>")[1].split("</mandatory_commercial_terms>")[0]
            terms = [line for line in block.splitlines() if line.startswith("- ")]
            content = FAKE_CONTENT.replace("\n\nAtentamente,", "\n\n" + "\n".join(terms) + "\n\nAtentamente,")
        body = json.dumps(
            {
                "model": "fake-e2e",
                "message": {"role": "assistant", "content": content},
                "done": True,
                "prompt_eval_count": 5,
                "eval_count": 7,
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def live_server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    workdir = tmp_path_factory.mktemp("e2e")
    database_url = f"sqlite:///{workdir / 'e2e.db'}"

    config = Config()
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")

    ollama = ThreadingHTTPServer(("127.0.0.1", free_port()), FakeOllama)
    threading.Thread(target=ollama.serve_forever, daemon=True).start()

    port = free_port()
    base_url = f"http://127.0.0.1:{port}"
    # Run from an empty directory: the developer's .env is never read by this server.
    env = {key: value for key, value in os.environ.items() if not key.startswith(("OPENAI_", "SMTP_"))}
    env.update(
        DATABASE_URL=database_url,
        ENVIRONMENT="testing",
        EMAIL_BACKEND="console",
        AI_PROVIDER="ollama",
        OLLAMA_BASE_URL=f"http://127.0.0.1:{ollama.server_port}",
        OLLAMA_MODEL="fake-e2e",
        APP_BASE_URL=base_url,
        GUEST_MODE_ENABLED="true",
        DEMO_LOGIN_ENABLED="true",
        DEMO_USERNAME="demo",
        DEMO_PASSWORD="demo123",
        LOG_LEVEL="WARNING",
        # Unbuffered: the retry decision reads this log and must see every request already served.
        PYTHONUNBUFFERED="1",
    )
    # Logs go to a file: an unread pipe fills up and blocks the server mid-request.
    server_log = (workdir / "server.log").open("w", encoding="utf-8")
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--app-dir", str(PROJECT_ROOT), "--port", str(port)],
        cwd=workdir,
        env=env,
        stdout=server_log,
        stderr=subprocess.STDOUT,
    )
    try:
        for _ in range(100):
            try:
                if httpx.get(f"{base_url}/health", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.1)
        else:
            raise RuntimeError("the e2e server did not start: " + (workdir / "server.log").read_text(errors="replace"))
        SERVER_LOGS[base_url] = workdir / "server.log"
        yield base_url
    finally:
        SERVER_LOGS.pop(base_url, None)
        server.terminate()
        server.wait(timeout=10)
        server_log.close()
        ollama.shutdown()


def run_harness(base_url: str, scenario: str) -> tuple[str, str, str | None]:
    """(stdout, stderr, failure) of one harness run; failure is None when the harness finished."""
    try:
        result = subprocess.run(
            ["node", str(HARNESS), base_url, scenario],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=HARNESS_TIMEOUT,
        )
    except subprocess.TimeoutExpired as error:
        output = [o.decode("utf-8", "replace") if isinstance(o, bytes) else (o or "") for o in (error.stdout, error.stderr)]
        return output[0], output[1], f"the harness did not finish in {HARNESS_TIMEOUT} s"
    lines = result.stdout.strip().splitlines()
    if not lines:
        return result.stdout, result.stderr, "the harness printed no report"
    if "harnessError" in json.loads(lines[-1]):
        return result.stdout, result.stderr, lines[-1]
    return result.stdout, result.stderr, None


def browser(base_url: str, scenario: str) -> dict:
    """Runs a scenario. Retried ONCE only if the server log proves Chrome's requests never arrived."""
    log = SERVER_LOGS[base_url]
    previous_stderr = ""
    for attempt in (1, 2):
        log_offset = log.stat().st_size
        stdout, stderr, failure = run_harness(base_url, scenario)
        if failure is None:
            break
        log_since_attempt = log.read_bytes()[log_offset:].decode("utf-8", "replace")
        lost = never_reached_server(stdout, stderr, log_since_attempt)
        if attempt == 2 or not lost:
            pytest.fail(f"{scenario}: {failure}\nstderr:\n{stderr}", pytrace=False)
        requests = ", ".join(f"{method} {path}" for method, path in sorted(lost))
        warnings.warn(
            f"{scenario}: retried once; the server log shows these requests never arrived: {requests}",
            stacklevel=2,
        )
        previous_stderr += stderr
    report = json.loads(stdout.strip().splitlines()[-1])
    # Audit: the harness may only ever close processes of its own temporary test profile.
    for line in (previous_stderr + stderr).splitlines():
        if "closed test process" in line:
            assert CLOSED_TEST_PROCESS.fullmatch(line.strip()), line
        if "did not load" in line:
            # Visible in the pytest summary: a page load had to be requested twice.
            warnings.warn(f"{scenario}: {line.strip()}", stacklevel=2)
    assert report["jsErrors"] == [], report["jsErrors"]
    assert report["failedRequests"] == [], report["failedRequests"]
    return report


# --- B) "Entrar sin iniciar sesión" -------------------------------------------------------------------


def test_guest_button_reaches_the_app_with_a_guest_session(live_server: str) -> None:
    report = browser(live_server, "guest-button")

    assert report["arrived"] and report["path"] == "/app"
    assert report["guestMenu"] and report["generateForm"]
    assert report["me"]["is_guest"] is True
    assert report["cookieVisibleToJs"] == ""  # HttpOnly: invisible to JavaScript


def test_guest_button_works_even_without_javascript(live_server: str) -> None:
    report = browser(live_server, "guest-button-no-js")

    assert report["arrived"] and report["path"] == "/app"
    assert report["guestMenu"]


# --- A) Demo credentials with the blue "Entrar" button ------------------------------------------------


def test_demo_credentials_are_prefilled_and_enter_the_app(live_server: str) -> None:
    report = browser(live_server, "demo-login")

    assert report["prefilled"]["identifier"] == "demo"
    assert report["prefilled"]["password"] == "demo123"
    assert "demo123" in report["prefilled"]["hint"]
    assert report["arrived"] and report["path"] == "/app"
    assert report["guestMenu"]
    assert report["me"]["is_guest"] is True


def test_demo_credentials_work_even_without_javascript(live_server: str) -> None:
    report = browser(live_server, "demo-login-no-js")

    assert report["arrived"] and report["path"] == "/app"
    assert report["guestMenu"]


@pytest.mark.parametrize("scenario", ["demo-wrong-password", "demo-wrong-password-no-js"])
def test_wrong_demo_password_does_not_enter(live_server: str, scenario: str) -> None:
    report = browser(live_server, scenario)

    assert report["path"] == "/login"
    assert report["loginError"]
    assert not report["guestMenu"]
    assert report.get("me", 401) == 401


# --- Using the app and leaving ---------------------------------------------------------------------------


def test_share_buttons_next_to_copy(live_server: str) -> None:
    report = browser(live_server, "guest-generates")
    share = report["share"]

    # Disabled (no href) until there is a result.
    assert report["shareBefore"] == [{"disabled": True, "href": None}, {"disabled": True, "href": None}]

    # Rendered right after «Copiar», in the same row, with the same height and a line icon.
    assert share["buttons"] == ["copy-result", "share-email", "share-whatsapp"]
    for name in ("email", "whatsapp"):
        link = share[name]
        assert link["icon"] and not link["disabled"]
        assert link["box"]["height"] == share["copy"]["height"]
        assert abs(link["box"]["top"] - share["copy"]["top"]) <= 1
    assert share["copy"]["left"] < share["email"]["box"]["left"] < share["whatsapp"]["box"]["left"]
    assert share["email"]["label"] == "Enviar por correo"

    # Email: the customer's address, the Kodexia subject and the result text.
    email = urlsplit(share["email"]["href"])
    query = parse_qs(email.query)
    assert email.scheme == "mailto" and email.path == "cliente@e2e.es"
    assert query["subject"] == ["Propuesta Comercial - Kodexia"]
    assert "Ayuda a reducir los costes operativos." in query["body"][0]

    # WhatsApp: wa.me with the encoded text, in a new tab.
    whatsapp = urlsplit(share["whatsapp"]["href"])
    assert (whatsapp.scheme, whatsapp.netloc, whatsapp.path) == ("https", "wa.me", "/")
    assert "Ayuda a reducir los costes operativos." in parse_qs(whatsapp.query)["text"][0]
    assert share["whatsapp"]["target"] == "_blank"


def test_guest_generates_content_in_the_browser(live_server: str) -> None:
    report = browser(live_server, "guest-generates")

    assert report["resultError"] is None
    assert "Ayuda a reducir los costes operativos." in report["result"]
    assert report["boldRendered"]
    assert report["historyRows"] == 1
    # Comercial: sent to the API, stored, shown in "Ver" and restored by "Editar".
    assert report["stored"]["salesperson"] == "Carlos Vila"
    assert report["stored"]["salesperson_company"] is None
    assert "Comercial" in report["detail"] and "Carlos Vila" in report["detail"]
    assert report["editSalesperson"] == "Carlos Vila"
    assert report["editCompany"] == ""
    # Customer email: stored and restored by "Editar".
    assert report["stored"]["customer_email"] == "cliente@e2e.es"
    assert report["editCustomerEmail"] == "cliente@e2e.es"
    # The obedient fake model copied the mandatory terms: no warning.
    assert report["commercialWarning"] is None
    assert "Precio final: 152,15 €" in report["result"]
    # Pricing: the backend's breakdown in the form, stored input, shown in "Ver", restored by "Editar".
    for text in ("179,00 €", "15 %", "26,85 €", "152,15 €"):
        assert text in report["pricingPreview"].replace(" ", " ")
    assert report["stored"]["pricing"]["final_price"] == "152.15"
    assert "Precio final" in report["detail"] and "152,15" in report["detail"]
    assert (report["editPrice"], report["editDiscount"]) == ("179", "15")
    assert "152,15" in report["editPreview"]


def test_guest_logout_ends_the_session(live_server: str) -> None:
    report = browser(live_server, "guest-logout")

    assert report["arrived"] and report["path"] == "/login"
    assert report["me"] == 401 and report["app"] == 401


def test_registered_user_register_logout_and_login(live_server: str) -> None:
    report = browser(live_server, "register-logout-login")

    assert report["registered"] and report["afterRegister"]["userMenu"]
    assert report["loggedOut"] and report["afterLogout"]["me"] == 401
    assert report["afterLogout"]["notice"] == "Has cerrado sesión correctamente."
    assert report["loggedIn"] and report["afterLogin"]["userMenu"]
    assert not report["afterLogin"]["guestMenu"]


def test_app_redirects_to_login_without_a_session(live_server: str) -> None:
    report = browser(live_server, "protected-app-redirects")

    assert report["path"] == "/login"
    assert "next=%2Fapp" in report["search"]


def test_missing_commercial_terms_warning_and_regenerate(live_server: str) -> None:
    report = browser(live_server, "missing-terms-warning")

    # The fake model ignores the rules: after the single retry the app shows what is missing.
    assert "El texto generado omite estos datos comerciales obligatorios" in report["warning"]
    for tier in ("De 1 a 5 contenedores", "De 21 a 50 contenedores: 15 % de descuento.", "Más de 50 contenedores"):
        assert tier in report["warning"]
    assert report["regenerateButton"]
    assert "Ayuda a reducir los costes operativos." in report["result"]  # the text itself is not edited
    assert report["afterRegenerate"]  # still warned: regenerating calls the model again
    assert "El texto generado omite" in report["detailWarning"]


# --- New access design: layout, language selector, footer ------------------------------------------


def test_login_layout_on_desktop_is_horizontal(live_server: str) -> None:
    report = browser(live_server, "login-layout-desktop")

    card, aside = report["card"], report["aside"]
    assert card["left"] + card["width"] <= aside["left"]  # card on the left, presentation on the right
    assert card["top"] < aside["bottom"] and aside["top"] < card["bottom"]  # same row
    assert report["scrollWidth"] <= report["viewportWidth"]
    assert report["background"] == "rgb(0, 130, 127)"  # brand turquoise


def test_login_layout_on_mobile_is_stacked_without_horizontal_scroll(live_server: str) -> None:
    report = browser(live_server, "login-layout-mobile")

    card, aside, footer = report["card"], report["aside"], report["footer"]
    assert card["bottom"] <= aside["top"] <= footer["top"]  # card, then presentation, then footer
    assert report["scrollWidth"] <= report["viewportWidth"] == 375
    assert card["width"] >= 330


def test_language_selector_opens_with_the_four_languages(live_server: str) -> None:
    report = browser(live_server, "language-selector")

    assert report["before"] is False and report["open"] is True
    assert report["label"] == "ES"
    assert report["items"] == ["Español", "English", "Portugués", "Francés"]
    assert report["lang"] == "es"


FOOTER_EN = ["Contact", "Legal Notice", "Privacy", "Email", "WhatsApp (opens in a new tab)", "GitHub (opens in a new tab)"]


def test_switching_to_english_translates_the_interface_and_the_footer(live_server: str) -> None:
    report = browser(live_server, "switch-to-english")

    # Login page, right after choosing EN in the top-right selector.
    assert report["login"] == {
        "lang": "en",
        "selector": "EN",
        "title": "Sign in",
        "submit": "Sign in",
        "guest": "Try it without signing up",
        "slogan": "Your smart sales assistant",
        "footer": FOOTER_EN,
        "copyright": report["login"]["copyright"],
    }
    assert report["login"]["copyright"].endswith("AI Sales Assistant")

    # The choice is kept in the app, including the texts written by JavaScript.
    assert report["app"] == {
        "lang": "en",
        "formTitle": "New generation",
        "generate": "Generate with AI",
        "guestBadge": "Guest mode",
        "requiredError": "This field is required.",
        "historyEmpty": "No generations yet.",
        "contentType": "Sales email",
        "footer": FOOTER_EN,
    }

    # Back to Spanish from the app header.
    assert report["back"] == {"lang": "es", "formTitle": "Nueva generación", "footer": ["Contacto", "Legal", "Privacidad"]}


def test_switching_between_portuguese_and_french(live_server: str) -> None:
    report = browser(live_server, "switch-pt-fr")

    tab = {"pt": "(abre num novo separador)", "fr": "(s'ouvre dans un nouvel onglet)"}
    assert report["loginPt"] == {
        "lang": "pt",
        "selector": "PT",
        "title": "Iniciar sessão",
        "guest": "Experimentar sem registo",
        "footer": ["Contacto", "Aviso Legal", "Privacidade", "E-mail", f"WhatsApp {tab['pt']}", f"GitHub {tab['pt']}"],
    }
    assert report["loginFr"] == {
        "lang": "fr",
        "selector": "FR",
        "title": "Se connecter",
        "guest": "Essayer sans inscription",
        "footer": ["Contact", "Mentions Légales", "Confidentialité", "E-mail", f"WhatsApp {tab['fr']}", f"GitHub {tab['fr']}"],
    }
    # Inside the app, including the validation message written by JavaScript.
    assert report["appFr"] == {
        "lang": "fr",
        "formTitle": "Nouvelle génération",
        "generate": "Générer avec l'IA",
        "requiredError": "Ce champ est obligatoire.",
        "footer": ["Contact", "Mentions Légales", "Confidentialité"],
    }
    assert report["appPt"] == {
        "lang": "pt",
        "formTitle": "Nova geração",
        "generate": "Gerar com IA",
        "requiredError": "Este campo é obrigatório.",
        "footer": ["Contacto", "Aviso Legal", "Privacidade"],
    }


def test_footer_links_open_the_public_pages(live_server: str) -> None:
    report = browser(live_server, "footer-navigation")

    assert report["visited"] == {
        "/contacto": "Contacto y soporte",
        "/legal": "Aviso legal",
        "/privacidad": "Política de privacidad",
    }


# --- /app shares the login identity ---------------------------------------------------------------------

TEAL_STRONG = "rgb(11, 111, 107)"  # --brand-teal-strong
WHITE = "rgb(255, 255, 255)"  # --brand-on-teal
GRAY = "rgb(95, 107, 115)"  # --brand-gray
TRANSPARENT = "rgba(0, 0, 0, 0)"

FOOTER_CONTACTS = [
    {"name": "email", "text": "Correo electrónico", "href": "mailto:soporte@aisalesassistant.demo", "target": "", "icon": True, "visible": True},
    {"name": "whatsapp", "text": "WhatsApp (se abre en una pestaña nueva)", "href": "https://wa.me/34600123456", "target": "_blank", "icon": True, "visible": True},
    {"name": "github", "text": "GitHub (se abre en una pestaña nueva)", "href": "https://github.com/LucPinheiro", "target": "_blank", "icon": True, "visible": True},
]


def test_footer_is_one_quiet_row_with_email_whatsapp_and_github(live_server: str) -> None:
    report = browser(live_server, "footer-contacts")

    # The same three contact links, each a bare line icon beside its text, on the access screen and in the app.
    assert report["login"] == FOOTER_CONTACTS
    assert report["app"] == FOOTER_CONTACTS

    # One row on desktop: copyright left, legal links centred, contact links right.
    row = report["row"]
    inner, copy, legal, social = row["inner"], row["copy"], row["legal"], row["social"]
    assert max(abs(part["middle"] - inner["middle"]) for part in (copy, legal, social)) <= 2
    assert copy["right"] < legal["left"] and legal["right"] < social["left"]
    assert abs((legal["left"] + legal["right"]) / 2 - (inner["left"] + inner["right"]) / 2) <= 2

    # Soft grey at rest, with no box: no background and no border.
    quiet = {"bg": TRANSPARENT, "border": "none", "color": GRAY}
    assert report["copyColor"] == GRAY
    assert report["socialRest"] == quiet | {"icon": GRAY}
    assert report["legalRest"] == quiet

    # Hover and keyboard focus tint only the text and the icon with the brand dark cyan.
    tinted = {"bg": TRANSPARENT, "border": "none", "color": TEAL_STRONG}
    assert report["socialHover"] == tinted | {"icon": TEAL_STRONG}
    assert report["socialFocus"] == tinted | {"icon": TEAL_STRONG}
    assert report["legalHover"] == tinted


def test_app_uses_the_brand_colours(live_server: str) -> None:
    report = browser(live_server, "app-brand-styles")

    assert report["generateBg"] == TEAL_STRONG  # "Generar con IA"
    assert report["copyBorder"] == TEAL_STRONG  # "Copiar"
    assert report["badgeBg"] == TEAL_STRONG  # content-type badge
    assert report["viewColor"] == TEAL_STRONG  # Ver
    assert report["editColor"] == "rgb(108, 117, 125)"  # Editar: neutral grey
    assert report["deleteColor"] == "rgb(220, 53, 69)"  # Eliminar: red
    assert report["focused"] and report["focusBorder"] == TEAL_STRONG
    assert "rgba(11, 111, 107" in report["focusShadow"]  # soft turquoise halo, not Bootstrap blue
    assert report["inputBg"] == "rgb(255, 255, 255)"
    assert report["pageBg"] == "rgb(244, 247, 247)"  # very light background, not turquoise
    assert report["cardBg"] == "rgb(255, 255, 255)"
    assert report["headerTop"] == "rgb(0, 130, 127)"


def test_menus_and_selects_highlight_with_the_logo_turquoise(live_server: str) -> None:
    report = browser(live_server, "dropdown-highlight")
    highlight = {"bg": TEAL_STRONG, "color": WHITE}

    # Bootstrap menus: current language, mouse hover, keyboard focus; "Cerrar sesión" turns white too.
    assert report["languageActive"] == highlight
    assert report["menuHover"] == highlight
    assert report["menuFocus"] == highlight
    assert report["logoutHover"] == highlight
    assert report["menuRest"]["bg"] != TEAL_STRONG  # only the highlighted item, not the whole menu

    # Native <select>: the chosen option, and hover inside the open list (not the system blue).
    assert report["baseSelect"] is True and report["selectAppearance"] == "base-select"
    assert report["optionChecked"] == highlight
    assert report["optionRest"] == {"bg": WHITE, "color": "rgb(18, 48, 58)"}  # --brand-ink on white
    assert report["optionHover"] == highlight
    assert report["pickerClosed"] is True


def test_login_logo_is_a_little_larger_and_still_responsive(live_server: str) -> None:
    report = browser(live_server, "login-logo-size")

    assert report["desktop"]["mark"] == 35 and report["desktop"]["wordmark"] == "21.6px"
    assert report["mobile"]["mark"] == 30 and report["mobile"]["scroll"]


# --- /contacto ---------------------------------------------------------------------------------------


def test_contact_page_in_the_browser(live_server: str) -> None:
    report = browser(live_server, "contact-page")

    desktop, mobile = report["desktop"], report["mobile"]
    assert desktop["info"]["right"] <= desktop["form"]["left"]  # two columns: details | form
    assert mobile["info"]["top"] < mobile["form"]["top"]  # one column: details first
    assert desktop["noScroll"] and mobile["noScroll"]

    styles = report["styles"]
    assert styles["button"] == TEAL_STRONG and styles["buttonText"] == "uppercase"  # ENVIAR MENSAJE
    assert styles["focusBorder"] == TEAL_STRONG and styles["inputBg"] == "rgb(255, 255, 255)"
    assert styles["mailto"] == "mailto:soporte@aisalesassistant.demo"
    assert styles["tel"] == "tel:+34600123456"
    assert styles["badge"] == "Datos de demostración"
    assert styles["consentInitially"] is False  # GDPR: never pre-ticked
    assert styles["gdprBelowForm"] is True  # first-layer information right below the form

    invalid = report["invalid"]
    assert invalid["nameError"] == "No se permiten etiquetas HTML ni los caracteres < y >."
    assert invalid["emailError"] == "Introduce un email válido."
    assert invalid["keptName"] == "<b>Ana</b>" and invalid["demo"] is False
    assert invalid["privacyError"] == "Debes aceptar la política de privacidad para enviar el mensaje."

    # The flow ticks the consent checkbox (a real click) before the valid submission.
    assert report["consent"]["checked"] is True
    assert report["consent"]["color"] == TEAL_STRONG  # brand colour, not Bootstrap blue
    assert report["consent"]["errorShown"] is False  # ticking it clears the consent error

    valid = report["valid"]
    assert valid["notice"] == (
        "Formulario en modo demostración: hemos comprobado tus datos, pero el mensaje no se ha enviado."
    )
    assert valid["cleared"] and not valid["errors"]
    assert valid["consentAfter"] is False  # a new message needs a new consent
