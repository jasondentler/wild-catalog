from abc import abstractmethod

from wild_catalog.conversion.format_sniffers.magic_bytes_format_sniffer import (
    MagicBytesFormatSniffer,
)


class HeicHeifFormatSniffer(MagicBytesFormatSniffer):
    def can_handle(self, file_bytes):
        if len(file_bytes) < 12:
            return False

        if file_bytes[4:8] != b"ftyp":
            return False

        brand = file_bytes[8:12].lower()

        return self.can_handle_brand(brand)

    @abstractmethod
    def can_handle_brand(self, brand: bytes) -> bool:
        return False
