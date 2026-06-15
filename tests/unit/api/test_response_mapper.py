import asyncio
import json

from PIL import Image

from wild_catalog.api.content_negotiation import ResponseFormat, ResponseSelection
from wild_catalog.api.response_mapper import map_multipart_response, map_response
from wild_catalog.core.types import BoundingBox, GpsCoordinates
from wild_catalog.identify_pipeline.identify_result import (
    IdentifiedObject,
    IdentifyResult,
    Prediction,
)


def test_map_response_returns_204_for_none() -> None:
    response = map_response(
        None,
        ResponseSelection(
            response_format=ResponseFormat.JSON,
            include_images=False,
        ),
    )

    assert response.status_code == 204


def test_map_response_serializes_identify_result_objects() -> None:
    result = IdentifyResult(
        gps_coordinates=GpsCoordinates(latitude=45.1234, longitude=-93.1234),
        objects=(
            IdentifiedObject(
                bounding_box=BoundingBox(xmin=10, ymin=20, xmax=110, ymax=220),
                bounding_box_with_margin=BoundingBox(xmin=0, ymin=5, xmax=120, ymax=235),
                predictions=(
                    Prediction(
                        confidence=0.92,
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

    response = map_response(
        result,
        ResponseSelection(
            response_format=ResponseFormat.JSON,
            include_images=False,
        ),
    )

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "gps_coordinates": {
            "latitude": 45.1234,
            "longitude": -93.1234,
        },
        "results": [
            {
                "bounding_box": {
                    "xmin": 10,
                    "ymin": 20,
                    "xmax": 110,
                    "ymax": 220,
                    "width": 100,
                    "height": 200,
                },
                "bounding_box_with_margin": {
                    "xmin": 0,
                    "ymin": 5,
                    "xmax": 120,
                    "ymax": 235,
                    "width": 120,
                    "height": 230,
                },
                "predictions": [
                    {
                        "confidence": 0.92,
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
        ],
    }


def test_map_response_uses_result_flag_for_multipart_negotiation() -> None:
    result = IdentifyResult(
        objects=(),
    )

    response = map_response(
        result,
        ResponseSelection(
            response_format=ResponseFormat.MULTIPART,
            include_images=True,
        ),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/mixed; boundary=")


def test_map_response_maps_none_top_level_gps_coordinates() -> None:
    result = IdentifyResult(
        objects=(
            IdentifiedObject(
                bounding_box=BoundingBox(xmin=1, ymin=2, xmax=3, ymax=4),
                bounding_box_with_margin=BoundingBox(xmin=1, ymin=2, xmax=3, ymax=4),
                predictions=(),
            ),
        )
    )

    response = map_response(
        result,
        ResponseSelection(
            response_format=ResponseFormat.JSON,
            include_images=False,
        ),
    )

    assert b'"gps_coordinates":null' in response.body
    assert b'"results":[{"bounding_box"' in response.body


def test_map_multipart_response_includes_images() -> None:
    result = IdentifyResult(
        objects=(
            IdentifiedObject(
                bounding_box=BoundingBox(xmin=1, ymin=2, xmax=3, ymax=4),
                bounding_box_with_margin=BoundingBox(xmin=1, ymin=2, xmax=3, ymax=4),
                predictions=(),
                cropped_image=Image.new("RGB", (1, 1), color=(255, 0, 0)),
            ),
        )
    )
    response = map_multipart_response(
        result,
        ResponseSelection(
            response_format=ResponseFormat.MULTIPART,
            include_images=True,
        ),
    )

    assert response.media_type.startswith("multipart/mixed; boundary=")

    async def collect() -> bytes:
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        return body

    assert b"Content-Type: image/jpeg" in asyncio.run(collect())


def test_map_multipart_response_skips_missing_images() -> None:
    result = IdentifyResult(
        objects=(
            IdentifiedObject(
                bounding_box=BoundingBox(xmin=1, ymin=2, xmax=3, ymax=4),
                bounding_box_with_margin=BoundingBox(xmin=1, ymin=2, xmax=3, ymax=4),
                predictions=(),
            ),
        )
    )
    response = map_multipart_response(
        result,
        ResponseSelection(
            response_format=ResponseFormat.MULTIPART,
            include_images=True,
        ),
    )

    assert response.headers["content-type"].startswith("multipart/mixed; boundary=")
