from __future__ import annotations

from wild_catalog.conversion.converters.pillow_converter import PillowConverter
from wild_catalog.conversion.format_sniffers.jpeg_format_sniffer import JpegFormatSniffer


def test_jpeg_format_sniffer_detects_jpeg_magic_bytes() -> None:
    assert isinstance(
        JpegFormatSniffer().handle(b"\xff\xd8\xff\xe0rest", "image.jpg"),
        PillowConverter,
    )
