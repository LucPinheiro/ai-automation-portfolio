from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.password_reset_token import PasswordResetToken


class PasswordResetRepository:
    """Persistence operations for password reset tokens. Flushes but never commits."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, token: PasswordResetToken) -> PasswordResetToken:
        self._session.add(token)
        self._session.flush()
        return token

    def get_by_token_hash(self, token_hash: str) -> PasswordResetToken | None:
        return self._session.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))

    def delete_unused_for_user(self, user_id: int) -> None:
        # A new request supersedes older links that were never used.
        self._session.execute(
            delete(PasswordResetToken).where(
                PasswordResetToken.user_id == user_id, PasswordResetToken.used_at.is_(None)
            )
        )
