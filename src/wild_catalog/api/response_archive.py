from __future__ import annotations

import json
import re
from pathlib import Path

from wild_catalog.identify_pipeline.identify_result import IdentifyResult

_LEADING_DATE_PREFIX = re.compile(r"^\d{8}-")
_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


class IdentifyResponseArchive:
    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def store(
        self,
        result: IdentifyResult,
        payload: dict[str, object],
    ) -> Path | None:
        if result.captured_at is None or result.original_filename is None:
            return None

        self._directory.mkdir(parents=True, exist_ok=True)
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        path = self._write_to_next_available_path(result, body + b"\n")
        return path

    def _write_to_next_available_path(
        self,
        result: IdentifyResult,
        body: bytes,
    ) -> Path:
        date_prefix = result.captured_at.strftime("%Y%m%d")
        file_stem = _response_file_stem(result.original_filename)
        base_name = f"{date_prefix}-{file_stem}"

        index = 1
        while True:
            suffix = "" if index == 1 else f"-{index}"
            path = self._directory / f"{base_name}{suffix}.json"
            try:
                with path.open("xb") as response_file:
                    response_file.write(body)
            except FileExistsError:
                index += 1
                continue

            return path


def _response_file_stem(original_filename: str) -> str:
    stem = Path(original_filename).name
    stem = Path(stem).stem
    stem = _LEADING_DATE_PREFIX.sub("", stem)
    stem = _UNSAFE_FILENAME_CHARS.sub("_", stem)
    return stem.strip("._-") or "upload"
