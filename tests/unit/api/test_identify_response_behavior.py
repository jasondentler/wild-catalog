from io import BytesIO
from typing import BinaryIO

from fastapi.testclient import TestClient
from PIL import Image

from wild_catalog.api.app import app
from wild_catalog.api.dependencies import get_identify_pipeline
from wild_catalog.core.types import BoundingBox, GpsCoordinates
from wild_catalog.pipeline.models import IdentifiedObject, IdentifyCommand, IdentifyResult
from wild_catalog.taxonomy.types import EnrichedPrediction


class FakePipeline:
    call_count = 0

    def identify(self, image_file: BinaryIO, command: IdentifyCommand) -> IdentifyResult:
        self.call_count += 1
        cropped_image = (
            Image.new("RGB", (10, 10), color=(128, 128, 128))
            if command.return_detected_images
            else None
        )

        return IdentifyResult(
            objects=(
                IdentifiedObject(
                    bounding_box=BoundingBox(1, 2, 8, 9),
                    bounding_box_with_margin=BoundingBox(0, 1, 9, 10),
                    gps_coordinates=GpsCoordinates(latitude=29.0, longitude=-95.0),
                    predictions=(
                        EnrichedPrediction(
                            class_id=0,
                            taxon_id=101,
                            accepted_taxon_id=101,
                            confidence=0.95,
                            is_present=True,
                            taxonomy=("Animalia", "Aves"),
                            taxonomy_common_names=("Animals", "Birds"),
                            taxonomy_rank_names=("kingdom", "class"),
                        ),
                    ),
                    cropped_image=cropped_image,
                ),
            )
        )


def make_payload(*, return_detected_images: bool) -> str:
    return (
        "{"
        '"original_filename":"test.jpg",'
        f'"return_detected_images":{str(return_detected_images).lower()},'
        '"common_name_language":"en-US"'
        "}"
    )


def make_image_file() -> tuple[str, BytesIO, str]:
    image_bytes = BytesIO()
    Image.new("RGB", (10, 10), color=(128, 128, 128)).save(
        image_bytes,
        format="JPEG",
    )
    image_bytes.seek(0)
    return ("test.jpg", image_bytes, "image/jpeg")


def post_identify(
    *,
    return_detected_images: bool,
    accept_header: str | None = None,
) -> tuple[FakePipeline, object]:
    pipeline = FakePipeline()
    app.dependency_overrides[get_identify_pipeline] = lambda: pipeline

    try:
        client = TestClient(app)
        headers = {"Accept": accept_header} if accept_header is not None else {}

        response = client.post(
            "/identify",
            headers=headers,
            files={"image": make_image_file()},
            data={"payload": make_payload(return_detected_images=return_detected_images)},
        )
    finally:
        app.dependency_overrides.clear()

    return pipeline, response


def test_identify_returns_json_by_default() -> None:
    _pipeline, response = post_identify(return_detected_images=False)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()[0]["predictions"][0]["taxonomy"] == ["Animalia", "Aves"]


def test_identify_returns_json_when_accepts_application_json() -> None:
    _pipeline, response = post_identify(
        return_detected_images=False,
        accept_header="application/json",
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


def test_identify_returns_json_when_accept_includes_json_and_multipart() -> None:
    _pipeline, response = post_identify(
        return_detected_images=False,
        accept_header="application/json, multipart/mixed",
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


def test_identify_returns_multipart_json_only_when_accepts_multipart_only() -> None:
    _pipeline, response = post_identify(
        return_detected_images=False,
        accept_header="multipart/mixed",
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/mixed")
    assert b"Content-Type: application/json; charset=utf-8" in response.content
    assert b"Content-Type: image/jpeg" not in response.content


def test_identify_returns_multipart_with_images_when_requested_and_multipart_accepted() -> None:
    _pipeline, response = post_identify(
        return_detected_images=True,
        accept_header="multipart/mixed",
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/mixed")
    assert b"Content-Type: application/json; charset=utf-8" in response.content
    assert b"Content-Type: image/jpeg" in response.content
    assert b"\xff\xd8" in response.content


def test_identify_returns_multipart_with_images_when_requested_and_accept_blank() -> None:
    _pipeline, response = post_identify(
        return_detected_images=True,
        accept_header="",
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/mixed")
    assert b"Content-Type: image/jpeg" in response.content


def test_identify_returns_multipart_with_images_when_requested_and_accept_wildcard() -> None:
    _pipeline, response = post_identify(
        return_detected_images=True,
        accept_header="*/*",
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/mixed")
    assert b"Content-Type: image/jpeg" in response.content


def test_identify_returns_406_when_images_requested_but_multipart_not_accepted() -> None:
    pipeline, response = post_identify(
        return_detected_images=True,
        accept_header="application/json",
    )

    assert response.status_code == 406
    assert "multipart/mixed" in response.json()["detail"]
    assert pipeline.call_count == 0
