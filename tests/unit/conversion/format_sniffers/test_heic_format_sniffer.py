from __future__ import annotations

import pytest

from wild_catalog.conversion.exceptions import UnsupportedImageFormatError
from wild_catalog.conversion.format_sniffers.heic_format_sniffer import HeicFormatSniffer


def test_heic_format_sniffer_raises_for_heic_brand() -> None:
    sniffer = HeicFormatSniffer()

    with pytest.raises(UnsupportedImageFormatError, match="HEIC image format is not supported"):
        sniffer.can_handle_brand(b"heic")


def test_heic_format_sniffer_returns_false_for_other_brand() -> None:
    sniffer = HeicFormatSniffer()

    assert sniffer.can_handle_brand(b"demo") is False
