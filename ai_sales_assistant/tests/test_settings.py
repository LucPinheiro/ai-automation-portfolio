import pytest

from app.config import Settings

SECRET_KEY = "sk-proj-super-secret-key"


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "DATABASE_URL",
        "AI_PROVIDER",
        "OLLAMA_BASE_URL",
        "OLLAMA_MODEL",
        "OLLAMA_TIMEOUT_SECONDS",
        "OLLAMA_MAX_OUTPUT_TOKENS",
        "ENVIRONMENT",
        "EMAIL_BACKEND",
        "SESSION_COOKIE_SECURE",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)


def load_settings() -> Settings:
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_openai_settings_are_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", SECRET_KEY)
    monkeypatch.setenv("OPENAI_MODEL", "gpt-custom")
    monkeypatch.setenv("OPENAI_TIMEOUT_SECONDS", "12.5")

    settings = load_settings()

    assert settings.openai_api_key is not None
    assert settings.openai_api_key.get_secret_value() == SECRET_KEY
    assert settings.openai_model == "gpt-custom"
    assert settings.openai_timeout_seconds == 12.5


def test_api_key_is_optional() -> None:
    assert load_settings().openai_api_key is None


@pytest.mark.parametrize("value", ["", "   "])
def test_blank_api_key_is_treated_as_missing(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", value)

    assert load_settings().openai_api_key is None


def test_api_key_is_hidden_from_repr_and_serialization(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", SECRET_KEY)

    settings = load_settings()

    assert SECRET_KEY not in repr(settings)
    assert SECRET_KEY not in str(settings.model_dump())
    assert SECRET_KEY not in settings.model_dump_json()


def test_ai_provider_defaults_to_openai() -> None:
    assert load_settings().ai_provider == "openai"


def test_ollama_defaults() -> None:
    settings = load_settings()

    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.ollama_model == "llama3.2:3b"
    assert settings.ollama_timeout_seconds == 120
    assert settings.ollama_max_output_tokens == 1200


def test_ollama_settings_are_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://gpu-box:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.1:8b")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("OLLAMA_MAX_OUTPUT_TOKENS", "600")

    settings = load_settings()

    assert settings.ai_provider == "ollama"
    assert settings.ollama_base_url == "http://gpu-box:11434"
    assert settings.ollama_model == "llama3.1:8b"
    assert settings.ollama_timeout_seconds == 45
    assert settings.ollama_max_output_tokens == 600


def test_unsupported_ai_provider_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "unknown")

    with pytest.raises(ValueError):
        load_settings()


def test_authentication_defaults() -> None:
    settings = load_settings()

    assert settings.session_cookie_name == "ai_sales_session"
    assert settings.session_ttl_hours == 168
    assert settings.password_reset_ttl_minutes == 30
    assert settings.email_backend == "console"
    assert settings.session_cookie_is_secure is False  # development default


@pytest.mark.parametrize(
    ("environment", "explicit", "expected"),
    [("production", None, True), ("development", None, False), ("development", "true", True), ("production", "false", False)],
)
def test_session_cookie_secure_flag(
    monkeypatch: pytest.MonkeyPatch, environment: str, explicit: str | None, expected: bool
) -> None:
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("EMAIL_BACKEND", "smtp")
    if explicit is not None:
        monkeypatch.setenv("SESSION_COOKIE_SECURE", explicit)

    assert load_settings().session_cookie_is_secure is expected


def test_blank_optional_auth_settings_are_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("SESSION_COOKIE_SECURE", "SMTP_USERNAME", "SMTP_PASSWORD"):
        monkeypatch.setenv(name, "")

    settings = load_settings()

    assert (settings.session_cookie_secure, settings.smtp_username, settings.smtp_password) == (None, None, None)


def test_smtp_password_is_hidden(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_PASSWORD", "smtp-secret")

    settings = load_settings()

    assert "smtp-secret" not in repr(settings)
    assert "smtp-secret" not in settings.model_dump_json()
