from collections.abc import AsyncGenerator

from fastapi import Request, UploadFile
from pydantic import ValidationError

from wild_catalog.api.request_models import IdentifyRequest
from wild_catalog.api.simple_request_mapper import parse_content_language_header
from wild_catalog.core.errors import (
    ImagePartMissingError,
    InvalidGpsOverrideError,
    MalformedJsonPayloadError,
)
from wild_catalog.core.types import GpsCoordinates
from wild_catalog.pipeline.identify_command import ExifOverride, IdentifyCommand


async def create_multipart_form_command(
    request: Request,
) -> tuple[IdentifyCommand, AsyncGenerator[bytes]]:
    identify_request: IdentifyRequest | None = None

    form = await request.form()

    image = form.get("image")
    if image is None:
        raise ImagePartMissingError()

    payload = form.get("payload")
    if payload is not None:
        try:
            if hasattr(payload, "read") and not isinstance(
                payload, (str, bytes, bytearray)
            ):
                payload = await payload.read()
            identify_request = IdentifyRequest.model_validate_json(payload)
        except ValidationError as error:
            if _is_gps_override_validation_error(error):
                raise InvalidGpsOverrideError(
                    public_detail="Invalid GPS override.",
                    debug_detail=str(error),
                ) from error

            raise MalformedJsonPayloadError(
                public_detail="Invalid identify request payload.",
                debug_detail=str(error),
            ) from error

    return __identify_request_to_command(request, identify_request, image), _get_stream(image)


def __identify_request_to_command(
    request: Request,
    identify_request: IdentifyRequest | None,
    image: UploadFile,
) -> IdentifyCommand:
    content_language = request.headers.get("content-language")

    original_filename = image.filename
    if original_filename is None and identify_request is not None:
        original_filename = identify_request.original_filename

    exif_override = None

    common_name_language: str | None = None

    if identify_request and identify_request.common_name_language:
        common_name_language = identify_request.common_name_language
    else:
        common_name_language = parse_content_language_header(content_language)

    if identify_request and identify_request.exif_override:
        exif_override = ExifOverride(
            gps_coordinates=_parse_gps_coordinates(
                identify_request.exif_override.gps_coordinates
            ),
            captured_at=identify_request.exif_override.captured_at,
        )

    return IdentifyCommand.create(
        original_filename=original_filename,
        image_size_bytes=image.size,
        exif_override=exif_override,
        return_detected_images=(
            identify_request.return_detected_images if identify_request else False
        ),
        common_name_language=common_name_language,
    )


def _parse_gps_coordinates(value: str | None) -> GpsCoordinates | None:
    if value is None:
        return None

    latitude, longitude = value.split(",")
    return float(latitude.strip()), float(longitude.strip())


def _is_gps_override_validation_error(error: ValidationError) -> bool:
    return any(
        tuple(validation_error["loc"])[-2:] == ("exif_override", "gps_coordinates")
        for validation_error in error.errors()
    )


async def _get_stream(file: UploadFile, chunk_size: int = 65536) -> AsyncGenerator[bytes]:
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        yield chunk
