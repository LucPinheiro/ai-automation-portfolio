import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.constants import GUEST_NAME
from app.core.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidCurrentPasswordError,
    InvalidResetTokenError,
    UsernameAlreadyTakenError,
)
from app.core.security import (
    burn_password_check,
    generate_token,
    hash_password,
    hash_token,
    password_needs_rehash,
    verify_password,
)
from app.database.types import utc_now
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.models.user_session import UserSession
from app.repositories.generation_repository import GenerationRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IssuedSession:
    """A new login session. `token` goes into the cookie and is never stored."""

    user: User
    token: str
    expires_at: datetime


@dataclass(frozen=True)
class PasswordResetRequest:
    """A reset token issued for an existing account. `token` is only sent by email."""

    user: User
    token: str


class AuthService:
    """Accounts, login sessions, guest sessions and password recovery.

    Guests are temporary users without credentials. Their data lives only as long as their
    session: logging out (or expiring) deletes the guest and its generations, while registering
    or logging in from a guest session moves the guest's generations to that account.
    """

    def __init__(
        self,
        session: Session,
        *,
        session_ttl: timedelta,
        reset_token_ttl: timedelta,
        guest_session_ttl: timedelta = timedelta(hours=24),
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._sessions = SessionRepository(session)
        self._reset_tokens = PasswordResetRepository(session)
        self._generations = GenerationRepository(session)
        self._session_ttl = session_ttl
        self._reset_token_ttl = reset_token_ttl
        self._guest_session_ttl = guest_session_ttl
        self._now = clock

    # --- Registration and login ------------------------------------------------------

    def register(
        self,
        *,
        name: str,
        email: str,
        password: str,
        username: str | None = None,
        guest_token: str | None = None,
    ) -> IssuedSession:
        """Create an account and log it in. A guest session behind `guest_token` is folded into it."""
        if self._users.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError()
        if username and self._users.get_by_username(username) is not None:
            raise UsernameAlreadyTakenError()
        user = User(
            name=name,
            email=email.strip().lower(),
            username=username.strip().lower() if username else None,
            password_hash=hash_password(password),
        )
        try:
            self._users.add(user)
            self._adopt_guest(guest_token, user)
            issued = self._issue_session(user)
            self._session.commit()
        except IntegrityError as exc:
            # Concurrent registrations with the same email or username: the unique constraints decide.
            self._session.rollback()
            if username and self._users.get_by_username(username) is not None:
                raise UsernameAlreadyTakenError() from exc
            raise EmailAlreadyRegisteredError() from exc
        except SQLAlchemyError:
            self._session.rollback()
            raise
        logger.info("User %s registered", user.id)
        return issued

    def login(self, *, identifier: str, password: str, guest_token: str | None = None) -> IssuedSession:
        """Log in with email or username. A guest session behind `guest_token` is folded into the account."""
        user = self._users.get_by_login(identifier)
        if user is None or user.password_hash is None:
            burn_password_check(password)
            raise InvalidCredentialsError()
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
        password_hash = user.password_hash

        def operation() -> IssuedSession:
            if password_needs_rehash(password_hash):
                user.password_hash = hash_password(password)
            self._sessions.delete_expired_for_user(user.id, self._now())
            self._adopt_guest(guest_token, user)
            return self._issue_session(user)

        issued = self._commit(operation)
        logger.info("User %s logged in", user.id)
        return issued

    def authenticate(self, token: str | None) -> User | None:
        """The user owning a valid, unexpired session token, or None."""
        if not token:
            return None
        user_session = self._sessions.get_by_token_hash(hash_token(token))
        if user_session is None or user_session.expires_at <= self._now():
            return None
        return user_session.user

    def logout(self, token: str | None) -> None:
        """Close the session. For a guest, the guest and all its generations are deleted."""
        if not token:
            return
        user_session = self._sessions.get_by_token_hash(hash_token(token))
        if user_session is None:
            return
        if user_session.user.is_guest:
            guest_id = user_session.user_id
            self._commit(lambda: self._discard_guests([guest_id]))
            logger.info("Guest %s logged out; its data was deleted", guest_id)
        else:
            self._commit(lambda: self._sessions.delete(user_session))

    # --- Guests ------------------------------------------------------------------------------

    def start_guest_session(self, *, previous_token: str | None = None) -> IssuedSession:
        """Create a temporary guest user with a short session (no email, no password)."""
        now = self._now()

        def operation() -> IssuedSession:
            self._purge_expired_guests(now)
            # Switching from a registered account to guest mode closes that account's session here.
            previous = self._sessions.get_by_token_hash(hash_token(previous_token)) if previous_token else None
            if previous is not None and not previous.user.is_guest:
                self._sessions.delete(previous)
            guest = self._users.add(User(name=GUEST_NAME, is_guest=True))
            return self._issue_session(guest, ttl=self._guest_session_ttl)

        issued = self._commit(operation)
        logger.info("Guest %s started a session", issued.user.id)
        return issued

    def purge_expired_guests(self) -> int:
        """Delete guests whose sessions have all expired, with their generations. Returns how many."""
        return self._commit(lambda: self._purge_expired_guests(self._now()))

    # --- Passwords -----------------------------------------------------------------------

    def change_password(self, user: User, *, current_password: str, new_password: str) -> IssuedSession:
        if user.password_hash is None or not verify_password(current_password, user.password_hash):
            raise InvalidCurrentPasswordError()

        def operation() -> IssuedSession:
            self._set_password(user, new_password)
            # Every other session is closed; the caller gets a fresh one (no session fixation).
            self._sessions.delete_all_for_user(user.id)
            return self._issue_session(user)

        issued = self._commit(operation)
        logger.info("User %s changed their password", user.id)
        return issued

    def request_password_reset(self, email: str) -> PasswordResetRequest | None:
        """Issue a reset token, or return None for an unknown email (the caller must not reveal which)."""
        user = self._users.get_by_email(email)
        if user is None:
            return None
        token = generate_token()

        def operation() -> None:
            self._reset_tokens.delete_unused_for_user(user.id)
            self._reset_tokens.add(
                PasswordResetToken(
                    user_id=user.id,
                    token_hash=hash_token(token),
                    expires_at=self._now() + self._reset_token_ttl,
                )
            )

        self._commit(operation)
        logger.info("Password reset requested for user %s", user.id)
        return PasswordResetRequest(user=user, token=token)

    def reset_password(self, *, token: str, new_password: str) -> None:
        record = self._reset_tokens.get_by_token_hash(hash_token(token))
        now = self._now()
        if record is None or record.used_at is not None or record.expires_at <= now:
            raise InvalidResetTokenError()
        user = record.user

        def operation() -> None:
            self._set_password(user, new_password)
            record.used_at = now
            # Whoever may have had access to the account is logged out everywhere.
            self._sessions.delete_all_for_user(user.id)
            self._session.flush()

        self._commit(operation)
        logger.info("Password reset completed for user %s", user.id)

    # --- Helpers ---------------------------------------------------------------------------

    def _set_password(self, user: User, password: str) -> None:
        user.password_hash = hash_password(password)
        user.password_changed_at = self._now()

    def _purge_expired_guests(self, now: datetime) -> int:
        guest_ids = self._users.expired_guest_ids(now)
        self._discard_guests(guest_ids)
        return len(guest_ids)

    def _discard_guests(self, guest_ids: list[int]) -> None:
        # Explicit deletes, independent of ON DELETE CASCADE (not enforced by SQLite by default).
        self._generations.delete_all_for_users(guest_ids)
        self._sessions.delete_all_for_users(guest_ids)
        self._users.delete_by_ids(guest_ids)

    def _adopt_guest(self, guest_token: str | None, user: User) -> None:
        """Move the generations of the guest behind `guest_token` to `user`, then delete the guest.

        Only the browser holding the guest's HttpOnly cookie can do this, so it proves ownership.
        """
        if not guest_token:
            return
        guest_session = self._sessions.get_by_token_hash(hash_token(guest_token))
        if guest_session is None or not guest_session.user.is_guest or guest_session.user_id == user.id:
            return
        guest_id = guest_session.user_id
        moved = self._generations.transfer(from_user_id=guest_id, to_user_id=user.id)
        self._discard_guests([guest_id])
        logger.info("Guest %s merged into user %s (%s generations)", guest_id, user.id, moved)

    def _issue_session(self, user: User, ttl: timedelta | None = None) -> IssuedSession:
        token = generate_token()
        expires_at = self._now() + (ttl or self._session_ttl)
        self._sessions.add(UserSession(user_id=user.id, token_hash=hash_token(token), expires_at=expires_at))
        return IssuedSession(user=user, token=token, expires_at=expires_at)

    def _commit[T](self, operation: Callable[[], T]) -> T:
        try:
            result = operation()
            self._session.commit()
        except SQLAlchemyError:
            self._session.rollback()
            raise
        return result
