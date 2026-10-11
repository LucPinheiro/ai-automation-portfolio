from pathlib import Path
from collections.abc import Awaitable, Callable
from typing import Annotated, Any
from urllib.parse import parse_qs, urlencode

from fastapi import APIRouter, Depends, Request, status
from pydantic import ValidationError
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.api.dependencies import AuthServiceDep, OptionalUserDep, SessionTokenDep, SettingsDep
from app.core.constants import (
    COMPANY_MAX_LENGTH,
    CUSTOMER_MAX_LENGTH,
    CUSTOMER_NEEDS_MAX_LENGTH,
    EMAIL_MAX_LENGTH,
    INDUSTRY_MAX_LENGTH,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    PRODUCT_OR_SERVICE_MAX_LENGTH,
    SALESPERSON_COMPANY_MAX_LENGTH,
    SALESPERSON_MAX_LENGTH,
    USER_NAME_MAX_LENGTH,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
)
from app.core.enums import ContentType, Language, Tone
from app.core.exceptions import GuestModeDisabledError, InvalidCredentialsError
from app.database.types import utc_now
from app.i18n import LANGUAGE_COOKIE, SUPPORTED_LANGUAGES, Translator, js_messages, resolve_language, translator
from app.models.user import User
from app.routers.auth import set_session_cookie
from app.schemas.contact import CONTACT_FIELDS, CONTACT_LIMITS, ContactCategory, ContactMessage
from app.services.access import demo_login_available, enter_guest_mode, sign_in
from app.services.contact import ContactService

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Catalog keys (app.i18n) of the UI labels for the API enum values, translated per request.
# Keys must cover every enum member (enforced by tests).
CONTENT_TYPE_LABELS: dict[ContentType, str] = {member: f"option.content_type.{member.value}" for member in ContentType}
LANGUAGE_LABELS: dict[Language, str] = {member: f"option.language.{member.value}" for member in Language}
TONE_LABELS: dict[Tone, str] = {member: f"option.tone.{member.value}" for member in Tone}

# Same limits the API enforces in GenerationCreate.
MAX_LENGTHS = {
    "customer": CUSTOMER_MAX_LENGTH,
    "company": COMPANY_MAX_LENGTH,
    "industry": INDUSTRY_MAX_LENGTH,
    "product_or_service": PRODUCT_OR_SERVICE_MAX_LENGTH,
    "customer_needs": CUSTOMER_NEEDS_MAX_LENGTH,
    "salesperson": SALESPERSON_MAX_LENGTH,
    "salesperson_company": SALESPERSON_COMPANY_MAX_LENGTH,
}

# Same limits the API enforces in the auth schemas.
AUTH_LIMITS = {
    "name": USER_NAME_MAX_LENGTH,
    "email": EMAIL_MAX_LENGTH,
    "password_min": PASSWORD_MIN_LENGTH,
    "password_max": PASSWORD_MAX_LENGTH,
    "username_min": USERNAME_MIN_LENGTH,
    "username_max": USERNAME_MAX_LENGTH,
}

# Fixed notices the login page can show (catalog keys); any other value is ignored (no reflected text).
LOGIN_NOTICES = {
    "logged_out": "auth.notice.logged_out",
    "password_reset": "auth.notice.password_reset",
    "session_expired": "auth.notice.session_expired",
    "guest_disabled": "auth.notice.guest_disabled",
}

LOGIN_FAILED_MESSAGE = "auth.login.failed"
LANGUAGE_COOKIE_MAX_AGE = 365 * 24 * 3600
MAX_FORM_BYTES = 4096
# The contact message allows 4000 characters; URL-encoded accents take up to 6 bytes each.
MAX_CONTACT_FORM_BYTES = 32 * 1024

DEFAULT_AFTER_LOGIN = "/app"

# The web UI is not part of the public API, so it is left out of OpenAPI.
router = APIRouter(include_in_schema=False)


def safe_next_path(value: str | None) -> str:
    """Only same-site paths are allowed as a post-login destination (no open redirects)."""
    if not value or not value.startswith("/") or value.startswith("//") or "\\" in value:
        return DEFAULT_AFTER_LOGIN
    return value


def login_redirect(request: Request) -> RedirectResponse:
    next_path = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    return RedirectResponse(f"/login?{urlencode({'next': next_path})}", status_code=303)


def is_registered(user: User | None) -> bool:
    return user is not None and not user.is_guest


def footer_contacts(settings: Any) -> list[dict[str, Any]]:
    """The footer buttons (email, WhatsApp, GitHub); one whose setting is empty is not shown."""
    contacts = []
    if settings.support_email:
        contacts.append({"name": "email", "href": f"mailto:{settings.support_email}", "external": False})
    whatsapp_number = "".join(ch for ch in settings.support_phone or "" if ch.isdigit())
    if whatsapp_number:
        contacts.append({"name": "whatsapp", "href": f"https://wa.me/{whatsapp_number}", "external": True})
    if settings.github_url:
        contacts.append({"name": "github", "href": settings.github_url, "external": True})
    return contacts


def translated(labels: dict[Any, str], t: Translator) -> dict[Any, str]:
    return {value: t(key) for value, key in labels.items()}


def render(request: Request, template: str, user: User | None, settings: Any, **context: Any) -> HTMLResponse:
    language = resolve_language(request)
    t = translator(language)
    return templates.TemplateResponse(
        request,
        template,
        {
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            # Interface language (app.i18n): `t("key")` in templates, the selector and <html lang>.
            "t": t,
            "ui_language": language,
            "ui_languages": SUPPORTED_LANGUAGES,
            # Texts used by the JavaScript (static/js/i18n.js), in the interface language.
            "js_messages": js_messages(language),
            # Where the language selector returns to. Path only: a query may hold a secret
            # (the password reset token), which must never be copied into the page.
            "current_path": request.url.path,
            "current_year": utc_now().year,
            "support_email": settings.support_email,
            "footer_contacts": footer_contacts(settings),
            "current_user": user,
            "auth_limits": AUTH_LIMITS,
            "guest_mode_enabled": settings.guest_mode_enabled,
            "guest_max_generations": settings.guest_max_generations,
            **context,
        },
    )


def no_store(response: Response) -> Response:
    # Pages with account data or forms for secrets must not be cached.
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/app", response_class=HTMLResponse)
def web_app(request: Request, user: OptionalUserDep, settings: SettingsDep) -> Response:
    if user is None:
        return login_redirect(request)
    t = translator(resolve_language(request))
    return no_store(
        render(
            request,
            "index.html",
            user,
            settings,
            content_types=translated(CONTENT_TYPE_LABELS, t),
            languages=translated(LANGUAGE_LABELS, t),
            tones=translated(TONE_LABELS, t),
            max_lengths=MAX_LENGTHS,
        )
    )


@router.get("/account", response_class=HTMLResponse)
def account(request: Request, user: OptionalUserDep, settings: SettingsDep) -> Response:
    if user is None:
        return login_redirect(request)
    if user.is_guest:
        # Guests have no account settings (no email or password).
        return RedirectResponse(DEFAULT_AFTER_LOGIN, status_code=303)
    return no_store(render(request, "account.html", user, settings))


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request, user: OptionalUserDep, settings: SettingsDep, next: str | None = None, notice: str | None = None
) -> Response:
    # Guests may log in (their generations move to the account); registered users go on.
    if is_registered(user):
        return RedirectResponse(safe_next_path(next), status_code=303)
    return render_login(request, user, settings, next_path=safe_next_path(next), notice=LOGIN_NOTICES.get(notice or ""))


def render_login(
    request: Request,
    user: User | None,
    settings: Any,
    *,
    next_path: str,
    notice: str | None = None,
    error: str | None = None,
    identifier: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    # The demo credentials are public and only open a guest session: shown pre-filled for a one-click demo.
    demo = None
    if demo_login_available(settings) and not (user and user.is_guest):
        demo = {"username": settings.demo_username, "password": settings.demo_password}
    t = translator(resolve_language(request))
    response = render(
        request,
        "login.html",
        user,
        settings,
        next_path=next_path,
        notice=t(notice) if notice else None,
        form_error=t(error) if error else None,
        demo=demo,
        identifier_value=identifier if identifier is not None else (demo["username"] if demo else ""),
        password_value="" if identifier is not None or not demo else demo["password"],
    )
    response.status_code = status_code
    return no_store(response)


def form_reader(max_bytes: int) -> Callable[[Request], Awaitable[dict[str, str]]]:
    """Dependency reading a URL-encoded form body (no python-multipart needed).

    Oversized bodies are treated as empty, so they fail validation without being parsed.
    """

    async def read(request: Request) -> dict[str, str]:
        body = await request.body()
        if len(body) > max_bytes:
            return {}
        parsed = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)
        return {key: values[0] for key, values in parsed.items()}

    return read


form_fields = form_reader(MAX_FORM_BYTES)
FormDep = Annotated[dict[str, str], Depends(form_fields)]
ContactFormDep = Annotated[dict[str, str], Depends(form_reader(MAX_CONTACT_FORM_BYTES))]


@router.post("/login", response_class=HTMLResponse)
def login_form(
    request: Request,
    form: FormDep,
    user: OptionalUserDep,
    token: SessionTokenDep,
    auth: AuthServiceDep,
    settings: SettingsDep,
) -> Response:
    """Classic form login: works even when JavaScript does not run (progressive enhancement)."""
    next_path = safe_next_path(form.get("next"))
    identifier = form.get("identifier", "").strip()
    password = form.get("password", "")
    if not identifier or not password or len(identifier) > EMAIL_MAX_LENGTH or len(password) > PASSWORD_MAX_LENGTH:
        return render_login(
            request, user, settings, next_path=next_path, error=LOGIN_FAILED_MESSAGE, identifier=identifier,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    try:
        result = sign_in(auth, settings, identifier=identifier, password=password, token=token)
    except InvalidCredentialsError:
        # Same message for unknown users and wrong passwords; the password is never echoed back.
        return render_login(
            request, user, settings, next_path=next_path, error=LOGIN_FAILED_MESSAGE, identifier=identifier,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    response = RedirectResponse(DEFAULT_AFTER_LOGIN if result.user.is_guest else next_path, status_code=303)
    if result.issued is not None:
        set_session_cookie(response, settings, result.issued)
    return response


@router.post("/guest")
def guest_form(token: SessionTokenDep, auth: AuthServiceDep, settings: SettingsDep) -> Response:
    """"Entrar sin iniciar sesión" as a plain form POST: creates the guest session and goes to /app."""
    try:
        result = enter_guest_mode(auth, settings, token)
    except GuestModeDisabledError:
        return RedirectResponse("/login?notice=guest_disabled", status_code=303)
    response = RedirectResponse(DEFAULT_AFTER_LOGIN, status_code=303)
    if result.issued is not None:
        set_session_cookie(response, settings, result.issued)
    return response


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, user: OptionalUserDep, settings: SettingsDep) -> Response:
    if is_registered(user):
        return RedirectResponse(DEFAULT_AFTER_LOGIN, status_code=303)
    return no_store(render(request, "register.html", user, settings))


@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request, user: OptionalUserDep, settings: SettingsDep) -> Response:
    return no_store(render(request, "forgot_password.html", user, settings))


@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(request: Request, user: OptionalUserDep, settings: SettingsDep) -> Response:
    # The token is read by JavaScript from the URL; it never goes into the HTML.
    response = no_store(render(request, "reset_password.html", user, settings))
    # The URL contains the token: never leak it through the Referer header.
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


# --- Public information pages (no session needed) ----------------------------------------------


@router.get("/language/{code}")
def set_language(code: str, next: str | None = None) -> Response:
    """Language selector: stores the interface language in a cookie and goes back to the same page."""
    response = RedirectResponse(safe_next_path(next), status_code=303)
    if code in SUPPORTED_LANGUAGES:
        # A preference, not a credential: SameSite=Lax, valid for a year.
        response.set_cookie(LANGUAGE_COOKIE, code, max_age=LANGUAGE_COOKIE_MAX_AGE, path="/", httponly=True, samesite="lax")
    return response


@router.get("/contacto", response_class=HTMLResponse)
def contact_page(request: Request, user: OptionalUserDep, settings: SettingsDep) -> Response:
    return render_contact(request, user, settings)


@router.post("/contacto", response_class=HTMLResponse)
def contact_submit(request: Request, form: ContactFormDep, user: OptionalUserDep, settings: SettingsDep) -> Response:
    """Validate the contact form. In demo mode nothing is sent, stored or logged."""
    values = {field: form.get(field, "") for field in CONTACT_FIELDS}
    try:
        message = ContactMessage.model_validate(values)
    except ValidationError as exc:
        return render_contact(
            request, user, settings, values=values, errors=contact_errors(exc, translator(resolve_language(request))),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    result = ContactService(settings.contact_form_mode).submit(message)
    # Demo: the form is cleared and the page states clearly that the message was not sent.
    return render_contact(request, user, settings, result=result)


def render_contact(
    request: Request,
    user: User | None,
    settings: Any,
    *,
    values: dict[str, str] | None = None,
    errors: dict[str, str] | None = None,
    result: Any = None,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    response = render(
        request,
        "contact.html",
        user,
        settings,
        support={
            "email": settings.support_email,
            "phone": settings.support_phone,
            # tel: links need the number without spaces.
            "phone_href": "".join(ch for ch in settings.support_phone or "" if ch.isdigit() or ch == "+"),
            "hours_open": settings.support_hours_open,
            "hours_close": settings.support_hours_close,
            "is_demo": settings.support_contact_is_demo,
        },
        contact_categories=[category.value for category in ContactCategory],
        contact_limits=CONTACT_LIMITS,
        contact_values=values or {},
        contact_errors=errors or {},
        contact_result=result,
    )
    response.status_code = status_code
    return response


# Validation error type -> catalog key (messages are generic: no input or internals are echoed).
CONTACT_ERROR_KEYS = {
    "missing": "contact.error.required",
    "string_too_short": "contact.error.too_short",
    "too_short": "contact.error.too_short",
    "string_too_long": "contact.error.too_long",
    "too_long": "contact.error.too_long",
    "value_error": "contact.error.email",
    "enum": "contact.error.category",
    "html_not_allowed": "contact.error.html",
    "line_break_not_allowed": "contact.error.line_break",
    "control_characters": "contact.error.control",
}


def contact_errors(exc: ValidationError, t: Any) -> dict[str, str]:
    """First error per field, as a Spanish message from the catalog."""
    errors: dict[str, str] = {}
    for error in exc.errors():
        field = str(error["loc"][0]) if error["loc"] else ""
        if field not in CONTACT_FIELDS or field in errors:
            continue
        # Consent: missing, empty or anything other than an explicit "yes" gets the same message.
        key = (
            "contact.error.privacy"
            if field == "privacy_accepted"
            else CONTACT_ERROR_KEYS.get(error["type"], "contact.error.invalid")
        )
        if key == "contact.error.too_short" and not str(error.get("input") or "").strip():
            key = "contact.error.required"
        minimum, maximum = CONTACT_LIMITS.get(field, (0, 0))
        errors[field] = t(key, min=minimum, max=maximum)
    return errors


@router.get("/legal", response_class=HTMLResponse)
def legal_page(request: Request, user: OptionalUserDep, settings: SettingsDep) -> Response:
    return render(request, "legal.html", user, settings)


@router.get("/privacidad", response_class=HTMLResponse)
def privacy_page(request: Request, user: OptionalUserDep, settings: SettingsDep) -> Response:
    return render(request, "privacy.html", user, settings)
