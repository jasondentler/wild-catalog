from fastapi.testclient import TestClient

from wild_catalog.api.app import app
from wild_catalog.api.dependencies import get_identify_pipeline
from wild_catalog.pipeline.models import IdentifyResult


class FakeIdentifyPipeline:
    def identify(self, image_file, command) -> IdentifyResult:
        return IdentifyResult(objects=())


def override_get_identify_pipeline() -> FakeIdentifyPipeline:
    return FakeIdentifyPipeline()


def test_identify_rejects_invalid_payload_json() -> None:
    app.dependency_overrides[get_identify_pipeline] = override_get_identify_pipeline

    try:
        client = TestClient(app)

        response = client.post(
            "/identify",
            files={
                "image": (
                    "image.jpg",
                    b"fake image bytes",
                    "image/jpeg",
                ),
            },
            data={"payload": "not json"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "malformed_json_payload"


def test_identify_rejects_missing_image() -> None:
    app.dependency_overrides[get_identify_pipeline] = override_get_identify_pipeline

    try:
        client = TestClient(app)

        response = client.post(
            "/identify",
            data={
                "payload": '{"original_filename":"image.jpg"}',
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_identify_rejects_missing_payload() -> None:
    app.dependency_overrides[get_identify_pipeline] = override_get_identify_pipeline

    try:
        client = TestClient(app)

        response = client.post(
            "/identify",
            files={
                "image": (
                    "image.jpg",
                    b"fake image bytes",
                    "image/jpeg",
                ),
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_identify_rejects_invalid_gps_override() -> None:
    app.dependency_overrides[get_identify_pipeline] = override_get_identify_pipeline

    try:
        client = TestClient(app)

        response = client.post(
            "/identify",
            files={
                "image": (
                    "image.jpg",
                    b"fake image bytes",
                    "image/jpeg",
                ),
            },
            data={
                "payload": (
                    '{"original_filename":"image.jpg",'
                    '"exif_override":{"gps_coordinates":"999.0, -95.0"}}'
                ),
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_gps_override"
