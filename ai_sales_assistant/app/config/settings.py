from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Sales Assistant"
    app_version: str = "0.1.0"
    environment: Literal["development", "testing", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    database_url: str = "sqlite:///./ai_sales_assistant.db"

    ai_provider: Literal["openai", "ollama"] = "openai"
    # SecretStr keeps the key out of repr(), str() and logs.
    openai_api_key: SecretStr | None = None
    openai_model: str = Field(default="gpt-4o-mini", min_length=1)
    openai_timeout_seconds: float = Field(default=30.0, gt=0)
    openai_max_output_tokens: int = Field(default=1200, gt=0)

    # Local models are slower than hosted APIs, hence the longer default timeout.
    ollama_base_url: str = Field(default="http://localhost:11434", min_length=1)
    ollama_model: str = Field(default="llama3.2:3b", min_length=1)
    ollama_timeout_seconds: float = Field(default=120.0, gt=0)
    ollama_max_output_tokens: int = Field(default=1200, gt=0)

    # Authentication (server-side sessions identified by an HttpOnly cookie).
    session_cookie_name: str = Field(default="ai_sales_session", min_length=1)
    session_ttl_hours: int = Field(default=168, gt=0)
    # None means: Secure cookie in production, plain cookie in development/testing (http://localhost).
    session_cookie_secure: bool | None = None
    password_reset_ttl_minutes: int = Field(default=30, gt=0)
    # Guest mode: try the app without an account. Guests get a short session, a generation limit
    # (AI calls cost money with OpenAI) and their data is deleted when they log out or expire.
    guest_mode_enabled: bool = True
    guest_session_ttl_hours: int = Field(default=24, gt=0)
    guest_max_generations: int = Field(default=10, gt=0)
    # Public demo credentials shown on the login page. They are not an account: they open a guest
    # session (same limits and isolation). Nothing is stored in the database for them.
    demo_login_enabled: bool = True
    # Mandatory commercial terms (prices, discounts, scales...): after generating, the app checks
    # that every term is in the text and asks the model again up to this many times. Strict mode
    # rejects (502) a text that still misses terms; by default it is saved with a visible warning.
    commercial_terms_max_retries: int = Field(default=1, ge=0, le=3)
    commercial_terms_strict: bool = False
    demo_username: str = Field(default="demo", min_length=1)
    demo_password: str = Field(default="demo123", min_length=1)
    # Public URL of the app, used in password reset links and as a trusted origin for the CSRF check.
    app_base_url: str = Field(default="http://127.0.0.1:8000", min_length=1)
    # Support details shown on /contacto. DEMO VALUES: replace them with the real ones when they
    # exist (SUPPORT_EMAIL, SUPPORT_PHONE, SUPPORT_HOURS_*), then set SUPPORT_CONTACT_IS_DEMO=false.
    # An empty email or phone is not shown (the page says it will be published soon).
    support_email: str | None = "soporte@aisalesassistant.demo"
    support_phone: str | None = "+34 600 123 456"
    support_hours_open: str = "09:00"
    support_hours_close: str = "18:00"
    support_contact_is_demo: bool = True
    # Footer buttons: email and WhatsApp reuse SUPPORT_EMAIL / SUPPORT_PHONE; GitHub uses this URL.
    # An empty value hides its button.
    github_url: str | None = "https://github.com/LucPinheiro"
    # Contact form: "demo" validates the message but sends and stores nothing. Real delivery
    # (reusing app.services.email with SMTP, a real inbox and rate limiting) is a later phase.
    contact_form_mode: Literal["demo"] = "demo"

    # Email: "console" logs messages (development only); "smtp" sends them.
    email_backend: Literal["console", "smtp"] = "console"
    email_from: str = Field(default="AI Sales Assistant <no-reply@localhost>", min_length=3)
    smtp_host: str = "localhost"
    smtp_port: int = Field(default=587, gt=0)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_use_tls: bool = True
    smtp_timeout_seconds: float = Field(default=10.0, gt=0)

    @field_validator(
        "openai_api_key",
        "smtp_password",
        "smtp_username",
        "session_cookie_secure",
        "support_email",
        "support_phone",
        "github_url",
        mode="before",
    )
    @classmethod
    def _blank_is_missing(cls, value: object) -> object:
        # `OPENAI_API_KEY=` (or any of these left empty) in .env means "not configured", not an empty value.
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def _console_email_only_outside_production(self) -> "Settings":
        # The console backend writes password reset links to the log: never acceptable in production.
        if self.environment == "production" and self.email_backend == "console":
            raise ValueError("EMAIL_BACKEND=console is not allowed in production; configure EMAIL_BACKEND=smtp.")
        return self

    @property
    def session_cookie_is_secure(self) -> bool:
        if self.session_cookie_secure is not None:
            return self.session_cookie_secure
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
