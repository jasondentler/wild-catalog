from typing import BinaryIO

from fastapi.testclient import TestClient

from wild_catalog.api.app import app
from wild_catalog.api.dependencies import get_identify_pipeline
from wild_catalog.core.types import BoundingBox, GpsCoordinates
from wild_catalog.pipeline.models import IdentifiedObject, IdentifyCommand, IdentifyResult
from wild_catalog.taxonomy.types import EnrichedPrediction


class FakeIdentifyPipeline:
    def identify(self, image_file: BinaryIO, command: IdentifyCommand) -> IdentifyResult:
        assert image_file.read() == b"fake image bytes"
        assert command.original_filename == "image.jpg"

        return IdentifyResult(
            objects=(
                IdentifiedObject(
                    bounding_box=BoundingBox(
                        xmin=10,
                        ymin=20,
                        xmax=30,
                        ymax=50,
                    ),
                    bounding_box_with_margin=BoundingBox(
                        xmin=5,
                        ymin=15,
                        xmax=35,
                        ymax=55,
                    ),
                    gps_coordinates=GpsCoordinates(
                        latitude=29.7604,
                        longitude=-95.3698,
                    ),
                    predictions=(
                        EnrichedPrediction(
                            confidence=0.98,
                            is_present=True,
                            taxonomy=(
                                "Animalia",
                                "Chordata",
                                "Aves",
                                "Passeriformes",
                                "Corvidae",
                                "Cyanocitta cristata",
                            ),
                            taxonomy_common_names=(
                                "Animals",
                                "Chordates",
                                "Birds",
                                "Perching Birds",
                                "Crows and Jays",
                                "Blue Jay",
                            ),
                        ),
                    ),
                ),
            )
        )


def override_get_identify_pipeline() -> FakeIdentifyPipeline:
    return FakeIdentifyPipeline()


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


def test_identify_returns_json_response() -> None:
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
                    '"return_detected_images":false,'
                    '"common_name_language":"en-US"}'
                ),
            },
            headers={"accept": "application/json"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        assert response.json() == [
            {
                "bounding_box": {
                    "xmin": 10,
                    "ymin": 20,
                    "xmax": 30,
                    "ymax": 50,
                    "width": 20,
                    "height": 30,
                },
                "bounding_box_with_margin": {
                    "xmin": 5,
                    "ymin": 15,
                    "xmax": 35,
                    "ymax": 55,
                    "width": 30,
                    "height": 40,
                },
                "gps_coordinates": [29.7604, -95.3698],
                "predictions": [
                    {
                        "confidence": 0.98,
                        "is_present": True,
                        "taxonomy": [
                            "Animalia",
                            "Chordata",
                            "Aves",
                            "Passeriformes",
                            "Corvidae",
                            "Cyanocitta cristata",
                        ],
                        "taxonomy_common_names": [
                            "Animals",
                            "Chordates",
                            "Birds",
                            "Perching Birds",
                            "Crows and Jays",
                            "Blue Jay",
                        ],
                    }
                ],
            }
        ]
    finally:
        app.dependency_overrides.clear()
