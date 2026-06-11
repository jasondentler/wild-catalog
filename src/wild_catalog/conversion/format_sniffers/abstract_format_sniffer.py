from abc import abstractmethod

from wild_catalog.conversion.converters.converter import Converter
from wild_catalog.conversion.format_sniffers.format_sniffer import FormatSniffer


class AbstractFormatSniffer(FormatSniffer):
    _next: FormatSniffer = None

    def set_next(self, handler: FormatSniffer) -> FormatSniffer:
        self._next = handler
        return handler

    @abstractmethod
    def handle(self, file_bytes: bytes, original_file_name: str) -> Converter:
        if self._next:
            return self._next.handle(file_bytes, original_file_name)

        return None
