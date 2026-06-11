from wild_catalog.conversion.exceptions import UnsupportedImageFormatError
from wild_catalog.conversion.format_sniffers.abstract_format_sniffer import AbstractFormatSniffer


class NotSupportedSniffer(AbstractFormatSniffer):

    def handle(self, file_bytes, original_file_name):
        raise UnsupportedImageFormatError("Image format could not be detected")
