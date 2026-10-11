from app.config import Settings
from app.services.email.base import EmailSender
from app.services.email.console_sender import ConsoleEmailSender
from app.services.email.smtp_sender import SmtpEmailSender


def create_email_sender(settings: Settings) -> EmailSender:
    if settings.email_backend == "smtp":
        return SmtpEmailSender(
            host=settings.smtp_host,
            port=settings.smtp_port,
            sender=settings.email_from,
            username=settings.smtp_username,
            password=settings.smtp_password,
            use_tls=settings.smtp_use_tls,
            timeout=settings.smtp_timeout_seconds,
        )
    return ConsoleEmailSender()
