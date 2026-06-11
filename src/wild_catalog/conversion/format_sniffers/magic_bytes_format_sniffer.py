from abc import abstractmethod

from wild_catalog.conversion.converters.converter import Converter
from wild_catalog.conversion.format_sniffers.abstract_format_sniffer import AbstractFormatSniffer


class MagicBytesFormatSniffer[TConverter: Converter](AbstractFormatSniffer):
    _converter: Converter

    def handle(self, file_bytes, original_file_name):
        if self.can_handle(file_bytes):
            return self._converter

        return super().handle(file_bytes, original_file_name)

    @abstractmethod
    def can_handle(self, file_bytes: bytes) -> bool:
        pass
