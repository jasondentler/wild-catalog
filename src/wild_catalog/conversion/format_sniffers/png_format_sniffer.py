from wild_catalog.conversion.converters.pillow_converter import PillowConverter
from wild_catalog.conversion.format_sniffers.magic_bytes_format_sniffer import (
    MagicBytesFormatSniffer,
)


class PngFormatSniffer(MagicBytesFormatSniffer[PillowConverter]):
    _converter = PillowConverter()

    def can_handle(self, file_bytes):
        return file_bytes.startswith(b"\x89PNG\r\n\x1a\n")
