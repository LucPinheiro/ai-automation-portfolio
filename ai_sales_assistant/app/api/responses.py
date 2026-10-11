from typing import Any

from fastapi import status

from app.core.exceptions import (
    AIProviderError,
    AIProviderNotConfiguredError,
    AppError,
    UnauthorizedError,
)
from app.schemas.errors import ErrorResponse


def _example(code: str, message: str, details: list[dict[str, str]] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or []}}


_DOCS: dict[int, tuple[str, dict[str, Any]]] = {
    status.HTTP_400_BAD_REQUEST: (
        "Malformed request (e.g. invalid JSON body)",
        _example("invalid_json", "The request body is not valid JSON."),
    ),
    status.HTTP_401_UNAUTHORIZED: (
        "Not authenticated: missing, invalid or expired session cookie",
        _example(UnauthorizedError.code, UnauthorizedError.default_message),
    ),
    status.HTTP_403_FORBIDDEN: (
        "Forbidden: cross-site request (CSRF check) or action not allowed for this account (e.g. guest limits)",
        _example("csrf_failed", "The request origin is not allowed."),
    ),
    status.HTTP_409_CONFLICT: (
        "Conflict with existing data",
        _example("email_already_registered", "An account with this email already exists."),
    ),
    status.HTTP_404_NOT_FOUND: (
        "Resource not found",
        _example("not_found", "Generation 999 was not found."),
    ),
    status.HTTP_422_UNPROCESSABLE_CONTENT: (
        "Validation error",
        _example(
            "validation_error",
            "The request contains invalid data.",
            [{"field": "customer", "message": "String should have at least 1 character", "type": "string_too_short"}],
        ),
    ),
    status.HTTP_500_INTERNAL_SERVER_ERROR: (
        "Unexpected server error (details are logged, never returned)",
        _example("internal_error", AppError.default_message),
    ),
    status.HTTP_502_BAD_GATEWAY: (
        "The AI provider failed (timeout, rate limit, invalid credentials, empty response...)",
        _example(AIProviderError.code, AIProviderError.default_message),
    ),
    status.HTTP_503_SERVICE_UNAVAILABLE: (
        "The AI provider is not configured (missing OPENAI_API_KEY)",
        _example(AIProviderNotConfiguredError.code, AIProviderNotConfiguredError.default_message),
    ),
}


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI `responses` entries documenting the common error format."""
    # String keys so FastAPI replaces its default 422 schema instead of adding a second one.
    return {
        str(code): {
            "model": ErrorResponse,
            "description": _DOCS[code][0],
            "content": {"application/json": {"example": _DOCS[code][1]}},
        }
        for code in status_codes
    }
