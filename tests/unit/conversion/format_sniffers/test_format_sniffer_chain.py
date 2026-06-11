from __future__ import annotations

from wild_catalog.conversion.format_sniffers.format_sniffer_chain import (
    build_format_sniffer_chain,
)
from wild_catalog.conversion.format_sniffers.heic_format_sniffer import HeicFormatSniffer
from wild_catalog.conversion.format_sniffers.heif_format_sniffer import HeifFormatSniffer
from wild_catalog.conversion.format_sniffers.jpeg_format_sniffer import JpegFormatSniffer
from wild_catalog.conversion.format_sniffers.not_supported_sniffer import NotSupportedSniffer
from wild_catalog.conversion.format_sniffers.png_format_sniffer import PngFormatSniffer
from wild_catalog.conversion.format_sniffers.raw_format_sniffer import RawFormatSniffer
from wild_catalog.conversion.format_sniffers.webp_format_sniffer import WebPFormatSniffer


def test_build_format_sniffer_chain_returns_singleton() -> None:
    assert build_format_sniffer_chain() is build_format_sniffer_chain()


def test_build_format_sniffer_chain_builds_expected_chain() -> None:
    chain = build_format_sniffer_chain()

    assert isinstance(chain, RawFormatSniffer)

    sniffers = []
    current = chain
    while current is not None:
        sniffers.append(type(current))
        current = current._next

    assert JpegFormatSniffer in sniffers
    assert PngFormatSniffer in sniffers
    assert WebPFormatSniffer in sniffers
    assert HeicFormatSniffer in sniffers
    assert HeifFormatSniffer in sniffers
    assert sniffers[-1] is NotSupportedSniffer
