from __future__ import annotations

from abc import ABC, abstractmethod

from wild_catalog.conversion.converters.converter import Converter


class FormatSniffer(ABC):
    @abstractmethod
    def set_next(self, handler: FormatSniffer) -> FormatSniffer:
        return handler  # pragma: no cover

    @abstractmethod
    def handle(self, file_bytes: bytes, original_filename: str) -> Converter:
        return None  # pragma: no cover
