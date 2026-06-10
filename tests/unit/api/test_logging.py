import asyncio
from types import SimpleNamespace

from wild_catalog.api.logging import log_identify_request_middleware


class DummyLogger:
    def __init__(self, *, debug_enabled: bool) -> None:
        self.debug_enabled = debug_enabled
        self.messages: list[str] = []

    def isEnabledFor(self, level: int) -> bool:  # noqa: N802
        return self.debug_enabled

    def debug(self, message: str) -> None:
        self.messages.append(message)


def test_log_identify_request_skips_logging_when_debug_disabled(monkeypatch) -> None:
    dummy_logger = DummyLogger(debug_enabled=False)
    monkeypatch.setattr("wild_catalog.api.logging.logger", dummy_logger)

    asyncio.run(
        log_identify_request_middleware(
            image=SimpleNamespace(filename="image.jpg", content_type="image/jpeg", size=123),
            payload=SimpleNamespace(model_dump_json=lambda: '{"foo":"bar"}'),
        )
    )

    assert dummy_logger.messages == []


def test_log_identify_request_logs_image_and_payload(monkeypatch) -> None:
    dummy_logger = DummyLogger(debug_enabled=True)
    monkeypatch.setattr("wild_catalog.api.logging.logger", dummy_logger)

    asyncio.run(
        log_identify_request_middleware(
            image=SimpleNamespace(filename=None, content_type=None, size=None),
            payload=SimpleNamespace(model_dump_json=lambda: '{"original_filename":"camera.jpg"}'),
        )
    )

    assert dummy_logger.messages == [
        "image: untitled; type=unknown; size=0 bytes",
        'Request payload: {"original_filename":"camera.jpg"}',
    ]


def test_log_identify_request_logs_missing_values(monkeypatch) -> None:
    dummy_logger = DummyLogger(debug_enabled=True)
    monkeypatch.setattr("wild_catalog.api.logging.logger", dummy_logger)

    asyncio.run(log_identify_request_middleware(image=None, payload=None))

    assert dummy_logger.messages == [
        "image: None",
        "Request payload: None",
    ]
