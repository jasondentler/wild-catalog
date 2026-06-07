from pathlib import Path
from typing import Protocol


class PlatformImageConverter(Protocol):
    def can_convert(self, detected_format: str) -> bool:
        ...

    def convert_to_jpeg(self, source_path: Path, output_path: Path) -> None:
        ...
