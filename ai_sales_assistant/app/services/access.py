"""Ways into the app, shared by the JSON API and the HTML forms.

- Registered users: username/email + password (AuthService.login).
- Guest mode: "Entrar sin iniciar sesión", or the public demo credentials. The demo
  credentials are not an account: they open a guest session, so nothing about them is
  stored in the database and they get exactly the guest limits and isolation.
"""

import hmac
from dataclasses import dataclass

from app.config import Settings
from app.core.exceptions import GuestModeDisabledError
from app.models.user import User
from app.services.auth_service import AuthService, IssuedSession


@dataclass(frozen=True)
class SignIn:
    """The user now behind the browser. `issued` is None when the current session is kept."""

    user: User
    issued: IssuedSession | None


def _same(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def demo_login_available(settings: Settings) -> bool:
    return settings.guest_mode_enabled and settings.demo_login_enabled


def is_demo_login(settings: Settings, identifier: str, password: str) -> bool:
    if not demo_login_available(settings):
        return False
    # Evaluate both comparisons, so timing does not tell which part was wrong.
    username_ok = _same(identifier.strip().lower(), settings.demo_username.strip().lower())
    password_ok = _same(password, settings.demo_password)
    return username_ok and password_ok


def enter_guest_mode(auth: AuthService, settings: Settings, token: str | None) -> SignIn:
    """Start a guest session, or keep the current one if the browser is already a guest."""
    if not settings.guest_mode_enabled:
        raise GuestModeDisabledError()
    current = auth.authenticate(token)
    if current is not None and current.is_guest:
        return SignIn(user=current, issued=None)
    issued = auth.start_guest_session(previous_token=token)
    return SignIn(user=issued.user, issued=issued)


def sign_in(auth: AuthService, settings: Settings, *, identifier: str, password: str, token: str | None) -> SignIn:
    """Log in with real credentials, or enter guest mode with the demo credentials."""
    if is_demo_login(settings, identifier, password):
        return enter_guest_mode(auth, settings, token)
    issued = auth.login(identifier=identifier, password=password, guest_token=token)
    return SignIn(user=issued.user, issued=issued)


def is_reserved_username(settings: Settings, username: str | None) -> bool:
    """The demo username can never belong to a real account."""
    return bool(username) and username.strip().lower() == settings.demo_username.strip().lower()
