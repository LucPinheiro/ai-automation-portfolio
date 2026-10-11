import logging
from collections.abc import Sequence
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError
from app.schemas.errors import ErrorBody, ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)

INVALID_JSON_ERROR_TYPE = "json_invalid"


def error_response(
    status_code: int, code: str, message: str, details: list[ErrorDetail] | None = None
) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details or []))
    return JSONResponse(status_code=status_code, content=body.model_dump())


def _field_from_location(location: Sequence[Any]) -> str | None:
    parts = [str(part) for part in location]
    if parts and parts[0] == "body":
        parts = parts[1:]
    return ".".join(parts) or None


def _validation_details(errors: Sequence[Any]) -> list[ErrorDetail]:
    # The submitted input is deliberately left out so it is never echoed back.
    return [
        ErrorDetail(field=_field_from_location(error["loc"]), message=error["msg"], type=error["type"])
        for error in errors
    ]


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    log = logger.error if exc.status_code >= 500 else logger.info
    log("Application error %s: %s", exc.code, exc.message)
    return error_response(exc.status_code, exc.code, exc.message)


async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    details = _validation_details(errors)
    if any(error["type"] == INVALID_JSON_ERROR_TYPE for error in errors):
        return error_response(
            status.HTTP_400_BAD_REQUEST, "invalid_json", "The request body is not valid JSON.", details
        )
    return error_response(
        status.HTTP_422_UNPROCESSABLE_CONTENT, "validation_error", "The request contains invalid data.", details
    )


async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    phrase = HTTPStatus(exc.status_code).phrase
    code = phrase.lower().replace(" ", "_").replace("-", "_")
    is_client_error = exc.status_code < 500 and isinstance(exc.detail, str)
    message = exc.detail if is_client_error else phrase
    return error_response(exc.status_code, code, message)


async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error", exc_info=exc)
    return error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR, "internal_error", "An unexpected error occurred."
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
