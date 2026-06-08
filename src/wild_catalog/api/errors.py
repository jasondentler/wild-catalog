import logging
import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from wild_catalog.core.errors import WildCatalogError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(WildCatalogError, wild_catalog_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)


async def wild_catalog_error_handler(
    request: Request,
    exc: WildCatalogError,
) -> JSONResponse:
    request_id = _get_or_create_request_id(request)

    logger.warning(
        "Wild Catalog request failed: code=%s status=%s request_id=%s detail=%s",
        exc.code,
        exc.status_code,
        request_id,
        exc.debug_detail or str(exc),
        exc_info=True,
    )

    return _error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.public_detail,
        request_id=request_id,
    )


async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    request_id = _get_or_create_request_id(request)

    logger.info(
        "Request validation failed: request_id=%s errors=%s",
        request_id,
        exc.errors(),
    )

    return _error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="bad_request",
        message="Request validation failed.",
        request_id=request_id,
    )


async def pydantic_validation_error_handler(
    request: Request,
    exc: ValidationError,
) -> JSONResponse:
    request_id = _get_or_create_request_id(request)

    logger.info(
        "Payload validation failed: request_id=%s errors=%s",
        request_id,
        exc.errors(),
    )

    return _error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="bad_request",
        message="Request payload validation failed.",
        request_id=request_id,
    )


async def unexpected_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    request_id = _get_or_create_request_id(request)

    logger.exception(
        "Unexpected API failure: request_id=%s",
        request_id,
    )

    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_server_error",
        message="Unexpected internal server error.",
        request_id=request_id,
    )


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
            }
        },
    )


def _get_or_create_request_id(request: Request) -> str:
    request_id = request.headers.get("x-request-id")

    if request_id:
        return request_id

    return uuid.uuid4().hex
