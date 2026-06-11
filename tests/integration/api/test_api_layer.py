from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wild_catalog.api.app import app
from wild_catalog.api.dependencies import get_identify_pipeline
from wild_catalog.api.openapi_schemas import IDENTIFY_REQUEST_OPENAPI_EXTRA
from wild_catalog.pipeline.identify_result import IdentifyResult

SAMPLE_IMAGES_DIR = Path("sample-images")
JPEG_IMAGE = SAMPLE_IMAGES_DIR / "20260402-IMG_7906.jpg"
RAW_IMAGE = SAMPLE_IMAGES_DIR / "20260525-IMG_7906.CR3"


class DummyPipeline:
    def __init__(self, *, return_detected_images: bool = False) -> None:
        self.calls: list[object] = []
        self.return_detected_images = return_detected_images

    async def execute(self, command, file):
        self.calls.append((command, file))
        return IdentifyResult(
            objects=(),
            return_detected_images=self.return_detected_images,
        )


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)
def test_health_endpoint_returns_status_ok() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)
def test_openapi_document_includes_identify_upload_examples() -> None:
    client = TestClient(app)

    response = client.get("/openapi.json")
    schema = response.json()
    request_body = schema["paths"]["/identify"]["post"]["requestBody"]["content"]

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert request_body == IDENTIFY_REQUEST_OPENAPI_EXTRA["requestBody"]["content"]


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)
@pytest.mark.parametrize(
    ("content_type", "headers", "file_path"),
    [
        ("image/jpeg", {"content-type": "image/jpeg"}, JPEG_IMAGE),
        ("application/octet-stream", {"content-type": "application/octet-stream"}, RAW_IMAGE),
    ],
)
def test_identify_accepts_direct_image_uploads_without_payload(
    content_type: str,
    headers: dict[str, str],
    file_path: Path,
) -> None:
    pipeline = DummyPipeline()
    client = TestClient(app)
    app.dependency_overrides[get_identify_pipeline] = lambda: pipeline

    try:
        response = client.post(
            "/identify",
            content=file_path.read_bytes(),
            headers={
                **headers,
                "x-filename": file_path.name,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == []
    command, _ = pipeline.calls[0]
    assert command.original_filename == file_path.name
    assert response.request.headers["content-type"].startswith(content_type)


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)
def test_identify_accepts_multipart_upload_with_payload() -> None:
    pipeline = DummyPipeline(return_detected_images=True)
    client = TestClient(app)
    app.dependency_overrides[get_identify_pipeline] = lambda: pipeline

    try:
        response = client.post(
            "/identify",
            files={"image": (JPEG_IMAGE.name, JPEG_IMAGE.read_bytes(), "image/jpeg")},
            data={
                "payload": json.dumps(
                    {
                        "original_filename": "override-name.jpg",
                        "return_detected_images": True,
                        "common_name_language": "es-MX",
                    }
                )
            },
            headers={"accept": "multipart/mixed"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/mixed; boundary=")
    assert b"Content-Type: application/json" in response.content
    command, _ = pipeline.calls[0]
    assert command.original_filename == JPEG_IMAGE.name
    assert command.return_detected_images is True
    assert command.common_name_language == "es-MX"


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)
def test_identify_accepts_multipart_upload_without_payload() -> None:
    pipeline = DummyPipeline(return_detected_images=False)
    client = TestClient(app)
    app.dependency_overrides[get_identify_pipeline] = lambda: pipeline

    try:
        response = client.post(
            "/identify",
            files={"image": (JPEG_IMAGE.name, JPEG_IMAGE.read_bytes(), "image/jpeg")},
            headers={"accept": "application/json"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == []
    command, _ = pipeline.calls[0]
    assert command.original_filename == JPEG_IMAGE.name
    assert command.return_detected_images is False


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)
def test_identify_returns_406_when_detected_images_are_requested_without_multipart_accept() -> None:
    pipeline = DummyPipeline(return_detected_images=True)
    client = TestClient(app)
    app.dependency_overrides[get_identify_pipeline] = lambda: pipeline

    try:
        response = client.post(
            "/identify",
            files={"image": (JPEG_IMAGE.name, JPEG_IMAGE.read_bytes(), "image/jpeg")},
            data={
                "payload": json.dumps(
                    {
                        "original_filename": JPEG_IMAGE.name,
                        "return_detected_images": True,
                    }
                )
            },
            headers={"accept": "application/json"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 406
    assert len(pipeline.calls) == 1


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)
def test_identify_honors_multipart_accept_for_json_only_responses() -> None:
    pipeline = DummyPipeline(return_detected_images=True)
    client = TestClient(app)
    app.dependency_overrides[get_identify_pipeline] = lambda: pipeline

    try:
        response = client.post(
            "/identify",
            files={"image": (JPEG_IMAGE.name, JPEG_IMAGE.read_bytes(), "image/jpeg")},
            headers={"accept": "multipart/mixed"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/mixed; boundary=")
    assert b"Content-Type: application/json" in response.content
