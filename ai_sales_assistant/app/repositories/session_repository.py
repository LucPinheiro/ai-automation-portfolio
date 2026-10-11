from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.user_session import UserSession


class SessionRepository:
    """Persistence operations for login sessions. Flushes but never commits."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, user_session: UserSession) -> UserSession:
        self._session.add(user_session)
        self._session.flush()
        return user_session

    def get_by_token_hash(self, token_hash: str) -> UserSession | None:
        return self._session.scalar(select(UserSession).where(UserSession.token_hash == token_hash))

    def delete(self, user_session: UserSession) -> None:
        self._session.delete(user_session)
        self._session.flush()

    def delete_all_for_user(self, user_id: int) -> None:
        self._session.execute(delete(UserSession).where(UserSession.user_id == user_id))

    def delete_expired_for_user(self, user_id: int, now: datetime) -> None:
        self._session.execute(
            delete(UserSession).where(UserSession.user_id == user_id, UserSession.expires_at <= now)
        )

    def delete_all_for_users(self, user_ids: list[int]) -> None:
        if user_ids:
            self._session.execute(delete(UserSession).where(UserSession.user_id.in_(user_ids)))
