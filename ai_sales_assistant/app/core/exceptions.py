from fastapi import status


class AppError(Exception):
    """Base class for errors that are safe to expose to API clients.

    `message` is always returned to the client, so it must never contain
    secrets, stack traces or provider internals.
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "internal_error"
    default_message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class BadRequestError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "bad_request"
    default_message = "The request could not be processed."


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"
    default_message = "The requested resource was not found."


class AIProviderError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
    code = "ai_provider_error"
    default_message = "The AI provider could not generate the content. Please try again later."


class AIProviderNotConfiguredError(AIProviderError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "ai_provider_not_configured"
    default_message = "The AI provider is not configured."


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "not_authenticated"
    default_message = "Authentication is required."


class InvalidCredentialsError(UnauthorizedError):
    # Same message whether the email exists or not, to prevent user enumeration.
    code = "invalid_credentials"
    default_message = "Invalid email or password."


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"
    default_message = "You are not allowed to perform this action."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"
    default_message = "The request conflicts with the current state of the resource."


class EmailAlreadyRegisteredError(ConflictError):
    code = "email_already_registered"
    default_message = "An account with this email already exists."


class InvalidCurrentPasswordError(BadRequestError):
    code = "invalid_current_password"
    default_message = "The current password is incorrect."


class InvalidResetTokenError(BadRequestError):
    # One message for unknown, used and expired tokens.
    code = "invalid_or_expired_token"
    default_message = "The password reset link is invalid or has expired."


class UsernameAlreadyTakenError(ConflictError):
    code = "username_already_taken"
    default_message = "This username is already taken."


class GuestNotAllowedError(ForbiddenError):
    code = "guest_not_allowed"
    default_message = "This action requires a registered account."


class GuestModeDisabledError(ForbiddenError):
    code = "guest_mode_disabled"
    default_message = "Guest access is disabled."


class GuestQuotaExceededError(ForbiddenError):
    code = "guest_quota_exceeded"
    default_message = "Guest generation limit reached. Create an account to keep generating."


class CommercialTermsMissingError(AIProviderError):
    """Strict mode only: the generated text omitted mandatory commercial terms even after a retry."""

    code = "commercial_terms_missing"
    default_message = "The generated text omitted mandatory commercial terms. Please try again."

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(f"{self.default_message} Missing: " + " | ".join(missing))
