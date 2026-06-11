from __future__ import annotations

from wild_catalog.conversion.format_sniffers.heic_heif_format_sniffer import (
    HeicHeifFormatSniffer,
)


class _HeicHeifSniffer(HeicHeifFormatSniffer):
    def can_handle_brand(self, brand: bytes) -> bool:
        return brand == b"demo"


def test_heic_heif_sniffer_requires_ftyp_header() -> None:
    sniffer = _HeicHeifSniffer()

    assert sniffer.can_handle(b"short") is False
    assert sniffer.can_handle(b"\x00\x00\x00\x18xxxxheicrest") is False
    assert sniffer.can_handle(b"\x00\x00\x00\x18ftypxxxxrest") is False


def test_heic_heif_sniffer_detects_supported_brand() -> None:
    sniffer = _HeicHeifSniffer()

    assert sniffer.can_handle(b"\x00\x00\x00\x18ftypdemorest") is True


def test_heic_heif_sniffer_base_can_handle_brand_returns_false() -> None:
    sniffer = _HeicHeifSniffer()

    assert HeicHeifFormatSniffer.can_handle_brand(sniffer, b"demo") is False
