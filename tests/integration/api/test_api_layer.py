from __future__ import annotations

import io
import json
import os
from email import policy
from email.parser import BytesParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from wild_catalog.api import app as app_module
from wild_catalog.api.app import app
from wild_catalog.api.dependencies import get_identify_pipeline, get_settings
from wild_catalog.api.openapi_schemas import IDENTIFY_REQUEST_OPENAPI_EXTRA
from wild_catalog.core.settings import Settings
from wild_catalog.core.types import GpsCoordinates
from wild_catalog.identify_pipeline.identify_command import ExifOverride
from wild_catalog.identify_pipeline.identify_result import IdentifyResult

SAMPLE_IMAGES_DIR = Path("sample-images")
JPEG_IMAGE_1 = SAMPLE_IMAGES_DIR / "20260402-IMG_7906.jpg"
JPEG_IMAGE_2 = SAMPLE_IMAGES_DIR / "20260419-DA8A0090.jpg"
JPEG_IMAGE_3 = SAMPLE_IMAGES_DIR / "20260419-DA8A5083.jpg"
JPEG_IMAGE_4 = SAMPLE_IMAGES_DIR / "20260419-DA8A5151.jpg"
JPEG_IMAGE_5 = SAMPLE_IMAGES_DIR / "20260419-DA8A5506.jpg"
JPEG_IMAGE_6 = SAMPLE_IMAGES_DIR / "20260419-DA8A7718.jpg"
PNG_IMAGE = SAMPLE_IMAGES_DIR / "20260402-IMG_7906.png"
WEBP_IMAGE = SAMPLE_IMAGES_DIR / "20260402-IMG_7906.webp"
RAW_IMAGE = SAMPLE_IMAGES_DIR / "20260525-IMG_7906.CR3"
DNG_IMAGE = SAMPLE_IMAGES_DIR / "20260525-IMG_7906.dng"
DNG_IMAGE_2 = SAMPLE_IMAGES_DIR / "20260525-IMG_7906_1.dng"
HEIC_IMAGE = SAMPLE_IMAGES_DIR / "20260525-IMG_7906.heic"


@pytest.fixture(autouse=True)
def _use_default_upload_limit(monkeypatch: pytest.MonkeyPatch):
    settings_from_env = staticmethod(lambda: Settings(max_upload_bytes=100000000))
    monkeypatch.setattr(
        app_module.Settings,
        "from_env",
        settings_from_env,
    )
    monkeypatch.setattr(
        app_module.limit_content_length.__globals__["Settings"],
        "from_env",
        settings_from_env,
    )
    get_settings.cache_clear()
    get_identify_pipeline.cache_clear()
    app.middleware_stack = None
    yield
    get_identify_pipeline.cache_clear()
    get_settings.cache_clear()
    app.middleware_stack = None


class DummyPipeline:
    def __init__(self, *, return_detected_images: bool = False) -> None:
        self.calls: list[object] = []
        self.return_detected_images = return_detected_images

    async def execute(self, command, file):
        self.calls.append((command, file))
        return IdentifyResult(
            objects=(),
            gps_coordinates=(
                command.exif_override.gps_coordinates
                if command.exif_override is not None
                else None
            ),
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
    (
        "scenario",
        "request_kwargs",
        "expected_status",
        "expected_content_type_prefix",
        "expected_body",
        "expected_command_checks",
    ),
    [
        pytest.param(
            "direct-jpeg",
            {
                "content": JPEG_IMAGE_1.read_bytes(),
                "headers": {
                    "content-type": "image/jpeg",
                    "x-filename": JPEG_IMAGE_1.name,
                },
            },
            200,
            "application/json",
            {"gps_coordinates": None, "results": []},
            [
                ("original_filename", JPEG_IMAGE_1.name),
                ("return_detected_images", False),
            ],
            id="direct-jpeg",
        ),
        pytest.param(
            "direct-jpeg-2",
            {
                "content": JPEG_IMAGE_2.read_bytes(),
                "headers": {
                    "content-type": "image/jpeg",
                    "x-filename": JPEG_IMAGE_2.name,
                },
            },
            200,
            "application/json",
            {"gps_coordinates": None, "results": []},
            [("original_filename", JPEG_IMAGE_2.name)],
            id="direct-jpeg-2",
        ),
        pytest.param(
            "direct-jpeg-3",
            {
                "content": JPEG_IMAGE_3.read_bytes(),
                "headers": {
                    "content-type": "image/jpeg",
                    "x-filename": JPEG_IMAGE_3.name,
                },
            },
            200,
            "application/json",
            {"gps_coordinates": None, "results": []},
            [("original_filename", JPEG_IMAGE_3.name)],
            id="direct-jpeg-3",
        ),
        pytest.param(
            "direct-jpeg-4",
            {
                "content": JPEG_IMAGE_4.read_bytes(),
                "headers": {
                    "content-type": "image/jpeg",
                    "x-filename": JPEG_IMAGE_4.name,
                },
            },
            200,
            "application/json",
            {"gps_coordinates": None, "results": []},
            [("original_filename", JPEG_IMAGE_4.name)],
            id="direct-jpeg-4",
        ),
        pytest.param(
            "direct-jpeg-5",
            {
                "content": JPEG_IMAGE_5.read_bytes(),
                "headers": {
                    "content-type": "image/jpeg",
                    "x-filename": JPEG_IMAGE_5.name,
                },
            },
            200,
            "application/json",
            {"gps_coordinates": None, "results": []},
            [("original_filename", JPEG_IMAGE_5.name)],
            id="direct-jpeg-5",
        ),
        pytest.param(
            "direct-jpeg-6",
            {
                "content": JPEG_IMAGE_6.read_bytes(),
                "headers": {
                    "content-type": "image/jpeg",
                    "x-filename": JPEG_IMAGE_6.name,
                },
            },
            200,
            "application/json",
            {"gps_coordinates": None, "results": []},
            [("original_filename", JPEG_IMAGE_6.name)],
            id="direct-jpeg-6",
        ),
        pytest.param(
            "direct-png",
            {
                "content": PNG_IMAGE.read_bytes(),
                "headers": {
                    "content-type": "image/png",
                    "x-filename": PNG_IMAGE.name,
                },
            },
            200,
            "application/json",
            {"gps_coordinates": None, "results": []},
            [("original_filename", PNG_IMAGE.name)],
            id="direct-png",
        ),
        pytest.param(
            "direct-webp",
            {
                "content": WEBP_IMAGE.read_bytes(),
                "headers": {
                    "content-type": "image/webp",
                    "x-filename": WEBP_IMAGE.name,
                },
            },
            200,
            "application/json",
            {"gps_coordinates": None, "results": []},
            [("original_filename", WEBP_IMAGE.name)],
            id="direct-webp",
        ),
        pytest.param(
            "multipart-jpeg",
            {
                "files": {"image": (JPEG_IMAGE_1.name, JPEG_IMAGE_1.read_bytes(), "image/jpeg")},
                "headers": {"accept": "application/json"},
            },
            200,
            "application/json",
            {"gps_coordinates": None, "results": []},
            [("original_filename", JPEG_IMAGE_1.name)],
            id="multipart-jpeg",
        ),
        pytest.param(
            "multipart-jpeg-payload",
            {
                "files": {"image": (JPEG_IMAGE_1.name, JPEG_IMAGE_1.read_bytes(), "image/jpeg")},
                "data": {
                    "payload": json.dumps(
                        {
                            "original_filename": "override-name.jpg",
                            "return_detected_images": True,
                            "common_name_language": "es-MX",
                        }
                    )
                },
                "headers": {"accept": "multipart/mixed"},
            },
            200,
            "multipart/mixed; boundary=",
            None,
            [
                ("original_filename", JPEG_IMAGE_1.name),
                ("return_detected_images", True),
                ("common_name_language", "es-MX"),
            ],
            id="multipart-jpeg-payload",
        ),
        pytest.param(
            "multipart-jpeg-no-payload",
            {
                "files": {"image": (JPEG_IMAGE_1.name, JPEG_IMAGE_1.read_bytes(), "image/jpeg")},
                "headers": {"accept": "application/json"},
            },
            200,
            "application/json",
            {"gps_coordinates": None, "results": []},
            [
                ("original_filename", JPEG_IMAGE_1.name),
                ("return_detected_images", False),
            ],
            id="multipart-jpeg-no-payload",
        ),
        pytest.param(
            "direct-raw",
            {
                "content": RAW_IMAGE.read_bytes(),
                "headers": {
                    "content-type": "application/octet-stream",
                    "x-filename": RAW_IMAGE.name,
                },
            },
            200,
            "application/json",
            {"gps_coordinates": None, "results": []},
            [("original_filename", RAW_IMAGE.name)],
            id="direct-raw",
        ),
        pytest.param(
            "direct-dng",
            {
                "content": DNG_IMAGE.read_bytes(),
                "headers": {
                    "content-type": "application/octet-stream",
                    "x-filename": DNG_IMAGE.name,
                },
            },
            200,
            "application/json",
            {"gps_coordinates": None, "results": []},
            [("original_filename", DNG_IMAGE.name)],
            id="direct-dng",
        ),
        pytest.param(
            "direct-dng-2",
            {
                "content": DNG_IMAGE_2.read_bytes(),
                "headers": {
                    "content-type": "application/octet-stream",
                    "x-filename": DNG_IMAGE_2.name,
                },
            },
            200,
            "application/json",
            {"gps_coordinates": None, "results": []},
            [("original_filename", DNG_IMAGE_2.name)],
            id="direct-dng-2",
        ),
        pytest.param(
            "houston-red-winged-blackbird",
            {
                "files": {
                    "image": (
                        DNG_IMAGE.name,
                        DNG_IMAGE.read_bytes(),
                        "application/octet-stream",
                    )
                },
                "data": {
                    "payload": json.dumps(
                            {
                                "original_filename": DNG_IMAGE.name,
                                "exif_override": {
                                    "gps_coordinates": {
                                        "latitude": 29.7604,
                                        "longitude": -95.3698,
                                    },
                                },
                            }
                    )
                },
                "headers": {"accept": "application/json"},
            },
            200,
            "application/json",
            {
                "gps_coordinates": {
                    "latitude": 29.7604,
                    "longitude": -95.3698,
                },
                "results": [],
            },
            [
                ("original_filename", DNG_IMAGE.name),
                (
                    "exif_override",
                    ExifOverride(
                        gps_coordinates=GpsCoordinates(
                            latitude=29.7604,
                            longitude=-95.3698,
                        ),
                    ),
                ),
            ],
            id="houston-red-winged-blackbird",
        ),
    ],
)
def test_identify_curl_scenarios_match_request_shapes(
    scenario: str,
    request_kwargs: dict[str, object],
    expected_status: int,
    expected_content_type_prefix: str,
    expected_body,
    expected_command_checks: list[tuple[str, object]],
) -> None:
    pipeline = DummyPipeline(return_detected_images=scenario == "multipart-jpeg-payload")
    client = TestClient(app)
    app.dependency_overrides[get_identify_pipeline] = lambda: pipeline

    try:
        response = client.post("/identify", **request_kwargs)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.headers["content-type"].startswith(expected_content_type_prefix)
    if expected_body is not None:
        assert response.json() == expected_body

    command, _ = pipeline.calls[0]
    for attribute, value in expected_command_checks:
        assert getattr(command, attribute) == value


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
            files={"image": (JPEG_IMAGE_1.name, JPEG_IMAGE_1.read_bytes(), "image/jpeg")},
            data={
                "payload": json.dumps(
                    {
                        "original_filename": JPEG_IMAGE_1.name,
                        "return_detected_images": True,
                    }
                )
            },
            headers={"accept": "application/json"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 406
    assert len(pipeline.calls) == 0


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
            files={"image": (JPEG_IMAGE_1.name, JPEG_IMAGE_1.read_bytes(), "image/jpeg")},
            headers={"accept": "multipart/mixed"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/mixed; boundary=")
    assert b"Content-Type: application/json" in response.content


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)
def test_identify_returns_cropped_jpeg_part_when_detected_images_are_requested() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/identify",
            files={"image": (JPEG_IMAGE_1.name, JPEG_IMAGE_1.read_bytes(), "image/jpeg")},
            data={
                "payload": json.dumps(
                    {
                        "original_filename": JPEG_IMAGE_1.name,
                        "return_detected_images": True,
                    }
                )
            },
            headers={"accept": "multipart/mixed"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/mixed; boundary=")

    message = BytesParser(policy=policy.default).parsebytes(
        (
            f"Content-Type: {response.headers['content-type']}\r\n"
            "MIME-Version: 1.0\r\n\r\n"
        ).encode()
        + response.content
    )
    parts = list(message.iter_parts())
    json_parts = [part for part in parts if part.get_content_type() == "application/json"]
    jpeg_parts = [part for part in parts if part.get_content_type() == "image/jpeg"]

    assert len(json_parts) == 1
    assert jpeg_parts

    with Image.open(io.BytesIO(jpeg_parts[0].get_payload(decode=True))) as image:
        image.verify()
        assert image.format == "JPEG"


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)
def test_identify_rejects_heic_upload(monkeypatch: pytest.MonkeyPatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.WildlifeDetector",
        lambda: object(),
    )
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.SpeciesClassifier",
        lambda *args, **kwargs: object(),
    )

    response = client.post(
        "/identify",
        content=HEIC_IMAGE.read_bytes(),
        headers={
            "content-type": "image/heic",
            "x-filename": HEIC_IMAGE.name,
        },
    )

    assert response.status_code == 415, response.text
    assert response.json()["error"]["code"] == "unsupported_image_format"
