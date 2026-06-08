import json
from io import BytesIO
from uuid import uuid4

from fastapi.responses import Response
from PIL import Image

from wild_catalog.api.serializers import identify_result_to_json
from wild_catalog.pipeline.models import IdentifyResult


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
        media_type=f"multipart/mixed; boundary={boundary}",
    )


def _build_multipart_body(
    result: IdentifyResult,
    *,
    boundary: str,
    include_images: bool,
) -> bytes:
    parts: list[bytes] = [
        _part(
            boundary=boundary,
            headers={
                "Content-Type": "application/json",
                "Content-Disposition": 'inline; name="metadata"',
            },
            body=json.dumps(identify_result_to_json(result)).encode("utf-8"),
        )
    ]

    if include_images:
        for index, identified_object in enumerate(result.objects):
            if identified_object.cropped_image is None:
                continue

            parts.append(
                _part(
                    boundary=boundary,
                    headers={
                        "Content-Type": "image/jpeg",
                        "Content-Disposition": (
                            f'inline; name="detected_image_{index}"; '
                            f'filename="detected_image_{index}.jpg"'
                        ),
                    },
                    body=_encode_image_as_jpeg(identified_object.cropped_image),
                )
            )

    parts.append(f"--{boundary}--\r\n".encode("ascii"))
    return b"".join(parts)


def _part(
    *,
    boundary: str,
    headers: dict[str, str],
    body: bytes,
) -> bytes:
    header_lines = [f"--{boundary}"]
    header_lines.extend(f"{key}: {value}" for key, value in headers.items())

    return (
        "\r\n".join(header_lines).encode("ascii")
        + b"\r\n\r\n"
        + body
        + b"\r\n"
    )


def _encode_image_as_jpeg(image: Image.Image) -> bytes:
    output = BytesIO()
    image.convert("RGB").save(output, format="JPEG")
    return output.getvalue()
