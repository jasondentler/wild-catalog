import asyncio
import io
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from starlette.datastructures import UploadFile
from starlette.requests import Request

from wild_catalog.api.multipart_request_mapper import (
    __identify_request_to_command,
    _get_stream,
    _is_gps_override_validation_error,
    create_multipart_form_command,
)
from wild_catalog.api.request_models import ExifOverrideRequest, IdentifyRequest
from wild_catalog.core.errors import (
    ImagePartMissingError,
    InvalidGpsOverrideError,
    MalformedJsonPayloadError,
)


def make_request(*, content_language: str | None = None) -> Request:
    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    headers = []
    if content_language is not None:
        headers.append((b"content-language", content_language.encode()))

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/identify",
            "headers": headers,
        },
        receive,
    )


def test_identify_request_to_command_uses_upload_metadata_when_payload_missing() -> None:
    image = SimpleNamespace(filename="trail-camera.jpg", size=1234)

    command = __identify_request_to_command(make_request(), None, image)

    assert command.original_filename == "trail-camera.jpg"
    assert command.image_size_bytes == 1234
    assert command.exif_override is None
    assert command.return_detected_images is False
    assert command.common_name_language == "en-US"


def test_identify_request_to_command_merges_payload_and_upload_metadata() -> None:
    image = SimpleNamespace(filename=None, size=4321)
    identify_request = IdentifyRequest(
        original_filename="fallback.jpg",
        exif_override=ExifOverrideRequest(
            gps_coordinates="29.573361, -94.389507",
            captured_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
        ),
        return_detected_images=True,
        common_name_language="es-MX",
    )

    command = __identify_request_to_command(make_request(), identify_request, image)

    assert command.original_filename == "fallback.jpg"
    assert command.image_size_bytes == 4321
    assert command.exif_override is not None
    assert command.exif_override.gps_coordinates == (29.573361, -94.389507)
    assert command.exif_override.captured_at == datetime(
        2026, 5, 1, 12, 30, tzinfo=UTC
    )
    assert command.return_detected_images is True
    assert command.common_name_language == "es-MX"


def test_get_stream_yields_chunks_until_eof() -> None:
    class FakeFile:
        def __init__(self) -> None:
            self.chunks = [b"abc", b"def", b""]

        async def read(self, chunk_size: int = 65536) -> bytes:
            return self.chunks.pop(0)

    async def collect() -> list[bytes]:
        return [chunk async for chunk in _get_stream(FakeFile())]

    assert asyncio.run(collect()) == [b"abc", b"def"]


def test_multipart_payload_uploadfile_is_parsed() -> None:
    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/identify",
            "headers": [],
        },
        receive,
    )
    image = SimpleNamespace(filename="trail-camera.jpg", size=1234)
    payload = UploadFile(file=io.BytesIO(b'{"original_filename":"blob.jpg"}'), filename="blob")

    async def run() -> object:
        form = {"image": image, "payload": payload}
        request._form = form  # type: ignore[attr-defined]
        command, _ = await create_multipart_form_command(request)
        return command

    command = asyncio.run(run())

    assert command.original_filename == "trail-camera.jpg"


def test_create_multipart_form_command_rejects_missing_image() -> None:
    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/identify",
            "headers": [],
        },
        receive,
    )

    async def run() -> object:
        request._form = {"payload": b"{}"}  # type: ignore[attr-defined]
        return await create_multipart_form_command(request)

    with pytest.raises(ImagePartMissingError):
        asyncio.run(run())


def test_is_gps_override_validation_error_detects_nested_location() -> None:
    class _Error:
        def errors(self):
            return [{"loc": ("body", "exif_override", "gps_coordinates")}]

    assert _is_gps_override_validation_error(_Error()) is True


def test_create_multipart_form_command_rejects_invalid_json_payload() -> None:
    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/identify",
            "headers": [],
        },
        receive,
    )
    image = SimpleNamespace(filename="trail-camera.jpg", size=1234)

    class _BadPayload:
        async def read(self):
            return b"not-json"

    async def run() -> object:
        request._form = {"image": image, "payload": _BadPayload()}  # type: ignore[attr-defined]
        return await create_multipart_form_command(request)

    with pytest.raises(MalformedJsonPayloadError):
        asyncio.run(run())


def test_create_multipart_form_command_rejects_invalid_gps_override() -> None:
    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/identify",
            "headers": [],
        },
        receive,
    )
    image = SimpleNamespace(filename="trail-camera.jpg", size=1234)
    payload = io.BytesIO(
        b'{"exif_override":{"gps_coordinates":"bad"}}'
    )

    async def run() -> object:
        request._form = {  # type: ignore[attr-defined]
            "image": image,
            "payload": UploadFile(file=payload, filename="payload.json"),
        }
        return await create_multipart_form_command(request)

    with pytest.raises(InvalidGpsOverrideError):
        asyncio.run(run())
