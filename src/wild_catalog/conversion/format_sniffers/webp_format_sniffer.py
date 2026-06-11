from wild_catalog.conversion.converters.pillow_converter import PillowConverter
from wild_catalog.conversion.format_sniffers.magic_bytes_format_sniffer import (
    MagicBytesFormatSniffer,
)


class WebPFormatSniffer(MagicBytesFormatSniffer[PillowConverter]):
    _converter = PillowConverter()

    def can_handle(self, file_bytes):
        return (
            len(file_bytes) >= 12 and file_bytes.startswith(b"RIFF") and file_bytes[8:12] == b"WEBP"
        )
