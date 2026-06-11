from __future__ import annotations

import pytest

from wild_catalog.conversion.exceptions import UnsupportedImageFormatError
from wild_catalog.conversion.format_sniffers.heif_format_sniffer import HeifFormatSniffer


def test_heif_format_sniffer_raises_for_heif_brand() -> None:
    sniffer = HeifFormatSniffer()

    with pytest.raises(UnsupportedImageFormatError, match="HEIF image format is not supported"):
        sniffer.can_handle_brand(b"heif")


def test_heif_format_sniffer_returns_false_for_other_brand() -> None:
    sniffer = HeifFormatSniffer()

    assert sniffer.can_handle_brand(b"demo") is False
