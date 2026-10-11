from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from fastapi import FastAPI, Request, Response, status

from app.config import get_settings
from app.core.error_handlers import error_response

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    # The app never needs to be framed; this blocks clickjacking of the login and account pages.
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
}

CallNext = Callable[[Request], Awaitable[Response]]


def origin_of(url: str) -> str | None:
    """`scheme://host[:port]` of a URL, lowercased; None for opaque values such as "null"."""
    parts = urlsplit(url.strip())
    if not parts.scheme or not parts.netloc:
        return None
    return f"{parts.scheme}://{parts.netloc}".lower()


def trusted_origins(request: Request) -> set[str]:
    origins = {origin_of(str(request.base_url)), origin_of(get_settings().app_base_url)}
    return {origin for origin in origins if origin}


async def reject_cross_site_writes(request: Request, call_next: CallNext) -> Response:
    """CSRF protection for the cookie-authenticated API.

    Browsers send `Origin` (or at least `Referer`) on every cross-site POST/PUT/DELETE, so a
    state-changing request whose source is another site is rejected. Together with the
    SameSite=Lax session cookie and JSON-only bodies, this blocks cross-site request forgery.
    Requests without either header (curl, server-to-server) carry no ambient browser cookies.
    """
    if request.method not in SAFE_METHODS:
        source = request.headers.get("origin") or request.headers.get("referer")
        if source is not None and origin_of(source) not in trusted_origins(request):
            return error_response(status.HTTP_403_FORBIDDEN, "csrf_failed", "The request origin is not allowed.")
    return await call_next(request)


async def add_security_headers(request: Request, call_next: CallNext) -> Response:
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        # Routes may set a stricter value (e.g. the reset page uses Referrer-Policy: no-referrer).
        response.headers.setdefault(header, value)
    path = request.url.path
    if path.startswith("/static/") and not path.startswith("/static/vendor/"):
        # Our own JS/CSS change with the app: the browser must revalidate (a cheap 304 when unchanged)
        # instead of reusing an outdated module that no longer matches the HTML or the API.
        response.headers.setdefault("Cache-Control", "no-cache")
    return response


def register_middleware(app: FastAPI) -> None:
    # Registered last = runs first: security headers wrap every response, including CSRF rejections.
    app.middleware("http")(reject_cross_site_writes)
    app.middleware("http")(add_security_headers)
