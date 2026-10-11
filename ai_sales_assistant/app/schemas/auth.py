from datetime import datetime
from typing import Annotated

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    ValidationInfo,
    field_validator,
)
from pydantic_core import PydanticCustomError

from app.core.constants import (
    EMAIL_MAX_LENGTH,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    USER_NAME_MAX_LENGTH,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
    USERNAME_PATTERN,
)

# Passwords are never stripped or otherwise altered: every character counts.
NewPassword = Annotated[
    str,
    Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
        description=f"Between {PASSWORD_MIN_LENGTH} and {PASSWORD_MAX_LENGTH} characters.",
    ),
]
# Existing passwords are only checked against the stored hash, so only the length cap applies.
AnyPassword = Annotated[str, Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)]
Email = Annotated[EmailStr, Field(max_length=EMAIL_MAX_LENGTH, examples=["maria@example.com"])]
Username = Annotated[
    str,
    StringConstraints(min_length=USERNAME_MIN_LENGTH, max_length=USERNAME_MAX_LENGTH, pattern=USERNAME_PATTERN),
    Field(
        description=(
            f"{USERNAME_MIN_LENGTH}-{USERNAME_MAX_LENGTH} characters: letters, digits, '.', '_' or '-'. "
            "Stored lowercased."
        ),
        examples=["maria.lopez"],
    ),
]


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _must_match(value: str, info: ValidationInfo, field: str) -> str:
    # Reported on the confirmation field, so the UI can show it next to that input.
    if field in info.data and value != info.data[field]:
        raise PydanticCustomError("password_mismatch", "Passwords do not match.")
    return value


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterRequest(_Request):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=USER_NAME_MAX_LENGTH)] = (
        Field(examples=["María López"])
    )
    email: Email
    username: Username | None = None
    password: NewPassword
    password_confirm: str = Field(max_length=PASSWORD_MAX_LENGTH)

    _normalize = field_validator("email", mode="before")(lambda value: _normalize_email(str(value)))

    @field_validator("username", mode="before")
    @classmethod
    def _normalize_username(cls, value: object) -> object:
        # The field is optional: an empty form input means "no username".
        if isinstance(value, str):
            value = value.strip().lower()
            return value or None
        return value

    @field_validator("password_confirm")
    @classmethod
    def _passwords_match(cls, value: str, info: ValidationInfo) -> str:
        return _must_match(value, info, "password")


class LoginRequest(_Request):
    # Username or email. `email` is still accepted as the key for existing API clients.
    identifier: str = Field(
        min_length=1,
        max_length=EMAIL_MAX_LENGTH,
        validation_alias=AliasChoices("identifier", "email"),
        description="Username or email.",
        examples=["maria@example.com"],
    )
    password: AnyPassword

    _normalize = field_validator("identifier", mode="before")(lambda value: _normalize_email(str(value)))


class ChangePasswordRequest(_Request):
    current_password: AnyPassword
    new_password: NewPassword
    new_password_confirm: str = Field(max_length=PASSWORD_MAX_LENGTH)

    @field_validator("new_password_confirm")
    @classmethod
    def _passwords_match(cls, value: str, info: ValidationInfo) -> str:
        return _must_match(value, info, "new_password")


class ForgotPasswordRequest(_Request):
    email: Email

    _normalize = field_validator("email", mode="before")(lambda value: _normalize_email(str(value)))


class ResetPasswordRequest(_Request):
    token: str = Field(min_length=1, max_length=256, description="Token from the password reset link.")
    new_password: NewPassword
    new_password_confirm: str = Field(max_length=PASSWORD_MAX_LENGTH)

    @field_validator("new_password_confirm")
    @classmethod
    def _passwords_match(cls, value: str, info: ValidationInfo) -> str:
        return _must_match(value, info, "new_password")


class UserRead(BaseModel):
    """The authenticated user. Never includes the password hash."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "name": "María López",
                    "email": "maria@example.com",
                    "username": "maria.lopez",
                    "is_guest": False,
                    "created_at": "2026-10-07T12:00:00Z",
                }
            ]
        },
    )

    id: int
    name: str
    email: str | None = Field(description="None for guests.")
    username: str | None = None
    is_guest: bool = Field(description="True for a temporary guest session (no email or password).")
    created_at: datetime


class MessageResponse(BaseModel):
    message: str
