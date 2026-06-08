from PIL import Image

from wild_catalog.api.multipart import build_multipart_response
from wild_catalog.core.types import BoundingBox
from wild_catalog.pipeline.models import IdentifiedObject, IdentifyResult


def test_build_multipart_response_includes_json_metadata() -> None:
    response = build_multipart_response(
        IdentifyResult(objects=()),
        include_images=False,
    )

    body = response.body

    assert response.media_type.startswith("multipart/mixed")
    assert b"Content-Type: application/json" in body
    assert b"[]" in body
    assert b"image/jpeg" not in body


def test_build_multipart_response_includes_requested_cropped_images() -> None:
    response = build_multipart_response(
        IdentifyResult(
            objects=(
                IdentifiedObject(
                    bounding_box=BoundingBox(10, 10, 30, 30),
                    bounding_box_with_margin=BoundingBox(5, 5, 35, 35),
                    gps_coordinates=None,
                    predictions=(),
                    cropped_image=Image.new("RGB", (10, 10), color="red"),
                ),
            )
        ),
        include_images=True,
    )

    body = response.body

    assert b"Content-Type: application/json" in body
    assert b"Content-Type: image/jpeg" in body
    assert b'detected_image_0"; filename="detected_image_0.jpg"' in body
    assert body.count(b"--wild-catalog-") == 3
