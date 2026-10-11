from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    body: str


class EmailSender(Protocol):
    """Sends transactional emails. Implementations: console (development) and SMTP."""

    def send(self, message: EmailMessage) -> None: ...
