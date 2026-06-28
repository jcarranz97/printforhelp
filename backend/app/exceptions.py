"""Application exception hierarchy and global FastAPI handlers.

Service-layer code raises subclasses of :class:`AppExceptionError`; the
handlers below convert any error into the standard ``{success, error}``
envelope documented in the API specification. Routers and services must
never raise ``HTTPException`` directly.
"""

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppExceptionError(Exception):
    """Base class for all domain exceptions."""

    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, object] | None = None,
    ) -> None:
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


def _envelope(
    code: str, message: str, details: dict[str, object] | None = None
) -> dict[str, object]:
    return {
        "success": False,
        "error": {"code": code, "message": message, "details": details or {}},
    }


async def app_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Render an :class:`AppExceptionError` as the standard envelope."""
    if not isinstance(exc, AppExceptionError):  # pragma: no cover - guard
        raise exc
    return JSONResponse(
        status_code=exc.status_code,
        content=_envelope(exc.error_code, exc.message, exc.details),
    )


async def http_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Render a raised ``HTTPException`` in the standard envelope."""
    if not isinstance(exc, StarletteHTTPException):  # pragma: no cover
        raise exc
    return JSONResponse(
        status_code=exc.status_code,
        content=_envelope("HTTP_ERROR", str(exc.detail)),
    )


async def validation_exception_handler(
    _request: Request, exc: Exception
) -> JSONResponse:
    """Render request validation failures as ``VALIDATION_ERROR``."""
    if not isinstance(exc, RequestValidationError):  # pragma: no cover
        raise exc
    return JSONResponse(
        status_code=422,
        content=_envelope(
            "VALIDATION_ERROR",
            "Request validation failed.",
            {"errors": exc.errors()},
        ),
    )


async def generic_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected errors."""
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=_envelope("INTERNAL_SERVER_ERROR", "An unexpected error occurred."),
    )
