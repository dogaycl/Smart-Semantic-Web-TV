import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import httpx
from starlette import status

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Validation error.", "errors": exc.errors()},
        )

    @app.exception_handler(httpx.HTTPError)
    async def upstream_exception_handler(_, exc: httpx.HTTPError) -> JSONResponse:
        logger.warning("Upstream provider request failed: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "An upstream content provider is temporarily unavailable."},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled application error", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Unexpected server error."},
        )
