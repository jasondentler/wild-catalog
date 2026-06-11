from __future__ import annotations

import pytest

from wild_catalog.conversion.exceptions import UnsupportedImageFormatError
from wild_catalog.conversion.format_sniffers.not_supported_sniffer import (
    NotSupportedSniffer,
)


def test_not_supported_sniffer_raises_unsupported_error() -> None:
    with pytest.raises(UnsupportedImageFormatError, match="Image format could not be detected"):
        NotSupportedSniffer().handle(b"bytes", "image.bin")
