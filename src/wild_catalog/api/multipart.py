import json
from io import BytesIO
from uuid import uuid4

from fastapi.responses import Response
from PIL import Image

from wild_catalog.api.serializers import identify_result_to_json
from wild_catalog.pipeline.models import IdentifiedObject, IdentifyResult


def build_multipart_response(
    result: IdentifyResult,
    *,
    include_images: bool,
) -> Response:
    boundary = f"wild-catalog-{uuid4().hex}"
    body = _build_multipart_body(
        result=result,
        boundary=boundary,
        include_images=include_images,
    )

    return Response(
        content=body,
        media_type=f'multipart/mixed; boundary="{boundary}"',
    )


def _build_multipart_body(
    result: IdentifyResult,
    *,
    boundary: str,
    include_images: bool,
) -> bytes:
    parts: list[bytes] = [
        _build_json_part(json_payload=identify_result_to_json(result))
    ]

    if include_images:
        for index, identified_object in enumerate(result.objects):
            if identified_object.cropped_image is None:
                continue

            parts.append(
                _build_jpeg_part(
                    identified_object=identified_object,
                    index=index,
                )
            )

    return _join_multipart_parts(parts, boundary=boundary)


def _build_json_part(*, json_payload: object) -> bytes:
    payload = json.dumps(json_payload, separators=(",", ":")).encode("utf-8")
    headers = [
        b"Content-Type: application/json; charset=utf-8",
        b'Content-Disposition: inline; name="metadata"',
    ]

    return _build_part(headers=headers, payload=payload)


def _build_jpeg_part(
    *,
    identified_object: IdentifiedObject,
    index: int,
) -> bytes:
    if identified_object.cropped_image is None:
        raise ValueError("Cannot build JPEG part without cropped image.")

    headers = [
        b"Content-Type: image/jpeg",
        (
            f'Content-Disposition: attachment; name="crop-{index}"; '
            f'filename="crop-{index}.jpg"'
        ).encode(),
    ]

    return _build_part(
        headers=headers,
        payload=_encode_image_as_jpeg(identified_object.cropped_image),
    )


def _build_part(*, headers: list[bytes], payload: bytes) -> bytes:
    return b"\r\n".join([*headers, b"", payload])


def _join_multipart_parts(parts: list[bytes], *, boundary: str) -> bytes:
    boundary_bytes = boundary.encode("ascii")
    body = bytearray()

    for part in parts:
        body.extend(b"--")
        body.extend(boundary_bytes)
        body.extend(b"\r\n")
        body.extend(part)
        body.extend(b"\r\n")

    body.extend(b"--")
    body.extend(boundary_bytes)
    body.extend(b"--\r\n")

    return bytes(body)


def _encode_image_as_jpeg(image: Image.Image) -> bytes:
    output = BytesIO()
    rgb_image = image if image.mode == "RGB" else image.convert("RGB")
    rgb_image.save(output, format="JPEG", quality=90, optimize=True)
    return output.getvalue()
