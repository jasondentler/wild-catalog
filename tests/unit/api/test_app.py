
import pytest
from fastapi.testclient import TestClient

from wild_catalog.api import app as app_module
from wild_catalog.api.app import app
from wild_catalog.api.dependencies import get_identify_pipeline
from wild_catalog.identify_pipeline.identify_result import IdentifyResult


def test_health_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_json_is_available() -> None:
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


def test_lifespan_preloads_range_data_and_identify_pipeline(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr(
        app_module,
        "preload_inaturalist_taxonomy_data",
        lambda: calls.append("taxonomy-data-loaded"),
    )
    monkeypatch.setattr(
        app_module,
        "preload_inaturalist_open_range_data",
        lambda: calls.append("range-data-loaded"),
    )
    monkeypatch.setattr(
        app_module,
        "get_identify_pipeline",
        lambda: calls.append("pipeline-loaded"),
    )

    with TestClient(app):
        pass

    assert calls == ["taxonomy-data-loaded", "range-data-loaded", "pipeline-loaded"]


def test_identify_openapi_includes_upload_content_types() -> None:
    client = TestClient(app)

    schema = client.get("/openapi.json").json()
    identify_operation = schema["paths"]["/identify"]["post"]
    request_body = schema["paths"]["/identify"]["post"]["requestBody"]["content"]

    assert "multipart/form-data" in request_body
    assert "application/octet-stream" in request_body
    assert "image/jpeg" in request_body
    assert request_body["multipart/form-data"]["schema"]["properties"]["image"] == {
        "type": "string",
        "format": "binary",
        "description": "Image file upload.",
    }
    assert "examples" in request_body["multipart/form-data"]
    assert (
        request_body["multipart/form-data"]["schema"]["properties"]["payload"]["example"]
        == {
            "original_filename": "IMG_7906.jpg",
            "exif_override": {
                "gps_coordinates": {
                    "latitude": 29.573361,
                    "longitude": -94.389507,
                },
                "captured_at": "2026-05-01T12:30:00Z",
            },
            "return_detected_images": True,
            "common_name_language": "en-US",
        }
    )
    assert identify_operation["requestBody"]["required"] is True
    assert request_body["multipart/form-data"]["examples"] == {
        "imageOnly": {
            "summary": "Image only",
            "value": {
                "image": "<binary image file>",
            },
        },
        "imageAndPayload": {
            "summary": "Image and JSON payload",
            "value": {
                "image": "<binary image file>",
                "payload": {
                    "original_filename": "IMG_7906.jpg",
                    "exif_override": {
                        "gps_coordinates": {
                            "latitude": 29.573361,
                            "longitude": -94.389507,
                        },
                        "captured_at": "2026-05-01T12:30:00Z",
                    },
                    "return_detected_images": True,
                    "common_name_language": "en-US",
                },
            },
        },
    }
    assert request_body["application/octet-stream"]["examples"] == {
        "rawImage": {
            "summary": "Raw bytes upload",
            "value": "<binary image bytes>",
        }
    }
    assert request_body["image/jpeg"]["examples"] == {
        "rawImage": {
            "summary": "JPEG upload",
            "value": "<binary image bytes>",
        }
    }
    success_response = identify_operation["responses"]["200"]
    assert success_response["description"] == "Successful Response"
    assert list(success_response["content"]) == ["multipart/mixed", "application/json"]
    assert success_response["content"]["multipart/mixed"] == {
        "schema": {
            "type": "string",
            "format": "binary",
        },
        "example": (
            "Multipart response with an application/json part followed by "
            "zero or more image/jpeg detected image parts."
        ),
    }
    assert identify_operation["responses"]["406"] == {
        "description": (
            "The requested response format is not acceptable. "
            "return_detected_images=true requires Accept: multipart/mixed."
        ),
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "not_acceptable",
                        "message": "Requested detected images require multipart/mixed.",
                        "request_id": "request-id",
                    }
                }
            }
        },
    }
    identify_response_schema = schema["components"]["schemas"]["IdentifyResponse"]
    assert identify_response_schema["required"] == ["results"]
    assert identify_response_schema["properties"]["gps_coordinates"]["anyOf"] == [
        {"$ref": "#/components/schemas/GpsCoordinatesResponse"},
        {"type": "null"},
    ]
    assert schema["components"]["schemas"]["GpsCoordinatesResponse"]["required"] == [
        "latitude",
        "longitude",
    ]
    assert identify_operation["parameters"] == [
        {
            "name": "accept",
            "in": "header",
            "required": False,
            "description": (
                "Response format to request. Use multipart/mixed when "
                "return_detected_images is true."
            ),
            "schema": {
                "type": "string",
                "enum": [
                    "multipart/mixed",
                    "application/json",
                    "application/json, multipart/mixed",
                ],
                "default": "multipart/mixed",
            },
        }
    ]

@pytest.mark.parametrize(
    ("content_type", "request_kwargs"),
    [
        (
            "multipart/form-data",
            {"files": {"image": ("trail-camera.jpg", b"fake image bytes", "image/jpeg")}},
        ),
        (
            "application/octet-stream",
            {
                "content": b"fake image bytes",
                "headers": {
                    "content-type": "application/octet-stream",
                    "x-filename": "trail-camera.jpg",
                },
            },
        ),
        (
            "image/jpeg",
            {
                "content": b"fake image bytes",
                "headers": {
                    "content-type": "image/jpeg",
                    "x-filename": "trail-camera.jpg",
                },
            },
        ),
    ],
)
def test_identify_accepts_image_without_payload(
    content_type: str,
    request_kwargs: dict[str, object],
) -> None:
    class DummyPipeline:
        async def execute(self, command, file):
            return IdentifyResult(objects=())

    client = TestClient(app)
    app.dependency_overrides[get_identify_pipeline] = lambda: DummyPipeline()

    try:
        response = client.post("/identify", **request_kwargs)
    finally:
        app.dependency_overrides.clear()

    assert response.request.headers["content-type"].startswith(content_type)
    assert response.headers["content-type"].startswith("application/json")
    assert response.status_code == 200


def test_identify_accepts_image_with_json_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPipeline:
        async def execute(self, command, file):
            return IdentifyResult(objects=())

    client = TestClient(app)
    seen_payloads: list[str] = []
    original_model_validate_json = (
        __import__("wild_catalog.api.multipart_request_mapper", fromlist=["IdentifyRequest"])
        .IdentifyRequest.model_validate_json
    )

    def fake_model_validate(value: str):
        seen_payloads.append(value)
        return original_model_validate_json(value)

    monkeypatch.setattr(
        "wild_catalog.api.multipart_request_mapper.IdentifyRequest.model_validate_json",
        fake_model_validate,
    )
    app.dependency_overrides[get_identify_pipeline] = lambda: DummyPipeline()

    try:
        response = client.post(
            "/identify",
            files={"image": ("trail-camera.jpg", b"fake image bytes", "image/jpeg")},
            data={
                "payload": (
                    '{"original_filename":"trail-camera.jpg","return_detected_images":true}'
                ),
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.request.headers["content-type"].startswith("multipart/form-data")
    assert response.status_code == 200
    assert seen_payloads == [
        '{"original_filename":"trail-camera.jpg","return_detected_images":true}'
    ]


def test_identify_rejects_detected_images_with_json_accept_before_pipeline() -> None:
    class DummyPipeline:
        def __init__(self) -> None:
            self.calls = 0

        async def execute(self, command, file):
            self.calls += 1
            return IdentifyResult(objects=())

    pipeline = DummyPipeline()
    client = TestClient(app)
    app.dependency_overrides[get_identify_pipeline] = lambda: pipeline

    try:
        response = client.post(
            "/identify",
            files={"image": ("trail-camera.jpg", b"fake image bytes", "image/jpeg")},
            data={
                "payload": (
                    '{"original_filename":"trail-camera.jpg","return_detected_images":true}'
                ),
            },
            headers={"accept": "application/json", "x-request-id": "req-1"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 406
    assert response.json() == {
        "error": {
            "code": "not_acceptable",
            "message": "Requested detected images require multipart/mixed.",
            "request_id": "req-1",
        }
    }
    assert pipeline.calls == 0


def test_identify_sets_multipart_response_format_when_accepted() -> None:
    class DummyPipeline:
        async def execute(self, command, file):
            return IdentifyResult(objects=())

    client = TestClient(app)
    app.dependency_overrides[get_identify_pipeline] = lambda: DummyPipeline()

    try:
        response = client.post(
            "/identify",
            files={"image": ("trail-camera.jpg", b"fake image bytes", "image/jpeg")},
            headers={"accept": "multipart/mixed"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.headers["content-type"].startswith("multipart/mixed; boundary=")
    assert response.status_code == 200
