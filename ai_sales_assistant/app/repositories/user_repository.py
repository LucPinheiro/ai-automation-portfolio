from datetime import datetime

from sqlalchemy import delete, exists, select, update
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_session import UserSession


class UserRepository:
    """Persistence operations for `User`. Flushes but never commits (the service owns transactions)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, user: User) -> User:
        self._session.add(user)
        self._session.flush()
        return user

    def get_by_id(self, user_id: int) -> User | None:
        return self._session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self._session.scalar(select(User).where(User.email == email.strip().lower()))

    def get_by_username(self, username: str) -> User | None:
        return self._session.scalar(select(User).where(User.username == username.strip().lower()))

    def get_by_login(self, identifier: str) -> User | None:
        """A registered user by email (when it contains "@") or username. Guests never match."""
        identifier = identifier.strip().lower()
        column = User.email if "@" in identifier else User.username
        return self._session.scalar(select(User).where(column == identifier, User.is_guest.is_(False)))

    def delete(self, user: User) -> None:
        self._session.delete(user)
        self._session.flush()

    def ai_generation_count(self, user_id: int) -> int:
        return self._session.scalar(select(User.ai_generation_count).where(User.id == user_id)) or 0

    def increment_ai_generation_count(self, user_id: int, by: int = 1) -> None:
        self._session.execute(
            update(User).where(User.id == user_id).values(ai_generation_count=User.ai_generation_count + by)
        )

    def expired_guest_ids(self, now: datetime) -> list[int]:
        """Guests without any unexpired session: nobody can use them any more."""
        active_session = exists().where(UserSession.user_id == User.id, UserSession.expires_at > now)
        return list(self._session.scalars(select(User.id).where(User.is_guest.is_(True), ~active_session)))

    def delete_by_ids(self, user_ids: list[int]) -> None:
        if user_ids:
            self._session.execute(delete(User).where(User.id.in_(user_ids)))
