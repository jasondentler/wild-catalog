from fastapi import FastAPI
from fastapi.testclient import TestClient

from wild_catalog.api.errors import register_exception_handlers
from wild_catalog.core.errors import (
    ModelUnavailableError,
    PlatformConversionError,
    UnsupportedMediaTypeError,
)


def make_app_with_route(exc: Exception) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise exc

    return app


def test_unsupported_media_type_maps_to_415() -> None:
    app = make_app_with_route(UnsupportedMediaTypeError())
    client = TestClient(app)

    response = client.get("/boom")

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_image_format"


def test_platform_conversion_maps_to_422_without_debug_detail() -> None:
    app = make_app_with_route(
        PlatformConversionError(
            public_detail="Image conversion failed.",
            debug_detail="secret stderr",
        )
    )
    client = TestClient(app)

    response = client.get("/boom")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "platform_conversion_failed"
    assert "secret stderr" not in response.text


def test_model_unavailable_maps_to_503() -> None:
    app = make_app_with_route(ModelUnavailableError())
    client = TestClient(app)

    response = client.get("/boom")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "model_unavailable"


def test_unexpected_exception_maps_to_500_without_stack_trace() -> None:
    app = make_app_with_route(RuntimeError("secret internal failure"))
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_server_error"
    assert "secret internal failure" not in response.text
    assert "Traceback" not in response.text
