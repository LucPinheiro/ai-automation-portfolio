import logging
import smtplib

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.services.email import EmailMessage, create_email_sender, password_reset_email, send_safely
from app.services.email.console_sender import ConsoleEmailSender
from app.services.email.smtp_sender import SmtpEmailSender


def make_settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


def test_console_backend_is_the_default() -> None:
    assert isinstance(create_email_sender(make_settings()), ConsoleEmailSender)


def test_smtp_backend_is_built_from_settings() -> None:
    sender = create_email_sender(
        make_settings(email_backend="smtp", smtp_host="mail.example.com", smtp_port=2525, smtp_username="user")
    )

    assert isinstance(sender, SmtpEmailSender)
    assert (sender._host, sender._port, sender._username) == ("mail.example.com", 2525, "user")


def test_console_backend_is_refused_in_production() -> None:
    with pytest.raises(ValidationError, match="EMAIL_BACKEND=console is not allowed in production"):
        make_settings(environment="production", email_backend="console")


def test_console_sender_logs_the_message(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        ConsoleEmailSender().send(EmailMessage(to="maria@example.com", subject="Hola", body="Enlace: X"))

    assert "maria@example.com" in caplog.text
    assert "Enlace: X" in caplog.text


def test_smtp_sender_uses_starttls_and_login(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: float) -> None:
            calls.append(f"connect {host}:{port}")

        def __enter__(self) -> "FakeSMTP":
            return self

        def __exit__(self, *args: object) -> None:
            calls.append("quit")

        def starttls(self) -> None:
            calls.append("starttls")

        def login(self, username: str, password: str) -> None:
            calls.append(f"login {username}")

        def send_message(self, message) -> None:
            calls.append(f"send to={message['To']}")

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    sender = create_email_sender(
        make_settings(email_backend="smtp", smtp_host="mail", smtp_port=587, smtp_username="u", smtp_password="p")
    )

    sender.send(EmailMessage(to="maria@example.com", subject="S", body="B"))

    assert calls == ["connect mail:587", "starttls", "login u", "send to=maria@example.com", "quit"]


def test_reset_email_contains_a_link_with_the_token() -> None:
    message = password_reset_email(
        to="maria@example.com", name="María", base_url="https://app.example.com/", token="abc-123_x", ttl_minutes=30
    )

    assert message.to == "maria@example.com"
    assert "https://app.example.com/reset-password?token=abc-123_x" in message.body
    assert "30 minutos" in message.body


def test_send_safely_logs_delivery_failures(caplog: pytest.LogCaptureFixture) -> None:
    class BrokenSender:
        def send(self, message: EmailMessage) -> None:
            raise ConnectionError("SMTP down")

    send_safely(BrokenSender(), EmailMessage(to="a@example.com", subject="Asunto", body="B"))

    assert "Could not send email" in caplog.text
