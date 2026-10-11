import logging
from urllib.parse import urlencode

from app.services.email.base import EmailMessage, EmailSender

logger = logging.getLogger(__name__)


def password_reset_email(*, to: str, name: str, base_url: str, token: str, ttl_minutes: int) -> EmailMessage:
    link = f"{base_url.rstrip('/')}/reset-password?{urlencode({'token': token})}"
    body = (
        f"Hola {name},\n\n"
        "Hemos recibido una solicitud para restablecer la contraseña de tu cuenta de AI Sales Assistant.\n\n"
        f"Abre este enlace para elegir una contraseña nueva (caduca en {ttl_minutes} minutos y solo se puede usar una vez):\n"
        f"{link}\n\n"
        "Si no has sido tú, ignora este mensaje: tu contraseña no cambiará.\n"
    )
    return EmailMessage(to=to, subject="Restablece tu contraseña de AI Sales Assistant", body=body)


def send_safely(sender: EmailSender, message: EmailMessage) -> None:
    """Background-task wrapper: a delivery failure is logged, never shown to the requester."""
    try:
        sender.send(message)
    except Exception:
        logger.exception("Could not send email %r", message.subject)
