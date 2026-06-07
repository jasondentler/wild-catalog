from pathlib import Path


class NoopPlatformImageConverter:
    def can_convert(self, detected_format: str) -> bool:
        return False

    def convert_to_jpeg(self, source_path: Path, output_path: Path) -> None:
        raise RuntimeError("No platform image converter is configured.")
