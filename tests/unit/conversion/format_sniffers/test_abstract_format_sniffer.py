from __future__ import annotations

from types import SimpleNamespace

from wild_catalog.conversion.format_sniffers.abstract_format_sniffer import (
    AbstractFormatSniffer,
)


class _DelegatingSniffer(AbstractFormatSniffer):
    def __init__(self, result: object | None = None) -> None:
        self.result = result
        self.calls: list[tuple[bytes, str]] = []

    def handle(self, file_bytes: bytes, original_file_name: str):
        self.calls.append((file_bytes, original_file_name))
        if self.result is not None:
            return self.result

        return super().handle(file_bytes, original_file_name)


class _BaseMethodSniffer(AbstractFormatSniffer):
    def set_next(self, handler: AbstractFormatSniffer):
        return super().set_next(handler)

    def handle(self, file_bytes: bytes, original_file_name: str):
        return super().handle(file_bytes, original_file_name)


def test_abstract_format_sniffer_delegates_to_next() -> None:
    next_sniffer = _DelegatingSniffer(result="handled")
    sniffer = _DelegatingSniffer()
    sniffer.set_next(next_sniffer)

    assert sniffer.handle(b"bytes", "image.jpg") == "handled"
    assert next_sniffer.calls == [(b"bytes", "image.jpg")]


def test_abstract_format_sniffer_returns_none_without_next() -> None:
    sniffer = _DelegatingSniffer()

    assert sniffer.handle(b"bytes", "image.jpg") is None


def test_abstract_format_sniffer_set_next_returns_handler() -> None:
    sniffer = _DelegatingSniffer()
    next_sniffer = _DelegatingSniffer(result="handled")

    assert sniffer.set_next(next_sniffer) is next_sniffer


def test_abstract_format_sniffer_base_methods_execute() -> None:
    sniffer = _BaseMethodSniffer()
    next_sniffer = _DelegatingSniffer(result="handled")

    assert sniffer.set_next(next_sniffer) is next_sniffer
    assert sniffer.handle(b"bytes", "image.jpg") == "handled"


def test_abstract_format_sniffer_unbound_base_methods_execute() -> None:
    handler = _DelegatingSniffer(result="handled")

    sniffer = SimpleNamespace(_next=None)

    assert AbstractFormatSniffer.set_next(sniffer, handler) is handler
    assert AbstractFormatSniffer.handle(sniffer, b"bytes", "image.jpg") == "handled"
