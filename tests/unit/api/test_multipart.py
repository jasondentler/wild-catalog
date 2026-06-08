from PIL import Image

from wild_catalog.api.multipart import build_multipart_response
from wild_catalog.core.types import BoundingBox, GpsCoordinates
from wild_catalog.pipeline.models import IdentifiedObject, IdentifyResult
from wild_catalog.taxonomy.types import EnrichedPrediction


def make_result(*, include_cropped_image: bool) -> IdentifyResult:
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
                cropped_image=(
                    Image.new("RGB", (10, 10), color=(128, 128, 128))
                    if include_cropped_image
                    else None
                ),
            ),
        )
    )


def test_build_multipart_response_always_includes_json_first_part() -> None:
    response = build_multipart_response(
        make_result(include_cropped_image=False),
        include_images=False,
    )

    body = response.body

    assert response.media_type.startswith("multipart/mixed")
    assert b"Content-Type: application/json; charset=utf-8" in body
    assert b'"taxonomy":["Animalia","Aves"]' in body
    assert b"image/jpeg" not in body


def test_build_multipart_response_includes_jpeg_parts_when_requested() -> None:
    response = build_multipart_response(
        make_result(include_cropped_image=True),
        include_images=True,
    )

    body = response.body

    assert response.media_type.startswith("multipart/mixed")
    assert b"Content-Type: application/json; charset=utf-8" in body
    assert b"Content-Type: image/jpeg" in body
    assert b'filename="crop-0.jpg"' in body
    assert b"\xff\xd8" in body


def test_build_multipart_response_does_not_base64_encode_images() -> None:
    response = build_multipart_response(
        make_result(include_cropped_image=True),
        include_images=True,
    )

    body = response.body

    assert b"Content-Transfer-Encoding: base64" not in body
    assert b"data:image/jpeg;base64" not in body
    assert b"\xff\xd8" in body


def test_build_multipart_response_uses_crlf_boundaries() -> None:
    response = build_multipart_response(
        make_result(include_cropped_image=False),
        include_images=False,
    )

    body = response.body

    assert b"\r\n" in body
    assert body.endswith(b"--\r\n")


def test_build_multipart_response_json_part_is_first() -> None:
    response = build_multipart_response(
        make_result(include_cropped_image=True),
        include_images=True,
    )

    body = response.body

    json_position = body.index(b"Content-Type: application/json; charset=utf-8")
    image_position = body.index(b"Content-Type: image/jpeg")

    assert json_position < image_position


def test_build_multipart_response_skips_missing_crop_images() -> None:
    response = build_multipart_response(
        make_result(include_cropped_image=False),
        include_images=True,
    )

    body = response.body

    assert b"Content-Type: application/json; charset=utf-8" in body
    assert b"Content-Type: image/jpeg" not in body
