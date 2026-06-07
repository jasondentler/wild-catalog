from io import BytesIO

import pytest
from PIL import Image

from wild_catalog.conversion.exceptions import ImageTooLargeError, InvalidImageError
from wild_catalog.conversion.standard import decode_standard_image


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

    image = decode_standard_image(file_bytes, max_image_pixels=10_000)

    assert image.mode == "RGB"
    assert image.size == (10, 10)


def test_decode_standard_image_rejects_too_many_pixels() -> None:
    file_bytes = make_test_image_bytes(size=(10, 10))

    with pytest.raises(ImageTooLargeError):
        decode_standard_image(file_bytes, max_image_pixels=50)


def test_decode_standard_image_rejects_invalid_bytes() -> None:
    with pytest.raises(InvalidImageError):
        decode_standard_image(b"not an image", max_image_pixels=10_000)
