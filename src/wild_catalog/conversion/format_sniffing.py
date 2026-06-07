from enum import StrEnum


class ImageFormat(StrEnum):
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    HEIC = "heic"
    HEIF = "heif"

    CR2 = "cr2"
    CR3 = "cr3"
    CRW = "crw"
    DNG = "dng"
    NEF = "nef"
    NRW = "nrw"
    ARW = "arw"
    SRF = "srf"
    SR2 = "sr2"
    RAF = "raf"
    RW2 = "rw2"
    ORF = "orf"
    PEF = "pef"
    GPR = "gpr"
    THREE_FR = "3fr"
    FFF = "fff"
    DCR = "dcr"
    K25 = "k25"
    KDC = "kdc"
    MOS = "mos"
    IIQ = "iiq"

    UNKNOWN = "unknown"


RAW_EXTENSIONS = {
    ".cr2": ImageFormat.CR2,
    ".cr3": ImageFormat.CR3,
    ".crw": ImageFormat.CRW,
    ".dng": ImageFormat.DNG,
    ".nef": ImageFormat.NEF,
    ".nrw": ImageFormat.NRW,
    ".arw": ImageFormat.ARW,
    ".srf": ImageFormat.SRF,
    ".sr2": ImageFormat.SR2,
    ".raf": ImageFormat.RAF,
    ".rw2": ImageFormat.RW2,
    ".orf": ImageFormat.ORF,
    ".pef": ImageFormat.PEF,
    ".gpr": ImageFormat.GPR,
    ".3fr": ImageFormat.THREE_FR,
    ".fff": ImageFormat.FFF,
    ".dcr": ImageFormat.DCR,
    ".k25": ImageFormat.K25,
    ".kdc": ImageFormat.KDC,
    ".mos": ImageFormat.MOS,
    ".iiq": ImageFormat.IIQ,
}

RAW_FORMATS = frozenset(RAW_EXTENSIONS.values())


def sniff_image_format(file_bytes: bytes, original_filename: str | None = None) -> ImageFormat:
    if file_bytes.startswith(b"\xff\xd8\xff"):
        return ImageFormat.JPEG

    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return ImageFormat.PNG

    if file_bytes.startswith(b"RIFF") and file_bytes[8:12] == b"WEBP":
        return ImageFormat.WEBP

    if len(file_bytes) >= 12 and file_bytes[4:8] == b"ftyp":
        brand = file_bytes[8:12].lower()

        if brand in {b"heic", b"heix", b"hevc", b"hevx"}:
            return ImageFormat.HEIC

        if brand in {b"heif", b"mif1", b"msf1"}:
            return ImageFormat.HEIF

    if original_filename is not None:
        lowered = original_filename.lower()

        for extension, image_format in RAW_EXTENSIONS.items():
            if lowered.endswith(extension):
                return image_format

    return ImageFormat.UNKNOWN
