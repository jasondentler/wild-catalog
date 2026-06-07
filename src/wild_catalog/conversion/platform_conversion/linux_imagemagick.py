import shutil
import subprocess
from pathlib import Path


class LinuxImageMagickImageConverter:
    def __init__(
        self,
        magick_path: Path | None = None,
        timeout_seconds: int = 10,
    ) -> None:
        self._magick_path = _resolve_executable(magick_path or Path("magick"))
        self._timeout_seconds = timeout_seconds

    def can_convert(self, detected_format: str) -> bool:
        return self._magick_path is not None and detected_format.lower() in {"heic", "heif"}

    def convert_to_jpeg(self, source_path: Path, output_path: Path) -> None:
        if self._magick_path is None:
            raise RuntimeError("ImageMagick conversion utility was not found.")

        subprocess.run(
            [
                str(self._magick_path),
                str(source_path),
                str(output_path),
            ],
            check=True,
            timeout=self._timeout_seconds,
            capture_output=True,
            text=True,
        )


def _resolve_executable(path: Path) -> Path | None:
    if path.is_absolute():
        return path if path.exists() else None

    resolved = shutil.which(str(path))
    return Path(resolved) if resolved is not None else None
