from datetime import timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.core.exceptions import GuestNotAllowedError, UnauthorizedError
from app.database import get_db
from app.models.user import User
from app.repositories.generation_repository import GenerationRepository
from app.services.ai import AIProvider, create_ai_provider
from app.services.auth_service import AuthService
from app.services.email import EmailSender, create_email_sender
from app.services.generation_service import AIProviderResolver, GenerationService

SessionDep = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@lru_cache
def get_ai_provider() -> AIProvider:
    """Process-wide provider instance, so its HTTP connection pool is reused.

    Failures (e.g. a missing API key) are not cached and are retried on the next call.
    """
    return create_ai_provider(get_settings())


def get_ai_provider_resolver() -> AIProviderResolver:
    return get_ai_provider


def get_generation_service(
    session: SessionDep,
    settings: SettingsDep,
    resolve_ai_provider: Annotated[AIProviderResolver, Depends(get_ai_provider_resolver)],
) -> GenerationService:
    return GenerationService(
        session=session,
        repository=GenerationRepository(session),
        resolve_ai_provider=resolve_ai_provider,
        commercial_terms_max_retries=settings.commercial_terms_max_retries,
        commercial_terms_strict=settings.commercial_terms_strict,
    )


GenerationServiceDep = Annotated[GenerationService, Depends(get_generation_service)]


# --- Authentication ---------------------------------------------------------------------


def get_auth_service(session: SessionDep, settings: SettingsDep) -> AuthService:
    return AuthService(
        session,
        session_ttl=timedelta(hours=settings.session_ttl_hours),
        reset_token_ttl=timedelta(minutes=settings.password_reset_ttl_minutes),
        guest_session_ttl=timedelta(hours=settings.guest_session_ttl_hours),
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def session_token(request: Request, settings: SettingsDep) -> str | None:
    return request.cookies.get(settings.session_cookie_name)


SessionTokenDep = Annotated[str | None, Depends(session_token)]


def get_optional_user(auth: AuthServiceDep, token: SessionTokenDep) -> User | None:
    return auth.authenticate(token)


OptionalUserDep = Annotated[User | None, Depends(get_optional_user)]


def get_current_user(user: OptionalUserDep) -> User:
    """The logged-in user; 401 when the session cookie is missing, unknown or expired."""
    if user is None:
        raise UnauthorizedError()
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def get_registered_user(user: CurrentUserDep) -> User:
    """A logged-in, registered user; guests get 403 (e.g. they have no password to change)."""
    if user.is_guest:
        raise GuestNotAllowedError()
    return user


RegisteredUserDep = Annotated[User, Depends(get_registered_user)]


@lru_cache
def get_email_sender() -> EmailSender:
    return create_email_sender(get_settings())


EmailSenderDep = Annotated[EmailSender, Depends(get_email_sender)]
