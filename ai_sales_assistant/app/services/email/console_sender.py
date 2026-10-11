import logging

from app.services.email.base import EmailMessage

logger = logging.getLogger(__name__)


class ConsoleEmailSender:
    """Development backend: writes the email to the server log instead of sending it.

    It lets the password reset flow be tested without SMTP. Settings refuse it in production,
    because reset links are secrets.
    """

    def send(self, message: EmailMessage) -> None:
        logger.warning(
            "EMAIL_BACKEND=console (not sent)\nTo: %s\nSubject: %s\n\n%s", message.to, message.subject, message.body
        )
