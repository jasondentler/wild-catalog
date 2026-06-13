import sys
from datetime import datetime
from io import BytesIO
from types import SimpleNamespace

from wild_catalog.conversion import exif
from wild_catalog.conversion.exif import extract_metadata


def test_extract_metadata_returns_none_when_exifread_fails(monkeypatch) -> None:
    class _File(BytesIO):
        def seek(self, offset: int, whence: int = 0):
            return super().seek(offset, whence)

    monkeypatch.setattr(
        exif.exifread,
        "process_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("fail")),
    )

    metadata = exif.extract_metadata(_File(b"data"))

    assert metadata.gps_coordinates is None
    assert metadata.captured_at is None


def test_extract_metadata_seeks_back_to_start(monkeypatch) -> None:
    class _File(BytesIO):
        def seek(self, offset: int, whence: int = 0):
            return super().seek(offset, whence)

    monkeypatch.setattr(exif.exifread, "process_file", lambda *_args, **_kwargs: {})
    file_obj = _File(b"data")
    exif.extract_metadata(file_obj)

    assert file_obj.tell() == 0


def test_extract_gps_coordinates_and_captured_at(monkeypatch) -> None:
    class Ratio:
        def __init__(self, num, den):
            self.num = num
            self.den = den

    tags = {
        "GPS GPSLatitude": SimpleNamespace(values=[Ratio(29, 1), Ratio(34, 1), Ratio(0, 1)]),
        "GPS GPSLatitudeRef": "N",
        "GPS GPSLongitude": SimpleNamespace(values=[Ratio(94, 1), Ratio(23, 1), Ratio(0, 1)]),
        "GPS GPSLongitudeRef": "W",
        "EXIF DateTimeOriginal": "2026:04:02 17:34:08",
    }

    assert exif._extract_gps_coordinates(tags) == exif.GpsCoordinates(
        latitude=29.566666666666666,
        longitude=-94.38333333333334,
    )
    assert exif._extract_captured_at(tags) == datetime(2026, 4, 2, 17, 34, 8)


def test_extract_gps_coordinates_applies_south_and_west_signs() -> None:
    class Ratio:
        def __init__(self, num, den):
            self.num = num
            self.den = den

    tags = {
        "GPS GPSLatitude": SimpleNamespace(values=[Ratio(29, 1), Ratio(34, 1), Ratio(0, 1)]),
        "GPS GPSLatitudeRef": "S",
        "GPS GPSLongitude": SimpleNamespace(values=[Ratio(94, 1), Ratio(23, 1), Ratio(0, 1)]),
        "GPS GPSLongitudeRef": "W",
    }

    coordinates = exif._extract_gps_coordinates(tags)

    assert coordinates.latitude < 0
    assert coordinates.longitude < 0


def test_extract_captured_at_returns_none_for_invalid_value() -> None:
    assert exif._extract_captured_at({"EXIF DateTimeOriginal": "bad"}) is None


def test_ratio_to_float_handles_plain_numbers() -> None:
    assert exif._ratio_to_float(1.5) == 1.5


def test_extract_metadata_suppresses_exifread_stderr(monkeypatch, capsys) -> None:
    def fake_process_file(image_file, details: bool = False):
        print("File format not recognized.", file=sys.stderr)
        return {}

    monkeypatch.setattr("wild_catalog.conversion.exif.exifread.process_file", fake_process_file)

    result = extract_metadata(BytesIO(b"raw bytes"))

    assert result.original_filename is None
    assert capsys.readouterr().err == ""
