import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock

from wild_catalog.conversion.platform_conversion.windows_imagemagick import (
    WindowsImageMagickImageConverter,
)


def test_windows_imagemagick_can_convert_heic_and_heif(monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda command: "C:/ImageMagick/magick.exe")
    converter = WindowsImageMagickImageConverter(magick_path=Path("magick.exe"))

    assert converter.can_convert("heic") is True
    assert converter.can_convert("heif") is True
    assert converter.can_convert("jpeg") is False


def test_windows_imagemagick_detects_magick_exe_from_path(monkeypatch) -> None:
    def which(command: str) -> str | None:
        return "C:/ImageMagick/magick.exe" if command == "magick.exe" else None

    monkeypatch.setattr(shutil, "which", which)

    converter = WindowsImageMagickImageConverter()

    assert converter._magick_path == Path("C:/ImageMagick/magick.exe")
    assert converter.can_convert("heic") is True


def test_windows_imagemagick_falls_back_to_magick_from_path(monkeypatch) -> None:
    def which(command: str) -> str | None:
        return "C:/ImageMagick/magick" if command == "magick" else None

    monkeypatch.setattr(shutil, "which", which)

    converter = WindowsImageMagickImageConverter()

    assert converter._magick_path == Path("C:/ImageMagick/magick")


def test_windows_imagemagick_cannot_convert_when_magick_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda command: None)

    converter = WindowsImageMagickImageConverter()

    assert converter._magick_path is None
    assert converter.can_convert("heic") is False


def test_windows_imagemagick_uses_shell_false_command(monkeypatch, tmp_path) -> None:
    run = Mock()
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(shutil, "which", lambda command: "C:/ImageMagick/magick.exe")

    converter = WindowsImageMagickImageConverter(
        magick_path=Path("magick.exe"),
        timeout_seconds=7,
    )

    source = tmp_path / "source.heic"
    output = tmp_path / "output.jpg"

    converter.convert_to_jpeg(source, output)

    run.assert_called_once_with(
        [
            "C:/ImageMagick/magick.exe",
            str(source),
            str(output),
        ],
        check=True,
        timeout=7,
        capture_output=True,
        text=True,
    )


def test_windows_imagemagick_rejects_conversion_when_magick_is_missing(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda command: None)

    converter = WindowsImageMagickImageConverter()

    try:
        converter.convert_to_jpeg(tmp_path / "source.heic", tmp_path / "output.jpg")
    except RuntimeError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("Expected missing ImageMagick utility to fail conversion.")
