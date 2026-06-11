from __future__ import annotations

from wild_catalog.conversion.converters.pillow_converter import PillowConverter
from wild_catalog.conversion.format_sniffers.webp_format_sniffer import WebPFormatSniffer


def test_webp_format_sniffer_detects_webp_magic_bytes() -> None:
    assert isinstance(
        WebPFormatSniffer().handle(b"RIFFxxxxWEBPrest", "image.webp"),
        PillowConverter,
    )
