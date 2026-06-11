from wild_catalog.conversion.exceptions import UnsupportedImageFormatError
from wild_catalog.conversion.format_sniffers.heic_heif_format_sniffer import HeicHeifFormatSniffer


class HeifFormatSniffer(HeicHeifFormatSniffer):
    def can_handle_brand(self, brand):
        if brand in {b"heif", b"mif1", b"msf1"}:
            raise UnsupportedImageFormatError("HEIF image format is not supported.")

        return False
