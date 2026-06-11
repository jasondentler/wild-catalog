from wild_catalog.conversion.converters.raw_converter import RawConverter
from wild_catalog.conversion.format_sniffers.abstract_format_sniffer import AbstractFormatSniffer

RAW_EXTENSIONS = [
    ".cr2",
    ".cr3",
    ".crw",
    ".dng",
    ".nef",
    ".nrw",
    ".arw",
    ".srf",
    ".sr2",
    ".raf",
    ".rw2",
    ".orf",
    ".pef",
    ".gpr",
    ".3fr",
    ".fff",
    ".dcr",
    ".k25",
    ".kdc",
    ".mos",
    ".iiq",
]

class RawFormatSniffer(AbstractFormatSniffer):
    _converter = RawConverter()

    def handle(self, file_bytes, original_filename):
        if original_filename is None:
            return super().handle(file_bytes, original_filename)

        lowered = original_filename.lower()

        if self.can_handle(lowered):
            return self._converter

        return super().handle(file_bytes, original_filename)

    def can_handle(self, original_filename: str) -> bool:
        return original_filename.endswith(tuple(RAW_EXTENSIONS))
