"""Contact form message: categories, limits and validation (no HTML, no header injection)."""

import re
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field
from pydantic_core import PydanticCustomError


class ContactCategory(StrEnum):
    TECHNICAL = "soporte_tecnico"
    API = "api"
    ACCOUNT = "cuenta"
    BILLING = "facturacion"
    SALES = "comercial"
    OTHER = "otra"


# Field limits, shared by the schema, the form (maxlength) and the error messages.
CONTACT_LIMITS: dict[str, tuple[int, int]] = {
    "name": (2, 100),
    "email": (3, 254),
    "subject": (3, 150),
    "message": (10, 4000),
}
CONTACT_FIELDS = ("name", "email", "category", "subject", "message", "privacy_accepted")

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _no_html(value: str) -> str:
    # No markup of any kind: "<" and ">" are never needed in a support message.
    if "<" in value or ">" in value:
        raise PydanticCustomError("html_not_allowed", "HTML is not allowed.")
    if _CONTROL.search(value):
        raise PydanticCustomError("control_characters", "Control characters are not allowed.")
    return value


def _single_line(value: str) -> str:
    # A future email header (name, subject) must never contain line breaks (header injection).
    if "\n" in value or "\r" in value:
        raise PydanticCustomError("line_break_not_allowed", "Line breaks are not allowed.")
    return value


def _must_accept(value: bool) -> bool:
    # GDPR consent: an explicit, unticked-by-default checkbox the user must tick.
    if value is not True:
        raise PydanticCustomError("privacy_not_accepted", "The privacy policy must be accepted.")
    return value


def _normalise_newlines(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _limits(field: str) -> Field:
    minimum, maximum = CONTACT_LIMITS[field]
    return Field(min_length=minimum, max_length=maximum)


SingleLine = Annotated[str, AfterValidator(_single_line), AfterValidator(_no_html)]


class ContactMessage(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: Annotated[SingleLine, _limits("name")]
    email: Annotated[EmailStr, Field(max_length=CONTACT_LIMITS["email"][1])]
    category: ContactCategory
    subject: Annotated[SingleLine, _limits("subject")]
    message: Annotated[str, AfterValidator(_normalise_newlines), AfterValidator(_no_html), _limits("message")]
    privacy_accepted: Annotated[bool, AfterValidator(_must_accept)]
