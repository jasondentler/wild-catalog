from __future__ import annotations

from wild_catalog.conversion.converters.pillow_converter import PillowConverter
from wild_catalog.conversion.format_sniffers.png_format_sniffer import PngFormatSniffer


def test_png_format_sniffer_detects_png_magic_bytes() -> None:
    assert isinstance(
        PngFormatSniffer().handle(b"\x89PNG\r\n\x1a\nrest", "image.png"),
        PillowConverter,
    )
