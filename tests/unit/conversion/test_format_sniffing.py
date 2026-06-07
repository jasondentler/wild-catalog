from wild_catalog.conversion.format_sniffing import ImageFormat, sniff_image_format


def test_sniff_image_format_detects_jpeg() -> None:
    assert sniff_image_format(b"\xff\xd8\xff\xe0rest") == ImageFormat.JPEG


def test_sniff_image_format_detects_png() -> None:
    assert sniff_image_format(b"\x89PNG\r\n\x1a\nrest") == ImageFormat.PNG


def test_sniff_image_format_detects_webp() -> None:
    assert sniff_image_format(b"RIFFxxxxWEBPrest") == ImageFormat.WEBP


def test_sniff_image_format_detects_heic() -> None:
    assert sniff_image_format(b"\x00\x00\x00\x18ftypheicrest") == ImageFormat.HEIC


def test_sniff_image_format_detects_heif() -> None:
    assert sniff_image_format(b"\x00\x00\x00\x18ftypheifrest") == ImageFormat.HEIF


def test_sniff_image_format_detects_raw_by_extension() -> None:
    assert sniff_image_format(b"raw bytes", "image.cr3") == ImageFormat.CR3


def test_sniff_image_format_prefers_standard_magic_bytes_over_raw_extension() -> None:
    assert sniff_image_format(b"\xff\xd8\xff\xe0rest", "image.cr3") == ImageFormat.JPEG


def test_sniff_image_format_returns_unknown() -> None:
    assert sniff_image_format(b"not an image") == ImageFormat.UNKNOWN
