import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock

from wild_catalog.conversion.platform_conversion.macos_sips import MacOSSipsImageConverter


def test_macos_sips_can_convert_heic_and_heif(tmp_path) -> None:
    sips_path = tmp_path / "sips"
    sips_path.touch()
    converter = MacOSSipsImageConverter(sips_path=sips_path)

    assert converter.can_convert("heic") is True
    assert converter.can_convert("heif") is True
    assert converter.can_convert("jpeg") is False


def test_macos_sips_detects_sips_from_path(monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda command: "/usr/bin/sips")

    converter = MacOSSipsImageConverter()

    assert converter._sips_path == Path("/usr/bin/sips")
    assert converter.can_convert("heic") is True


def test_macos_sips_cannot_convert_when_sips_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda command: None)
    monkeypatch.setattr(Path, "exists", lambda path: False)

    converter = MacOSSipsImageConverter()

    assert converter._sips_path is None
    assert converter.can_convert("heic") is False


def test_macos_sips_uses_shell_false_command(monkeypatch, tmp_path) -> None:
    run = Mock()
    monkeypatch.setattr(subprocess, "run", run)
    sips_path = tmp_path / "sips"
    sips_path.touch()

    converter = MacOSSipsImageConverter(
        sips_path=sips_path,
        timeout_seconds=7,
    )

    source = tmp_path / "source.heic"
    output = tmp_path / "output.jpg"

    converter.convert_to_jpeg(source, output)

    run.assert_called_once_with(
        [
            str(sips_path),
            "-s",
            "format",
            "jpeg",
            str(source),
            "--out",
            str(output),
        ],
        check=True,
        timeout=7,
        capture_output=True,
        text=True,
    )


def test_macos_sips_rejects_conversion_when_sips_is_missing(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(shutil, "which", lambda command: None)
    monkeypatch.setattr(Path, "exists", lambda path: False)

    converter = MacOSSipsImageConverter()

    try:
        converter.convert_to_jpeg(tmp_path / "source.heic", tmp_path / "output.jpg")
    except RuntimeError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("Expected missing sips utility to fail conversion.")
