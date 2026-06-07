import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock

from wild_catalog.conversion.platform_conversion.linux_imagemagick import (
    LinuxImageMagickImageConverter,
)


def test_linux_imagemagick_can_convert_heic_and_heif(tmp_path) -> None:
    magick_path = tmp_path / "magick"
    magick_path.touch()
    converter = LinuxImageMagickImageConverter(magick_path=magick_path)

    assert converter.can_convert("heic") is True
    assert converter.can_convert("heif") is True
    assert converter.can_convert("jpeg") is False


def test_linux_imagemagick_detects_magick_from_path(monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda command: "/usr/local/bin/magick")

    converter = LinuxImageMagickImageConverter()

    assert converter._magick_path == Path("/usr/local/bin/magick")
    assert converter.can_convert("heic") is True


def test_linux_imagemagick_cannot_convert_when_magick_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda command: None)

    converter = LinuxImageMagickImageConverter()

    assert converter._magick_path is None
    assert converter.can_convert("heic") is False


def test_linux_imagemagick_uses_shell_false_command(monkeypatch, tmp_path) -> None:
    run = Mock()
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(shutil, "which", lambda command: "/usr/local/bin/magick")

    converter = LinuxImageMagickImageConverter(
        magick_path=Path("magick"),
        timeout_seconds=7,
    )

    source = tmp_path / "source.heic"
    output = tmp_path / "output.jpg"

    converter.convert_to_jpeg(source, output)

    run.assert_called_once_with(
        [
            "/usr/local/bin/magick",
            str(source),
            str(output),
        ],
        check=True,
        timeout=7,
        capture_output=True,
        text=True,
    )


def test_linux_imagemagick_rejects_conversion_when_magick_is_missing(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda command: None)

    converter = LinuxImageMagickImageConverter()

    try:
        converter.convert_to_jpeg(tmp_path / "source.heic", tmp_path / "output.jpg")
    except RuntimeError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("Expected missing ImageMagick utility to fail conversion.")
