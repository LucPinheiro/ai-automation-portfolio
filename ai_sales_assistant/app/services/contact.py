"""Contact form handling.

Only the "demo" mode exists for now: the message has been validated (ContactMessage) and is then
discarded. Nothing is sent, stored or logged, so no personal data is kept.

Next phase ("email" mode): build an app.services.email.EmailMessage to a real support inbox with
Reply-To set to the sender, and send it in the background with the existing EmailSender (SMTP),
together with rate limiting and an anti-spam honeypot. Name and subject are already guaranteed to
be single-line and HTML-free, so they are safe to use in email headers.
"""

from dataclasses import dataclass
from typing import Literal

from app.schemas.contact import ContactMessage

ContactMode = Literal["demo"]


@dataclass(frozen=True)
class ContactResult:
    delivered: bool
    mode: ContactMode


class ContactService:
    def __init__(self, mode: ContactMode = "demo") -> None:
        self._mode = mode

    def submit(self, message: ContactMessage) -> ContactResult:
        # Demo: validated, never sent. The page must say so instead of pretending it was sent.
        del message
        return ContactResult(delivered=False, mode=self._mode)
