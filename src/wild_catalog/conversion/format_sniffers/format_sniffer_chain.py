from functools import cache

from wild_catalog.conversion.format_sniffers.format_sniffer import FormatSniffer
from wild_catalog.conversion.format_sniffers.heic_format_sniffer import HeicFormatSniffer
from wild_catalog.conversion.format_sniffers.heif_format_sniffer import HeifFormatSniffer
from wild_catalog.conversion.format_sniffers.jpeg_format_sniffer import JpegFormatSniffer
from wild_catalog.conversion.format_sniffers.not_supported_sniffer import NotSupportedSniffer
from wild_catalog.conversion.format_sniffers.png_format_sniffer import PngFormatSniffer
from wild_catalog.conversion.format_sniffers.raw_format_sniffer import RawFormatSniffer
from wild_catalog.conversion.format_sniffers.webp_format_sniffer import WebPFormatSniffer


@cache
def build_format_sniffer_chain() -> FormatSniffer:
    head = RawFormatSniffer()
    head.set_next(JpegFormatSniffer()) \
        .set_next(PngFormatSniffer()) \
        .set_next(WebPFormatSniffer()) \
        .set_next(HeicFormatSniffer()) \
        .set_next(HeifFormatSniffer()) \
        .set_next(NotSupportedSniffer())
    return head
