from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Integer, String, false
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import EMAIL_MAX_LENGTH, USER_NAME_MAX_LENGTH, USERNAME_MAX_LENGTH
from app.database.base import Base
from app.database.types import UTCDateTime, utc_now


class User(Base):
    """An account that owns generations: registered, or a temporary guest.

    Registered users log in with email or username and a password (only its Argon2id hash
    is stored). Guests have neither: they exist only while their session does.
    """

    __tablename__ = "users"
    __table_args__ = (
        # A registered account can never lose its credentials; only guests may lack them.
        CheckConstraint(
            "is_guest OR (email IS NOT NULL AND password_hash IS NOT NULL)", name="registered_has_credentials"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(USER_NAME_MAX_LENGTH))
    # Email and username are stored lowercased, so uniqueness is case-insensitive on every backend.
    email: Mapped[str | None] = mapped_column(String(EMAIL_MAX_LENGTH), unique=True)
    username: Mapped[str | None] = mapped_column(String(USERNAME_MAX_LENGTH), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_guest: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    # Successful AI calls (generate + regenerate); limits what a guest can spend.
    ai_generation_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    password_changed_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    def __repr__(self) -> str:
        # Never include the email or the password hash in logs.
        return f"User(id={self.id!r}, is_guest={self.is_guest!r})"
