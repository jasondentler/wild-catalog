from __future__ import annotations

from wild_catalog.conversion.converters.raw_converter import RawConverter
from wild_catalog.conversion.format_sniffers.abstract_format_sniffer import (
    AbstractFormatSniffer,
)
from wild_catalog.conversion.format_sniffers.raw_format_sniffer import RawFormatSniffer


class _DelegatingSniffer(AbstractFormatSniffer):
    def __init__(self, result: object | None = None) -> None:
        self.result = result
        self.calls: list[tuple[bytes, str | None]] = []

    def handle(self, file_bytes: bytes, original_file_name: str | None):
        self.calls.append((file_bytes, original_file_name))
        if self.result is not None:
            return self.result

        return super().handle(file_bytes, original_file_name)


def test_raw_format_sniffer_detects_raw_extensions() -> None:
    sniffer = RawFormatSniffer()

    assert sniffer.can_handle("image.cr2") is True
    assert sniffer.can_handle("image.cr3") is True
    assert sniffer.can_handle("image.jpg") is False
    assert sniffer.can_handle("image.txt") is False


def test_raw_format_sniffer_returns_raw_converter_for_raw_extension() -> None:
    assert isinstance(RawFormatSniffer().handle(b"raw bytes", "image.cr3"), RawConverter)


def test_raw_format_sniffer_delegates_when_filename_missing() -> None:
    next_sniffer = _DelegatingSniffer(result="fallback")
    sniffer = RawFormatSniffer()
    sniffer.set_next(next_sniffer)

    assert sniffer.handle(b"raw bytes", None) == "fallback"
    assert next_sniffer.calls == [(b"raw bytes", None)]


def test_raw_format_sniffer_returns_none_without_next_for_non_raw_file() -> None:
    sniffer = RawFormatSniffer()

    assert sniffer.handle(b"raw bytes", "image.jpg") is None
