from datetime import datetime
from io import BytesIO

import pytest
from PIL import Image

from wild_catalog.conversion.exceptions import (
    ImageTooLargeError,
    PlatformConversionError,
    UnsupportedImageFormatError,
)
from wild_catalog.conversion.service import ImageConversionService
from wild_catalog.core.config import Settings
from wild_catalog.core.types import GpsCoordinates


class FailingPlatformConverter:
    def can_convert(self, detected_format: str) -> bool:
        return detected_format == "heic"

    def convert_to_jpeg(self, source_path, output_path) -> None:
        raise RuntimeError("conversion failed")


class CopyingPlatformConverter:
    def __init__(self, jpeg_bytes: bytes) -> None:
        self._jpeg_bytes = jpeg_bytes

    def can_convert(self, detected_format: str) -> bool:
        return detected_format == "heic"

    def convert_to_jpeg(self, source_path, output_path) -> None:
        output_path.write_bytes(self._jpeg_bytes)


def make_jpeg_bytes() -> bytes:
    image = Image.new("RGB", (10, 10), color=(255, 0, 0))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def make_service() -> ImageConversionService:
    return ImageConversionService(
        Settings(
            max_upload_bytes=100_000,
            max_image_pixels=10_000,
            enable_platform_image_conversion=False,
        )
    )


def test_conversion_service_rejects_upload_larger_than_limit() -> None:
    service = ImageConversionService(
        Settings(
            max_upload_bytes=3,
            max_image_pixels=10_000,
            enable_platform_image_conversion=False,
        )
    )

    with pytest.raises(ImageTooLargeError):
        service.process_and_extract_metadata(
            image_file=BytesIO(b"too large"),
            original_filename="image.jpg",
        )


def test_conversion_service_rejects_unknown_format() -> None:
    with pytest.raises(UnsupportedImageFormatError):
        make_service().process_and_extract_metadata(
            image_file=BytesIO(b"not an image"),
            original_filename="image.bin",
        )


def test_conversion_service_converts_jpeg_to_rgb() -> None:
    result = make_service().process_and_extract_metadata(
        image_file=BytesIO(make_jpeg_bytes()),
        original_filename="image.jpg",
    )

    assert result.image.mode == "RGB"
    assert result.image.size == (10, 10)
    assert result.original_filename == "image.jpg"
    assert result.detected_format == "jpeg"


def test_conversion_service_applies_metadata_overrides() -> None:
    gps_coordinates = GpsCoordinates(latitude=29.7604, longitude=-95.3698)
    captured_at = datetime(2026, 4, 19, 12, 30, 0)

    result = make_service().process_and_extract_metadata(
        image_file=BytesIO(make_jpeg_bytes()),
        original_filename="image.jpg",
        gps_coordinates_override=gps_coordinates,
        captured_at_override=captured_at,
    )

    assert result.gps_coordinates == gps_coordinates
    assert result.captured_at == captured_at


def test_conversion_service_rejects_heic_without_platform_converter() -> None:
    with pytest.raises(UnsupportedImageFormatError):
        make_service().process_and_extract_metadata(
            image_file=BytesIO(b"\x00\x00\x00\x18ftypheicrest"),
            original_filename="image.heic",
        )


def test_conversion_service_wraps_platform_conversion_failures() -> None:
    service = ImageConversionService(
        Settings(
            max_upload_bytes=100_000,
            max_image_pixels=10_000,
            platform_image_converter="macos-sips",
        )
    )
    service._platform_converter = FailingPlatformConverter()

    with pytest.raises(PlatformConversionError):
        service.process_and_extract_metadata(
            image_file=BytesIO(b"\x00\x00\x00\x18ftypheicrest"),
            original_filename="image.heic",
        )


def test_conversion_service_decodes_platform_converted_jpeg() -> None:
    service = ImageConversionService(
        Settings(
            max_upload_bytes=100_000,
            max_image_pixels=10_000,
            platform_image_converter="macos-sips",
        )
    )
    service._platform_converter = CopyingPlatformConverter(make_jpeg_bytes())

    result = service.process_and_extract_metadata(
        image_file=BytesIO(b"\x00\x00\x00\x18ftypheicrest"),
        original_filename="image.heic",
    )

    assert result.image.mode == "RGB"
    assert result.image.size == (10, 10)
    assert result.detected_format == "heic"
