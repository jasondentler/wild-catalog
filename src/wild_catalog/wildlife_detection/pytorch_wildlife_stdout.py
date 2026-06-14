import io
import sys
from contextlib import contextmanager, redirect_stdout
from typing import Any


@contextmanager
def suppress_pytorch_wildlife_model_load_stdout():
    stdout_filter = _FilteredStdout(sys.stdout)
    try:
        with redirect_stdout(stdout_filter):
            yield
    finally:
        stdout_filter.flush()


class _FilteredStdout(io.TextIOBase):
    def __init__(self, stream: Any) -> None:
        self._stream = stream
        self._buffer = ""

    @property
    def encoding(self) -> str | None:
        return getattr(self._stream, "encoding", None)

    def writable(self) -> bool:
        return True

    def write(self, value: str) -> int:
        self._buffer += value

        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._write_line(line + "\n")

        return len(value)

    def flush(self) -> None:
        if self._buffer:
            self._write_line(self._buffer)
            self._buffer = ""
        self._stream.flush()

    def _write_line(self, line: str) -> None:
        if _is_pytorch_wildlife_model_load_line(line):
            return

        self._stream.write(line)


def _is_pytorch_wildlife_model_load_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("Load PResNet") and stripped.endswith(" state_dict")
