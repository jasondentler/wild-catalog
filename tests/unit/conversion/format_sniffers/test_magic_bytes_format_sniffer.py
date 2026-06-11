from __future__ import annotations

from wild_catalog.conversion.converters.pillow_converter import PillowConverter
from wild_catalog.conversion.format_sniffers.magic_bytes_format_sniffer import (
    MagicBytesFormatSniffer,
)


class _DelegatingSniffer(MagicBytesFormatSniffer[PillowConverter]):
    _converter = PillowConverter()

    def can_handle(self, file_bytes: bytes) -> bool:
        return file_bytes == b"magic"


class _BaseCanHandleSniffer(MagicBytesFormatSniffer[PillowConverter]):
    _converter = PillowConverter()

    def can_handle(self, file_bytes: bytes) -> bool:
        return super().can_handle(file_bytes)


def test_magic_bytes_format_sniffer_returns_converter_when_match() -> None:
    sniffer = _DelegatingSniffer()

    assert isinstance(sniffer.handle(b"magic", "image.jpg"), PillowConverter)


def test_magic_bytes_format_sniffer_delegates_when_not_matched() -> None:
    class _FallbackSniffer:
        def __init__(self) -> None:
            self.calls: list[tuple[bytes, str]] = []

        def handle(self, file_bytes: bytes, original_file_name: str):
            self.calls.append((file_bytes, original_file_name))
            return "fallback"

    next_sniffer = _FallbackSniffer()
    sniffer = _DelegatingSniffer()
    sniffer.set_next(next_sniffer)

    assert sniffer.handle(b"other", "image.jpg") == "fallback"
    assert next_sniffer.calls == [(b"other", "image.jpg")]


def test_magic_bytes_format_sniffer_returns_none_without_next() -> None:
    sniffer = _DelegatingSniffer()

    assert sniffer.handle(b"other", "image.jpg") is None


def test_magic_bytes_format_sniffer_base_can_handle_executes() -> None:
    sniffer = _BaseCanHandleSniffer()

    assert sniffer.can_handle(b"other") is None
