import asyncio
from types import SimpleNamespace

from wild_catalog.api import logging as api_logging


class _Logger:
    def __init__(self, enabled: bool = True, calls: list[str] | None = None) -> None:
        self._enabled = enabled
        self.calls = calls if calls is not None else []

    def isEnabledFor(self, level):  # noqa: N802
        return self._enabled

    def debug(self, message):
        self.calls.append(message)


def test_format_size_handles_none_zero_and_large_values() -> None:
    format_size = getattr(api_logging, "__format_size")

    assert format_size(None) == "0 B"
    assert format_size(0) == "0 B"
    assert format_size("1024") == "1.00 KB"
    assert format_size(1024 * 1024) == "1.00 MB"


def test_log_identify_request_skips_when_debug_disabled(monkeypatch) -> None:
    monkeypatch.setattr(api_logging, "logger", _Logger(enabled=False))

    asyncio.run(api_logging.log_identify_request(SimpleNamespace(headers={})))


def test_log_identify_request_logs_single_part(monkeypatch) -> None:
    calls = []

    request = SimpleNamespace(headers={"x-filename": "image.jpg", "content-length": "1024"})
    monkeypatch.setattr(api_logging, "logger", _Logger(calls=calls))

    asyncio.run(api_logging.log_identify_request(request))

    assert any("x-filename: image.jpg" in message for message in calls)
    assert any("content-length: 1.00 KB bytes" in message for message in calls)


def test_log_identify_request_logs_multipart(monkeypatch) -> None:
    calls = []

    class _Upload:
        filename = "sample.jpg"
        content_type = "image/jpeg"
        size = 2048

    class _Form:
        def get(self, key):
            return {"image": _Upload(), "payload": b"abc"}.get(key)

    class _Request:
        headers = {"content-type": "multipart/form-data"}

        async def form(self):
            return _Form()

    monkeypatch.setattr(api_logging, "logger", _Logger(calls=calls))

    asyncio.run(api_logging.log_identify_request(_Request()))

    assert any("image.filename: sample.jpg" in message for message in calls)
    assert any("image.content_type: image/jpeg" in message for message in calls)
    assert any("image.size: 2.00 KB" in message for message in calls)
    assert any("payload: b'abc'" in message for message in calls)


def test_log_identify_request_logs_empty_multipart_fields(monkeypatch) -> None:
    calls = []

    class _Form:
        def get(self, key):
            return None

    class _Request:
        headers = {"content-type": "multipart/form-data"}

        async def form(self):
            return _Form()

    monkeypatch.setattr(api_logging, "logger", _Logger(calls=calls))

    asyncio.run(api_logging.log_identify_request(_Request()))

    assert "image: None" in calls
    assert "payload: None" in calls
