from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image

from wild_catalog.conversion.exceptions import (
    ImageTooLargeError,
    UnsupportedImageFormatError,
)
from wild_catalog.conversion.service import ImageConversionService


def make_test_image_bytes(
    *,
    image_format: str = "JPEG",
    size: tuple[int, int] = (10, 10),
) -> bytes:
    image = Image.new("RGB", size, color=(255, 0, 0))
    buffer = BytesIO()
    image.save(buffer, format=image_format)
    return buffer.getvalue()


def test_decode_standard_image_returns_rgb_image() -> None:
    file_bytes = make_test_image_bytes()

    service = ImageConversionService(
        SimpleNamespace(max_upload_bytes=10_000, max_image_pixels=10_000),
    )
    image = service.convert(BytesIO(file_bytes))

    assert image.mode == "RGB"
    assert image.size == (10, 10)


def test_decode_standard_image_rejects_too_many_pixels() -> None:
    file_bytes = make_test_image_bytes(size=(10, 10))
    service = ImageConversionService(
        SimpleNamespace(max_upload_bytes=10_000, max_image_pixels=50),
    )

    with pytest.raises(ImageTooLargeError) as exc_info:
        service.convert(BytesIO(file_bytes))

    assert exc_info.value.public_detail == (
        "Decoded image exceeds the configured pixel limit of 0.00 MP."
    )


def test_decode_standard_image_rejects_invalid_bytes() -> None:
    service = ImageConversionService(
        SimpleNamespace(max_upload_bytes=10_000, max_image_pixels=10_000),
    )

    with pytest.raises(UnsupportedImageFormatError):
        service.process_and_extract_metadata(
            image_file=BytesIO(b"not an image"),
            original_filename="image.jpg",
        )
