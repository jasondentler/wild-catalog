from datetime import datetime
from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image

from wild_catalog.conversion.exceptions import (
    ImageTooLargeError,
    UnsupportedImageFormatError,
)
from wild_catalog.conversion.service import ImageConversionService
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
    settings = SimpleNamespace(max_upload_bytes=100_000, max_image_pixels=10_000)
    return ImageConversionService(settings)


def test_conversion_service_rejects_upload_larger_than_limit() -> None:
    settings = SimpleNamespace(max_upload_bytes=3, max_image_pixels=10_000)
    service = ImageConversionService(settings)

    with pytest.raises(ImageTooLargeError):
        service.process_and_extract_metadata(
            image_file=BytesIO(b"too large"),
            original_filename="image.jpg",
        )


def test_read_upload_bytes_stops_reading_after_limit() -> None:
    class ChunkedFile:
        def __init__(self) -> None:
            self.calls = 0
            self.rewound = False

        def seek(self, offset: int, whence: int = 0):
            if offset == 0 and whence == 0:
                self.rewound = True

        def read(self, size: int = -1) -> bytes:
            self.calls += 1
            if self.calls == 1:
                return b"abc"
            if self.calls == 2:
                return b"def"
            return b""

    service = ImageConversionService(SimpleNamespace(max_upload_bytes=5, max_image_pixels=10_000))
    file_obj = ChunkedFile()

    with pytest.raises(ImageTooLargeError):
        service._read_upload_bytes(file_obj)

    assert file_obj.calls == 2


def test_read_upload_bytes_rewinds_on_success() -> None:
    class ChunkedFile:
        def __init__(self) -> None:
            self.calls = 0
            self.positions = []

        def seek(self, offset: int, whence: int = 0):
            self.positions.append((offset, whence))

        def read(self, size: int = -1) -> bytes:
            self.calls += 1
            if self.calls == 1:
                return b"abc"
            return b""

    service = ImageConversionService(SimpleNamespace(max_upload_bytes=5, max_image_pixels=10_000))
    file_obj = ChunkedFile()

    assert service._read_upload_bytes(file_obj) == b"abc"
    assert file_obj.positions[0] == (0, 0)
    assert file_obj.positions[-1] == (0, 0)


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
