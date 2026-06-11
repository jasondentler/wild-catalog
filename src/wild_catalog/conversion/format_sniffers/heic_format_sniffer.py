from wild_catalog.conversion.exceptions import UnsupportedImageFormatError
from wild_catalog.conversion.format_sniffers.heic_heif_format_sniffer import HeicHeifFormatSniffer


class HeicFormatSniffer(HeicHeifFormatSniffer):
    def can_handle_brand(self, brand):
        if brand in {b"heic", b"heix", b"hevc", b"hevx"}:
            raise UnsupportedImageFormatError("HEIC image format is not supported.")

        return False
