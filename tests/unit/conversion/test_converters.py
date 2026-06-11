from __future__ import annotations

from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from wild_catalog.conversion.converters.pillow_converter import PillowConverter
from wild_catalog.conversion.converters.raw_converter import RawConverter
from wild_catalog.conversion.exceptions import InvalidImageError


def make_jpeg_bytes() -> bytes:
    image = Image.new("RGB", (2, 2), color=(255, 0, 0))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_pillow_converter_converts_to_rgb() -> None:
    image = PillowConverter().convert(make_jpeg_bytes())

    assert image.mode == "RGB"
    assert image.size == (2, 2)


def test_pillow_converter_raises_for_invalid_bytes() -> None:
    with pytest.raises(InvalidImageError, match="Unable to decode standard image"):
        PillowConverter().convert(b"not an image")


def test_raw_converter_converts_to_rgb(monkeypatch: pytest.MonkeyPatch) -> None:
    class _RawContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def postprocess(self, use_camera_wb: bool):
            return np.array([[[255, 0, 0]]], dtype=np.uint8)

    monkeypatch.setattr(
        "wild_catalog.conversion.converters.raw_converter.rawpy.imread",
        lambda _: _RawContext(),
    )

    image = RawConverter().convert(b"raw-bytes")

    assert image.mode == "RGB"
    assert image.size == (1, 1)


def test_raw_converter_raises_for_decode_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "wild_catalog.conversion.converters.raw_converter.rawpy.imread",
        lambda _: (_ for _ in ()).throw(RuntimeError("decode failed")),
    )

    with pytest.raises(InvalidImageError, match="Unable to decode RAW image"):
        RawConverter().convert(b"raw-bytes")
