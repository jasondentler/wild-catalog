from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError

from wild_catalog.api.errors import (
    _error_response,
    _get_or_create_request_id,
    pydantic_validation_error_handler,
    register_exception_handlers,
    request_validation_error_handler,
    unexpected_error_handler,
    wild_catalog_error_handler,
)
from wild_catalog.core.errors import ContentLengthHeaderIsNotNumberError


def make_request(headers: dict[str, str] | None = None) -> Request:
    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    raw_headers = [(key.encode(), value.encode()) for key, value in (headers or {}).items()]
    return Request({"type": "http", "method": "GET", "path": "/", "headers": raw_headers}, receive)


def test_get_or_create_request_id_uses_header() -> None:
    request = make_request({"x-request-id": "abc123"})

    assert _get_or_create_request_id(request) == "abc123"


def test_get_or_create_request_id_generates_value(monkeypatch) -> None:
    monkeypatch.setattr(
        "wild_catalog.api.errors.uuid.uuid4",
        lambda: type("U", (), {"hex": "generated"})(),
    )
    request = make_request()

    assert _get_or_create_request_id(request) == "generated"


def test_error_response_shape() -> None:
    response = _error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="bad_request",
        message="bad",
        request_id="req-1",
    )

    assert response.status_code == 400
    assert response.body == b'{"error":{"code":"bad_request","message":"bad","request_id":"req-1"}}'


def test_wild_catalog_error_handler_uses_public_detail() -> None:
    request = make_request({"x-request-id": "req-1"})
    exc = ContentLengthHeaderIsNotNumberError(debug_detail="debug")

    response = __import__("asyncio").run(wild_catalog_error_handler(request, exc))

    assert response.status_code == exc.status_code


def test_request_validation_error_handler() -> None:
    request = make_request({"x-request-id": "req-1"})

    class Model(BaseModel):
        value: int

    try:
        Model.model_validate({"value": "x"})
    except ValidationError as exc:
        response = __import__("asyncio").run(
            request_validation_error_handler(
                request,
                RequestValidationError(exc.errors()),
            )
        )

    assert response.status_code == 400


def test_pydantic_validation_error_handler() -> None:
    request = make_request({"x-request-id": "req-1"})

    class Model(BaseModel):
        value: int

    try:
        Model.model_validate({"value": "x"})
    except ValidationError as exc:
        response = __import__("asyncio").run(pydantic_validation_error_handler(request, exc))

    assert response.status_code == 400


def test_unexpected_error_handler() -> None:
    request = make_request({"x-request-id": "req-1"})
    response = __import__("asyncio").run(unexpected_error_handler(request, RuntimeError("boom")))

    assert response.status_code == 500


def test_register_exception_handlers_registers_all_handlers() -> None:
    handlers = []

    class _App:
        def add_exception_handler(self, exc_class, handler):
            handlers.append((exc_class, handler))

    register_exception_handlers(_App())

    assert len(handlers) == 4
